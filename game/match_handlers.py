from __future__ import annotations

import logging

from network.session import Session, SessionManager
from rooms.room_manager import RoomManager
from protocol.messages import ClientMessage, ServerMessage, MsgType
from game.bubble import ClickOutcomeKind
from game.card_manager import CardError

log = logging.getLogger("unf.game.handlers")


class MatchHandlers:
    def __init__(self, sessions: SessionManager, rooms: RoomManager):
        self.sessions = sessions
        self.rooms = rooms
        self.matches: dict[str, "Match"] = {}   # room_id -> Match

    # ---------- helpers ----------

    async def _send(self, session: Session, msg: ServerMessage) -> None:
        await session.connection.send(msg)

    async def _broadcast(self, room_id: str, msg: ServerMessage) -> None:
        room = self.rooms.find_room(room_id)
        if room is None:
            return
        for pid in room.get_player_ids():
            s = self.sessions.get_by_player(pid)
            if s:
                await self._send(s, msg)

    def _match_for(self, session: Session):
        if session.room_id is None:
            return None
        return self.matches.get(session.room_id)

    async def _require_match(self, session: Session):
        m = self._match_for(session)
        if m is None:
            await self._send(session, ServerMessage(
                type=MsgType.CARD_ERROR,
                payload={"error": "NOT_IN_MATCH"},
            ))
        return m

    # ---------- card handlers ----------

    async def handle_train_card(
        self, session: Session, msg: ClientMessage
    ) -> None:
        m = await self._require_match(session)
        if m is None:
            return

        card_id = msg.payload.get("card_id", "")
        level = msg.payload.get("card_level")
        try:
            card = m.card_manager.train(
                m.inventory(session.player_id), card_id, level,
            )
        except CardError as e:
            return await self._send(session, ServerMessage(
                type=MsgType.CARD_ERROR,
                payload={"error": e.code},
            ))

        await self._send(session, ServerMessage(
            type=MsgType.CARD_TRAINED,
            payload={"card_id": card.card_id, "level": card.level},
        ))

    async def handle_card_level_up(
        self, session: Session, msg: ClientMessage
    ) -> None:
        m = await self._require_match(session)
        if m is None:
            return

        card_id = msg.payload.get("card_id", "")
        new_level = msg.payload.get("new_level", 0)
        try:
            card, changed = m.card_manager.apply_level_up(
                m.inventory(session.player_id), card_id, new_level,
            )
        except CardError as e:
            return await self._send(session, ServerMessage(
                type=MsgType.CARD_ERROR,
                payload={"error": e.code},
            ))

        # Always push the authoritative (id, level) - client is a cache.
        await self._send(session, ServerMessage(
            type=MsgType.CARD_LEVEL_UPDATED,
            payload={"card_id": card.card_id, "level": card.level},
        ))
        if changed:
            log.info("room=%s player=%s card=%s -> level %d",
                     m.room_id, session.player_id, card.card_id, card.level)

    async def handle_use_card(
        self, session: Session, msg: ClientMessage
    ) -> None:
        m = await self._require_match(session)
        if m is None:
            return

        card_id = msg.payload.get("card_id", "")
        level = msg.payload.get("card_level", 0)
        target = msg.payload.get("target_player_id", "")

        try:
            card = m.card_manager.validate_use(
                m.inventory(session.player_id), card_id, level,
            )
        except CardError as e:
            return await self._send(session, ServerMessage(
                type=MsgType.CARD_ERROR,
                payload={"error": e.code},
            ))

        await self._broadcast(m.room_id, ServerMessage(
            type=MsgType.CARD_USED,
            payload={
                "card_id": card.card_id,
                "level": card.level,
                "by_player_id": session.player_id,
                "target_player_id": target,
            },
        ))

    # ---------- bubble handlers ----------

    async def handle_bubble_click(
        self, session: Session, msg: ClientMessage
    ) -> None:
        m = await self._require_match(session)
        if m is None:
            return

        bubble_id = msg.payload.get("bubble_id", "")
        client_ts = msg.payload.get("client_ts")
        outcome = await m.bubbles.resolve_click(
            player_id=session.player_id,
            bubble_id=bubble_id,
            client_ts=float(client_ts) if client_ts is not None else None,
        )

        if outcome.kind is ClickOutcomeKind.WON:
            return

        await self._send(session, ServerMessage(
            type=MsgType.BUBBLE_ERROR,
            payload={"bubble_id": bubble_id, "error": outcome.kind.name},
        ))