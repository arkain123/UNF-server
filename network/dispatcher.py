import logging

from network.session import Session
from protocol.messages import ClientMessage, MsgType
from rooms.room_handlers import RoomHandlers

log = logging.getLogger("unf.server")


class Dispatcher:
    def __init__(self, room_handlers: RoomHandlers):
        self.handlers = {
            MsgType.SET_NICKNAME.value: room_handlers.handle_set_nickname,
            MsgType.CREATE_ROOM.value: room_handlers.handle_create_room,
            MsgType.JOIN_ROOM.value:   room_handlers.handle_join_room,
            MsgType.LEAVE_ROOM.value:  room_handlers.handle_leave_room,
            MsgType.SET_READY.value:   room_handlers.handle_set_ready,
        }

    async def dispatch(self, session, msg):
        handler = self.handlers.get(msg.type)
        if handler is None:
            log.warning("unknown message type=%s from id=%s",
                        msg.type, session.id)
            return
        log.debug("dispatch id=%s type=%s handler=%s",
                  session.id, msg.type, handler.__name__)
        await handler(session, msg)