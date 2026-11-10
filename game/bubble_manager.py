from __future__ import annotations

import asyncio
import logging
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

    # ---------- spawn loop ----------

    async def _spawn_loop(self) -> None:
        try:
            while self._running:
                await asyncio.sleep(config.BUBBLE_SPAWN_INTERVAL_SEC)
                if not self._running:
                    break
                await self._tick()
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("bubble spawn loop crashed room=%s", self.room_id)

    async def _tick(self) -> None:
        now = now_ms()

        # Expire stale bubbles.
        for b in list(self._bubbles.values()):
            if not b.resolved and b.is_expired(now):
                self._bubbles.pop(b.bubble_id, None)
                await self._broadcast(ServerMessage(
                    type=MsgType.BUBBLE_DESPAWN,
                    payload={"bubble_id": b.bubble_id, "reason": "expired"},
                ))

        # Respect concurrent cap.
        active = sum(1 for b in self._bubbles.values() if not b.resolved)
        if active >= config.BUBBLE_MAX_ACTIVE:
            return

        batch: list[Bubble] = []
        spawn_now = now_ms()
        for _ in range(config.BUBBLES_PER_SPAWN):
            if active + len(batch) >= config.BUBBLE_MAX_ACTIVE:
                break
            b = Bubble(bubble_id=uuid.uuid4().hex, spawned_at_ms=spawn_now)
            self._bubbles[b.bubble_id] = b
            batch.append(b)

        if not batch:
            return

        self._spawn_index += 1
        await self._broadcast(ServerMessage(
            type=MsgType.BUBBLE_SPAWN,
            payload={
                "spawn_index": self._spawn_index,
                "bubbles": [b.to_public() for b in batch],
            },
        ))
        log.debug("room=%s spawned %d bubbles", self.room_id, len(batch))

    # ---------- click resolution ----------

    async def resolve_click(
        self, player_id: str, bubble_id: str,
        client_ts: float | None = None,
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

            # TODO: client_ts ignored — server arrival time wins.

            b.resolved = True
            b.popped_by = player_id
            coins = config.BUBBLE_REWARD_COINS

        new_balance = await self._coin_award(player_id, coins)
        await self._broadcast(ServerMessage(
            type=MsgType.BUBBLE_RESULT,
            payload={
                "bubble_id": bubble_id,
                "winner_player_id": player_id,
                "coins_awarded": coins,
                "new_balance": new_balance,
            },
        ))
        await self._broadcast(ServerMessage(
            type=MsgType.COIN_UPDATE,
            payload={
                "player_id": player_id,
                "balance": new_balance,
                "delta": coins,
            },
        ))
        return ClickOutcome.won(bubble_id, player_id, coins)