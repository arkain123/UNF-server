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

    # server to client
    NICKNAME_SET   = "nickname_set"
    NICKNAME_ERROR = "nickname_error"
    ROOM_CREATED   = "room_created"
    ROOM_JOINED    = "room_joined"
    ROOM_STATE     = "room_state"
    ROOM_LEFT      = "room_left"
    ROOM_ERROR     = "room_error"
    OPPONENT_LEFT  = "opponent_left"


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
    