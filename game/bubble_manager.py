from __future__ import annotations

import asyncio
import logging
import random
import uuid
from typing import Awaitable, Callable

import config
from game.bubble import Bubble, ClickOutcome, ClickOutcomeKind, now_ms
from protocol.messages import MsgType, ServerMessage

log = logging.getLogger("unf.game.bubble")

BroadcastFn = Callable[[ServerMessage], Awaitable[None]]
CoinAwardFn = Callable[[str, int], Awaitable[int]]
RewardMultiplierFn = Callable[[], float]


# ---------- group generation ----------

class _GroupSpec:

    __slots__ = ("group_id", "bubbles")

    def __init__(self, group_id: int, bubbles: list[Bubble]):
        self.group_id = group_id
        self.bubbles = bubbles


def _pick_bubble_kind(rng: random.Random) -> str:
    return "gold" if rng.random() < config.BUBBLE_GOLD_CHANCE else "normal"


def _generate_bubble(
    rng: random.Random,
    group_id: int,
    spawn_delay: float,
) -> Bubble:
    kind = _pick_bubble_kind(rng)
    lifetime = rng.uniform(
        config.BUBBLE_LIFETIME_MIN_SEC,
        config.BUBBLE_LIFETIME_MAX_SEC,
    )
    size = rng.uniform(config.BUBBLE_SIZE_MIN, config.BUBBLE_SIZE_MAX)
    base_score = (
        config.BUBBLE_GOLD_REWARD_COINS
        if kind == "gold"
        else config.BUBBLE_REWARD_COINS
    )
    if config.BUBBLE_SCORE_JITTER > 0:
        base_score += rng.randint(
            -config.BUBBLE_SCORE_JITTER, config.BUBBLE_SCORE_JITTER
        )
        base_score = max(1, base_score)

    return Bubble(
        bubble_id=uuid.uuid4().hex,
        spawned_at_ms=0,  # set on actual spawn
        kind=kind,
        seed=rng.getrandbits(32),
        group_id=group_id,
        spawn_delay=spawn_delay,
        lifetime=lifetime,
        size=size,
        score=base_score,
    )


def _generate_sequential_group(rng: random.Random, group_id: int) -> _GroupSpec:
    count = rng.randint(
        config.SEQUENTIAL_GROUP_MIN_BUBBLES,
        config.SEQUENTIAL_GROUP_MAX_BUBBLES,
    )
    bubbles: list[Bubble] = []
    for _ in range(count):
        delay = rng.uniform(
            config.SEQUENTIAL_GROUP_MIN_DELAY,
            config.SEQUENTIAL_GROUP_MAX_DELAY,
        )
        bubbles.append(_generate_bubble(rng, group_id, delay))
    return _GroupSpec(group_id, bubbles)


# ---------- manager ----------

