import pytest

from rooms.room_manager import RoomManager
from rooms.room import RoomJoinError


async def test_create_returns_room():
    mgr = RoomManager()
    room = await mgr.create_room("p1", "Alice")
    assert room.id in mgr.rooms
    assert len(room.id) == 6
    assert room.players["p1"].is_host is True


async def test_codes_are_unique():
    mgr = RoomManager()
    ids = set()
    for i in range(50):
        room = await mgr.create_room(f"p{i}", f"P{i}")
        ids.add(room.id)
    assert len(ids) == 50


async def test_codes_use_safe_alphabet():
    from config import ROOM_CODE_ALPHABET
    mgr = RoomManager()
    for _ in range(30):
        room = await mgr.create_room("p", "P")
        assert all(c in ROOM_CODE_ALPHABET for c in room.id)


async def test_join_unknown():
    mgr = RoomManager()
    with pytest.raises(RoomJoinError) as e:
        await mgr.join_room("p2", "Bob", "ZZZZZZ")
    assert e.value.code == "ROOM_NOT_FOUND"


async def test_join_normalizes_case():
    mgr = RoomManager()
    room = await mgr.create_room("p1", "Alice")
    # find_room делает .upper()
    assert mgr.find_room(room.id.lower()) is room


async def test_leave_destroys_empty_room():
    mgr = RoomManager()
    room = await mgr.create_room("p1", "Alice")
    removed = await mgr.leave_room("p1", room.id)
    assert removed is True
    assert mgr.find_room(room.id) is None


async def test_leave_unknown_room_returns_false():
    mgr = RoomManager()
    removed = await mgr.leave_room("p1", "ZZZZZZ")
    assert removed is False


async def test_destroy_room():
    mgr = RoomManager()
    room = await mgr.create_room("p1", "Alice")
    await mgr.destroy_room(room.id)
    assert mgr.find_room(room.id) is None