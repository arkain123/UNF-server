import asyncio
from enum import Enum
from rooms.player_slot import PlayerSlot
from protocol.messages import ServerMessage, MsgType

from config import ROOM_MAX_PLAYERS


class RoomState(str, Enum):
    WAITING  = "waiting"
    STARTING = "starting"
    IN_MATCH = "in_match"
    FINISHED = "finished"


class Room:
    MAX_PLAYERS = ROOM_MAX_PLAYERS

    def __init__(self, room_id: str, host_player_id: str, host_display_name: str):
        self.id = room_id
        self.state = RoomState.WAITING
        self.players: dict[str, PlayerSlot] = {}
        self.match = None
        self._lock = asyncio.Lock()
        self._next_seat = 0
        self._add_internal(host_player_id, host_display_name, is_host=True)

    # INTERNAL

    def _add_internal(self, player_id: str, display_name: str, is_host: bool) -> PlayerSlot:
        slot = PlayerSlot(
            player_id=player_id,
            display_name=display_name,
            seat=self._next_seat,
            is_host=is_host,
        )
        self._next_seat += 1
        self.players[player_id] = slot
        return slot

    def _public_state(self) -> dict:
        return {
            "room_id": self.id,
            "state": self.state.value,
            "max_players": self.MAX_PLAYERS,
            "players": [p.to_public() for p in self.players.values()],
        }

    # PUBLIC

    async def add_player(self, player_id: str, display_name: str) -> PlayerSlot:
        async with self._lock:
            if self.state != RoomState.WAITING:
                raise RoomJoinError("ROOM_ALREADY_STARTED")
            if player_id in self.players:
                raise RoomJoinError("ALREADY_IN_ROOM")
            if len(self.players) >= self.MAX_PLAYERS:
                raise RoomJoinError("ROOM_FULL")
            return self._add_internal(player_id, display_name, is_host=False)

    async def remove_player(self, player_id: str) -> bool:
        """Return True if room is empty"""
        async with self._lock:
            slot = self.players.pop(player_id, None)
            if slot is None:
                return False

            # Give Host to next player
            if slot.is_host and self.players:
                next_slot = next(iter(self.players.values()))
                next_slot.is_host = True

            return len(self.players) == 0

    async def set_ready(self, player_id: str, ready: bool) -> None:
        async with self._lock:
            slot = self.players.get(player_id)
            if slot is None:
                raise RoomJoinError("NOT_IN_ROOM")
            if self.state != RoomState.WAITING:
                raise RoomJoinError("ROOM_ALREADY_STARTED")
            slot.ready = ready

    def is_all_ready(self) -> bool:
        if len(self.players) < self.MAX_PLAYERS:
            return False
        return all(p.ready for p in self.players.values())

    def public_state(self) -> dict:
        return self._public_state()

    def get_player_ids(self) -> list[str]:
        return list(self.players.keys())


class RoomJoinError(Exception) :
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)