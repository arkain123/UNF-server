from network.session import Session, SessionManager
from rooms.room_manager import RoomManager
from rooms.room import Room, RoomJoinError
from rooms.nickname import validate_nickname
from protocol.messages import ClientMessage, ServerMessage, MsgType


class RoomHandlers:
    def __init__(self, sessions: SessionManager, rooms: RoomManager):
        self.sessions = sessions
        self.rooms = rooms

    # HELPERS

    async def _send(self, session: Session, msg: ServerMessage) -> None:
        await session.connection.send(msg)

    def _room_state_msg(self, room: Room) -> ServerMessage:
        return ServerMessage(
            type=MsgType.ROOM_STATE,
            payload={"room": room.public_state()},
        )

    async def _broadcast_room(self, room: Room) -> None:
        msg = self._room_state_msg(room)
        for pid in room.get_player_ids():
            s = self.sessions.get_by_player(pid)
            if s:
                await self._send(s, msg)

    async def handle_set_nickname(
        self, session: Session, msg: ClientMessage
    ) -> None:
        if session.room_id is not None:
            return await self._send(session, ServerMessage(
                type=MsgType.NICKNAME_ERROR,
                payload={"error": "ALREADY_IN_ROOM"},
            ))

        raw = msg.payload.get("nickname", "")
        nick, err = validate_nickname(raw)
        if err:
            return await self._send(session, ServerMessage(
                type=MsgType.NICKNAME_ERROR,
                payload={"error": err},
            ))

        session.nickname = nick
        await self._send(session, ServerMessage(
            type=MsgType.NICKNAME_SET,
            payload={"nickname": nick},
        ))

    # ---------- create_room ----------

    async def handle_create_room(
        self, session: Session, msg: ClientMessage
    ) -> None:
        if not session.authenticated:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "NOT_AUTHENTICATED"},
            ))
        if session.room_id is not None:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "ALREADY_IN_ROOM"},
            ))
        if session.nickname is None:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "NICKNAME_REQUIRED"},
            ))

        room = await self.rooms.create_room(session.player_id, session.nickname)
        self.sessions.bind_room(session, room.id)

        await self._send(session, ServerMessage(
            type=MsgType.ROOM_CREATED,
            payload={"room_id": room.id, "room": room.public_state()},
        ))

    # ---------- join_room ----------

    async def handle_join_room(
        self, session: Session, msg: ClientMessage
    ) -> None:
        if not session.authenticated:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "NOT_AUTHENTICATED"},
            ))
        if session.room_id is not None:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "ALREADY_IN_ROOM"},
            ))
        if session.nickname is None:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "NICKNAME_REQUIRED"},
            ))

        room_code = (msg.payload.get("room_id") or "").strip().upper()
        if not room_code:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "INVALID_ROOM_CODE"},
            ))

        try:
            room = await self.rooms.join_room(
                session.player_id, session.nickname, room_code,
            )
        except RoomJoinError as e:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": e.code},
            ))

        self.sessions.bind_room(session, room.id)

        await self._send(session, ServerMessage(
            type=MsgType.ROOM_JOINED,
            payload={"room_id": room.id, "room": room.public_state()},
        ))

        await self._broadcast_room(room)

    # ---------- leave_room ----------

    async def handle_leave_room(
        self, session: Session, msg: ClientMessage
    ) -> None:
        if session.room_id is None:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "NOT_IN_ROOM"},
            ))

        room_id = session.room_id
        room = self.rooms.find_room(room_id)
        removed = await self.rooms.leave_room(session.player_id, room_id)
        self.sessions.unbind_room(session)

        await self._send(session, ServerMessage(
            type=MsgType.ROOM_LEFT,
            payload={"room_id": room_id},
        ))

        if room and not removed:
            for pid in room.get_player_ids():
                s = self.sessions.get_by_player(pid)
                if s:
                    await self._send(s, ServerMessage(
                        type=MsgType.OPPONENT_LEFT,
                        payload={
                            "player_id": session.player_id,
                            "display_name": session.nickname
                        },
                    ))
            await self._broadcast_room(room)

    # ---------- set_ready ----------

    async def handle_set_ready(
        self, session: Session, msg: ClientMessage
    ) -> None:
        if session.room_id is None:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "NOT_IN_ROOM"},
            ))

        room = self.rooms.find_room(session.room_id)
        if room is None:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "ROOM_NOT_FOUND"},
            ))

        ready = bool(msg.payload.get("ready", True))
        try:
            await room.set_ready(session.player_id, ready)
        except RoomJoinError as e:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": e.code},
            ))

        await self._broadcast_room(room)

    # ---------- start_match ----------

    async def handle_start_match(
        self, session: Session, msg: ClientMessage
    ) -> None:
        if session.room_id is None:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "NOT_IN_ROOM"},
            ))

        room = self.rooms.find_room(session.room_id)
        if room is None:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "ROOM_NOT_FOUND"},
            ))

        slot = room.players.get(session.player_id)
        if slot is None or not slot.is_host:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "HOST_REQUIRED"},
            ))

        if room.state != room.state.__class__.WAITING:
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "ROOM_ALREADY_STARTED"},
            ))

        if not room.can_start():
            return await self._send(session, ServerMessage(
                type=MsgType.ROOM_ERROR,
                payload={"error": "NOT_ALL_READY"},
            ))

        await self._start_match(room)

    async def _start_match(self, room: Room) -> None:
        try:
            room.mark_starting()
        except RoomJoinError as e:
            return
        # TODO: match = Match(room, ...); await match.start()
        for pid in room.get_player_ids():
            s = self.sessions.get_by_player(pid)
            if s:
                await self._send(s, ServerMessage(
                    type=MsgType.MATCH_STARTING,
                    payload={"room_id": room.id},
                ))