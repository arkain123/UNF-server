from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MsgType(str, Enum):
    # client to server
    SET_NICKNAME = "set_nickname"
    CREATE_ROOM  = "create_room"
    JOIN_ROOM    = "join_room"
    LEAVE_ROOM   = "leave_room"
    SET_READY    = "set_ready"
    START_MATCH  = "start_match"

    # client -> server (game)
    TRAIN_CARD     = "train_card"
    CARD_LEVEL_UP  = "card_level_up"
    USE_CARD       = "use_card"
    BUBBLE_CLICK   = "bubble_click"
    DAMAGE_DEALT   = "damage_dealt"
    EFFECT_APPLIED = "effect_applied"
    MATCH_ENDED = "match_ended"

    # server to client (lobby)
    NICKNAME_SET   = "nickname_set"
    NICKNAME_ERROR = "nickname_error"
    ROOM_CREATED   = "room_created"
    ROOM_JOINED    = "room_joined"
    ROOM_STATE     = "room_state"
    ROOM_LEFT      = "room_left"
    ROOM_ERROR     = "room_error"
    OPPONENT_LEFT  = "opponent_left"
    MATCH_STARTING = "match_starting"

    # server -> client (game)
    CARD_TRAINED       = "card_trained"
    CARD_LEVEL_UPDATED = "card_level_updated"
    CARD_USED          = "card_used"
    CARD_ERROR         = "card_error"

    BUBBLE_SPAWN   = "bubble_spawn"
    BUBBLE_DESPAWN = "bubble_despawn"
    BUBBLE_RESULT  = "bubble_result"
    BUBBLE_ERROR   = "bubble_error"
    COIN_UPDATE    = "coin_update"

    DAMAGE_APPLIED   = "damage_applied"
    EFFECT_CONFIRMED = "effect_confirmed"

    MATCH_STARTED = "match_started"
    MATCH_ENDED   = "match_ended"


@dataclass
class ClientMessage:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServerMessage:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if hasattr(self.type, "value"):
            self.type = self.type.value