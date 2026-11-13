from __future__ import annotations

import asyncio
import hashlib
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


class BubbleManager:
    def __init__(self, room_id: str, broadcast: BroadcastFn,
                 coin_award: CoinAwardFn):
        self.room_id = room_id
        self._broadcast = broadcast
        self._coin_award = coin_award

        self._bubbles: dict[str, Bubble] = {}
        self._lock = asyncio.Lock()
        self._spawn_task: asyncio.Task | None = None
        self._running = False
        self._spawn_index = 0

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

    # ---------- spawn loop (group-based, like singleplayer) ----------

    async def _spawn_loop(self) -> None:
        try:
            while self._running:
                await self._spawn_group()
                if not self._running:
                    break
                await self._wait_group_done()
                if not self._running:
                    break
                pause = random.uniform(
                    config.BUBBLE_GROUP_PAUSE_MIN,
                    config.BUBBLE_GROUP_PAUSE_MAX,
                )
                await asyncio.sleep(pause)
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("bubble spawn loop crashed room=%s", self.room_id)

    async def _spawn_group(self) -> None:
        count = random.randint(
            config.BUBBLE_GROUP_MIN,
            config.BUBBLE_GROUP_MAX,
        )
        log.debug("room=%s spawning group of %d bubbles", self.room_id, count)

        for _ in range(count):
            if not self._running:
                return
            delay = random.uniform(
                config.BUBBLE_GROUP_DELAY_MIN,
                config.BUBBLE_GROUP_DELAY_MAX,
            )
            await asyncio.sleep(delay)
            if not self._running:
                return
            await self._spawn_one()

    async def _spawn_one(self):
        to_despawn = []
        async with self._lock:
            if not self._running:
                return None
            now = now_ms()
            for b in list(self._bubbles.values()):
                if not b.resolved and b.is_expired(now):
                    self._bubbles.pop(b.bubble_id, None)
                    to_despawn.append(b.bubble_id)
            active = sum(1 for b in self._bubbles.values() if not b.resolved)
            if active >= config.BUBBLE_MAX_ACTIVE:
                return None
            bubble_id = uuid.uuid4().hex
            kind = "gold" if random.random() < config.BUBBLE_GOLD_CHANCE else "normal"
            seed_bytes = hashlib.sha256(bubble_id.encode("ascii")).digest()
            seed = int.from_bytes(seed_bytes[:4], "big")
            b = Bubble(bubble_id=bubble_id, spawned_at_ms=now_ms(), kind=kind, seed=seed)
            self._bubbles[bubble_id] = b
            self._spawn_index += 1
            spawn_idx = self._spawn_index

        for bid in to_despawn:
            await self._broadcast(ServerMessage(
                type=MsgType.BUBBLE_DESPAWN,
                payload={"bubble_id": bid, "reason": "expired"},
            ))
        await self._broadcast(ServerMessage(
            type=MsgType.BUBBLE_SPAWN,
            payload={"spawn_index": spawn_idx, "bubbles": [b.to_public()]},
        ))
        return bubble_id

    async def _wait_group_done(self) -> None:
        """Block until all currently alive bubbles are gone (resolved or expired)."""
        while self._running:
            async with self._lock:
                now = now_ms()
                alive = [
                    b for b in self._bubbles.values()
                    if not b.resolved and not b.is_expired(now)
                ]
            if not alive:
                return
            await asyncio.sleep(0.2)

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

            server_age = b.age_sec()
            reaction = server_age
            if not config.BUBBLE_USE_SERVER_TIME and client_ts is not None:
                try:
                    cts = float(client_ts)
                except (TypeError, ValueError):
                    cts = None
                if cts is not None and 0.0 <= cts <= (
                    config.BUBBLE_MAX_CLIENT_LATENCY_SEC + config.BUBBLE_LIFETIME_SEC
                ):
                    if cts <= server_age + config.BUBBLE_MAX_CLIENT_LATENCY_SEC:
                        reaction = cts

            if reaction < config.BUBBLE_REACTION_TIME_MIN_SEC:
                return ClickOutcome.rejected(ClickOutcomeKind.TOO_FAST, bubble_id)

            b.resolved = True
            b.popped_by = player_id

            cap = (config.BUBBLE_GOLD_REWARD_COINS * 10
                if b.kind == "gold"
                else config.BUBBLE_REWARD_COINS * 10)
            coins = max(1, min(int(client_coins), cap))

            self._bubbles.pop(bubble_id, None)
            kind = b.kind

        new_balance = await self._coin_award(player_id, coins)
        await self._broadcast(ServerMessage(
            type=MsgType.BUBBLE_RESULT,
            payload={
                "bubble_id": bubble_id,
                "winner_player_id": player_id,
                "coins_awarded": coins,
                "new_balance": new_balance,
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