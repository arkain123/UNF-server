import json
import logging

from websockets.exceptions import ConnectionClosed

import config
from network.connection import Connection
from network.session import SessionManager
from network.dispatcher import Dispatcher
from rooms.room_manager import RoomManager
from protocol.messages import ClientMessage, ServerMessage, MsgType

log = logging.getLogger("unf.server")


class WebSocketHandler:
    def __init__(self, sessions: SessionManager, rooms: RoomManager,
                 dispatcher: Dispatcher):
        self.sessions = sessions
        self.rooms = rooms
        self.dispatcher = dispatcher

    async def handle(self, ws):
        conn = Connection(ws)
        session = self.sessions.create(conn)
        self.sessions.authenticate(session, player_id=conn.id)

        peer = getattr(ws, "remote_address", None)
        log.info("connection open id=%s peer=%s", conn.id, peer)

        try:
            async for raw in ws:
                if len(raw) > config.MAX_MESSAGE_BYTES:
                    log.warning("recv too big id=%s size=%dB", conn.id, len(raw))
                    continue

                try:
                    data = json.loads(raw)
                    msg = ClientMessage(
                        type=data["type"],
                        payload=data.get("payload", {}),
                    )
                except (KeyError, json.JSONDecodeError, TypeError) as e:
                    log.warning("recv invalid id=%s error=%s raw=%r",
                                conn.id, e, raw[:200])
                    continue

                log.info("recv id=%s type=%s payload=%s",
                         conn.id, msg.type, msg.payload)

                await self.dispatcher.dispatch(session, msg)

        except ConnectionClosed:
            pass
        finally:
            await self._cleanup(session)
            log.info("connection closed id=%s", conn.id)

    async def _cleanup(self, session):
        if session.room_id:
            room = self.rooms.find_room(session.room_id)
            removed = await self.rooms.leave_room(session.player_id, session.room_id)
            if room and not removed:
                for pid in room.get_player_ids():
                    s = self.sessions.get_by_player(pid)
                    if s:
                        await s.connection.send(ServerMessage(
                            type=MsgType.OPPONENT_LEFT,
                            payload={
                                "player_id": session.player_id,
                                "display_name": session.nickname,
                            },
                        ))
                state_msg = ServerMessage(
                    type=MsgType.ROOM_STATE,
                    payload={"room": room.public_state()},
                )
                for pid in room.get_player_ids():
                    s = self.sessions.get_by_player(pid)
                    if s:
                        await s.connection.send(state_msg)
            log.info("cleanup id=%s room=%s removed=%s",
                     session.id, session.room_id, removed)
        self.sessions.destroy(session)