import secrets
import string
import asyncio
import config

from rooms.room import Room, RoomState, RoomJoinError


class RoomManager:

    def __init__(self):
        self.rooms: dict[str, Room] = {}
        self._lock = asyncio.Lock()
    
    # HELPERS

    def _generate_code(self) -> str:
        while True:
            code = "".join(
                secrets.choice(config.ROOM_CODE_ALPHABET)
                for _ in range(config.ROOM_CODE_LEN)
            )
            if code not in self.rooms:
                return code

    # CRUD

    async def create_room(self, host_player_id: str, host_display_name: str) -> Room:
        async with self._lock:
            code = self._generate_code()
            room = Room(
                room_id=code,
                host_player_id=host_player_id,
                host_display_name=host_display_name,
            )
            self.rooms[code] = room
            return room

    def find_room(self, room_id: str) -> Room | None:
        return self.rooms.get(room_id.upper())

    async def join_room(self, player_id: str, display_name: str, room_id: str) -> Room:
        room = self.find_room(room_id)
        if room is None:
            raise RoomJoinError("ROOM_NOT_FOUND")
        await room.add_player(player_id, display_name)
        return room

    async def leave_room(self, player_id: str, room_id: str) -> bool:
        room = self.find_room(room_id)
        if room is None:
            return False
        empty = await room.remove_player(player_id)
        if empty:
            async with self._lock:
                self.rooms.pop(room_id, None)
        return empty

    async def destroy_room(self, room_id: str) -> None:
        async with self._lock:
            self.rooms.pop(room_id, None)
