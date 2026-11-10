from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

import config
from game.bubble_manager import BubbleManager
from game.card import CardInventory
from game.card_manager import CardManager
from protocol.messages import MsgType, ServerMessage

log = logging.getLogger("unf.game.match")

BroadcastFn = Callable[[ServerMessage], Awaitable[None]]


class Match:
    def __init__(self, room, broadcast_fn: BroadcastFn):
        self.room = room
        self.room_id = room.id
        self._broadcast = broadcast_fn

        self.cards: dict[str, CardInventory] = {}
        self.coins: dict[str, int] = {}
        self.card_manager = CardManager(self.room_id)
        self.bubbles = BubbleManager(
            room_id=self.room_id,
            broadcast=broadcast_fn,
            coin_award=self._award_coins,
        )
        self._round_task: asyncio.Task | None = None
        self._running = False

    # ---------- lifecycle ----------

    async def start(self) -> None:
        if self._running:
            return
        self._running = True

        for pid in self.room.get_player_ids():
            self.cards[pid] = CardInventory()
            self.coins.setdefault(pid, 0)

        await self.bubbles.start()

        if config.BUBBLE_ROUND_DURATION_SEC > 0:
            self._round_task = asyncio.create_task(self._round_timer())

        await self._broadcast(ServerMessage(
            type=MsgType.MATCH_STARTED,
            payload={"room_id": self.room_id},
        ))
        log.info("match started room=%s", self.room_id)

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._round_task:
            self._round_task.cancel()
            try:
                await self._round_task
            except asyncio.CancelledError:
                pass
            self._round_task = None
        await self.bubbles.stop()
        await self._broadcast(ServerMessage(
            type=MsgType.MATCH_ENDED,
            payload={
                "room_id": self.room_id,
                "coins": dict(self.coins),
            },
        ))
        log.info("match stopped room=%s", self.room_id)

    async def _round_timer(self) -> None:
        try:
            await asyncio.sleep(config.BUBBLE_ROUND_DURATION_SEC)
            if self._running:
                await self.stop()
        except asyncio.CancelledError:
            pass

    # ---------- helpers ----------

    def inventory(self, player_id: str) -> CardInventory:
        inv = self.cards.get(player_id)
        if inv is None:
            inv = CardInventory()
            self.cards[player_id] = inv
        return inv

    def balance(self, player_id: str) -> int:
        return self.coins.get(player_id, 0)

    async def _award_coins(self, player_id: str, coins: int) -> int:
        new_balance = self.coins.get(player_id, 0) + coins
        self.coins[player_id] = new_balance
        return new_balance