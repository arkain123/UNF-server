import logging

from network.session import Session
from protocol.messages import ClientMessage, MsgType
from rooms.room_handlers import RoomHandlers

log = logging.getLogger("unf.server")


class Dispatcher:
    def __init__(self, room_handlers: RoomHandlers, match_handlers=None):
        self.handlers = {
            MsgType.SET_NICKNAME.value: room_handlers.handle_set_nickname,
            MsgType.CREATE_ROOM.value:  room_handlers.handle_create_room,
            MsgType.JOIN_ROOM.value:    room_handlers.handle_join_room,
            MsgType.LEAVE_ROOM.value:   room_handlers.handle_leave_room,
            MsgType.SET_READY.value:    room_handlers.handle_set_ready,
            MsgType.START_MATCH.value:  room_handlers.handle_start_match,
        }
        if match_handlers is not None:
            self.handlers.update({
                MsgType.TRAIN_CARD.value:     match_handlers.handle_train_card,
                MsgType.CARD_LEVEL_UP.value:  match_handlers.handle_card_level_up,
                MsgType.USE_CARD.value:       match_handlers.handle_use_card,
                MsgType.BUBBLE_CLICK.value:   match_handlers.handle_bubble_click,
                MsgType.DAMAGE_DEALT.value:   match_handlers.handle_damage_dealt,
                MsgType.EFFECT_APPLIED.value: match_handlers.handle_effect_applied,
            })

    async def dispatch(self, session: Session, msg: ClientMessage):
        handler = self.handlers.get(msg.type)
        if handler is None:
            log.warning("unknown message type=%s payload=%s from id=%s",
                        msg.type, msg.payload, session.id)
            return
        log.debug("dispatch id=%s type=%s handler=%s",
                  session.id, msg.type, handler.__name__)
        await handler(session, msg)