class BubbleManager:
    def __init__(
        self,
        room_id: str,
        broadcast: BroadcastFn,
        coin_award: CoinAwardFn,
        reward_multiplier: RewardMultiplierFn | None = None,
        rng_seed: int | None = None,
    ):
        self.room_id = room_id
        self._broadcast = broadcast
        self._coin_award = coin_award
        self._reward_multiplier = reward_multiplier or (lambda: 1.0)

        self._rng = random.Random(rng_seed) if rng_seed is not None else random.Random()
        self._next_group_id = 1

        self._bubbles: dict[str, Bubble] = {}
        self._lock = asyncio.Lock()
        self._spawn_task: asyncio.Task | None = None
        self._running = False

    # ---------- lifecycle ----------

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._spawn_task = asyncio.create_task(self._spawn_loop())
        log.info("bubble manager started room=%s", self.room_id)

    async def stop(self) -> None:
        self._running = False
        if self._spawn_task:
            self._spawn_task.cancel()
            try:
                await self._spawn_task
            except asyncio.CancelledError:
                pass
            self._spawn_task = None
        self._bubbles.clear()
        log.info("bubble manager stopped room=%s", self.room_id)

    # ---------- spawn loop ----------

    async def _spawn_loop(self) -> None:
        try:
            while self._running:
                await self._run_group()
                if not self._running:
                    break
                pause = self._rng.uniform(
                    config.BUBBLE_GROUP_PAUSE_MIN,
                    config.BUBBLE_GROUP_PAUSE_MAX,
                )
                await asyncio.sleep(pause)
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("bubble spawn loop crashed room=%s", self.room_id)

    async def _run_group(self) -> None:
        group_id = self._next_group_id
        self._next_group_id += 1

        spec = _generate_sequential_group(self._rng, group_id)

        await self._broadcast(ServerMessage(
            type=MsgType.BUBBLE_GROUP,
            payload={
                "group_id": spec.group_id,
                "type": "sequential",
                "bubble_count": len(spec.bubbles),
            },
        ))

        for bubble in spec.bubbles:
            if not self._running:
                return
            await asyncio.sleep(bubble.spawn_delay)
            if not self._running:
                return
            await self._spawn_bubble(bubble)

        await self._wait_group_done(group_id)

    async def _spawn_bubble(self, b: Bubble) -> None:
        b.spawned_at_ms = now_ms()
        async with self._lock:
            self._bubbles[b.bubble_id] = b

        await self._broadcast(ServerMessage(
            type=MsgType.BUBBLE_SPAWN,
            payload={"bubbles": [b.to_public()]},
        ))

    async def _wait_group_done(self, group_id: int) -> None:
        while self._running:
            async with self._lock:
                now = now_ms()
                for bid in list(self._bubbles):
                    b = self._bubbles[bid]
                    if b.group_id != group_id:
                        continue
                    if not b.resolved and b.is_expired(now):
                        self._bubbles.pop(bid, None)
                        await self._broadcast(ServerMessage(
                            type=MsgType.BUBBLE_DESPAWN,
                            payload={"bubble_id": bid, "reason": "expired"},
                        ))
                alive = [
                    b for b in self._bubbles.values()
                    if b.group_id == group_id and not b.resolved
                ]
            if not alive:
                return
            await asyncio.sleep(0.1)

    # ---------- click resolution ----------

    async def resolve_click(
        self, player_id: str, bubble_id: str,
        client_ts: float | None = None,
        client_coins: int = 0,
    ) -> ClickOutcome:
        async with self._lock:
            b = self._bubbles.get(bubble_id)
            if b is None:
                return ClickOutcome.rejected(ClickOutcomeKind.UNKNOWN, bubble_id)
            if b.resolved:
                return ClickOutcome.rejected(ClickOutcomeKind.TOO_LATE, bubble_id)
            if b.is_expired():
                self._bubbles.pop(bubble_id, None)
                return ClickOutcome.rejected(ClickOutcomeKind.EXPIRED, bubble_id)

            if b.age_sec() < config.BUBBLE_REACTION_TIME_MIN_SEC:
                return ClickOutcome.rejected(ClickOutcomeKind.TOO_FAST, bubble_id)

            b.resolved = True
            b.popped_by = player_id

            base_cap = b.score * 10
            base_coins = (
                max(1, min(int(client_coins), base_cap))
                if client_coins
                else b.score
            )

            multiplier = self._reward_multiplier()
            coins = max(1, int(round(base_coins * multiplier)))

            self._bubbles.pop(bubble_id, None)
            kind = b.kind
            base_score = b.score

        new_balance = await self._coin_award(player_id, coins)
        await self._broadcast(ServerMessage(
            type=MsgType.BUBBLE_RESULT,
            payload={
                "bubble_id": bubble_id,
                "winner_player_id": player_id,
                "coins_awarded": coins,
                "new_balance": new_balance,
                "multiplier": round(multiplier, 3),
                "base_score": base_score,
                "kind": kind,
            },
        ))
        await self._broadcast(ServerMessage(
            type=MsgType.COIN_UPDATE,
            payload={
                "player_id": player_id,
                "balance": new_balance,
                "delta": coins,
                "kind": kind,
            },
        ))
        return ClickOutcome.won(bubble_id, player_id, coins)