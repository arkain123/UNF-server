import pytest

from rooms.room import Room, RoomJoinError, RoomState


@pytest.fixture
def room():
    return Room(room_id="ABC123",
                host_player_id="p1",
                host_display_name="Alice")


def test_host_is_first(room):
    assert "p1" in room.players
    p = room.players["p1"]
    assert p.is_host is True
    assert p.display_name == "Alice"
    assert p.seat == 0
    assert room.state == RoomState.WAITING


async def test_add_second_player(room):
    slot = await room.add_player("p2", "Bob")
    assert slot.seat == 1
    assert slot.is_host is False
    assert len(room.players) == 2


async def test_room_full(room):
    await room.add_player("p2", "Bob")
    with pytest.raises(RoomJoinError) as e:
        await room.add_player("p3", "Carol")
    assert e.value.code == "ROOM_FULL"


async def test_no_duplicate_join(room):
    with pytest.raises(RoomJoinError) as e:
        await room.add_player("p1", "Alice2")
    assert e.value.code == "ALREADY_IN_ROOM"


async def test_join_after_start(room):
    room.state = RoomState.STARTING
    with pytest.raises(RoomJoinError) as e:
        await room.add_player("p2", "Bob")
    assert e.value.code == "ROOM_ALREADY_STARTED"


async def test_ready_requires_membership(room):
    with pytest.raises(RoomJoinError) as e:
        await room.set_ready("ghost", True)
    assert e.value.code == "NOT_IN_ROOM"


async def test_ready_in_non_waiting_state(room):
    room.state = RoomState.IN_MATCH
    with pytest.raises(RoomJoinError) as e:
        await room.set_ready("p1", True)
    assert e.value.code == "ROOM_ALREADY_STARTED"


async def test_is_all_ready_false_when_one(room):
    await room.set_ready("p1", True)
    assert room.is_all_ready() is False


async def test_is_all_ready_false_when_partial(room):
    await room.add_player("p2", "Bob")
    await room.set_ready("p1", True)
    await room.set_ready("p2", False)
    assert room.is_all_ready() is False


async def test_is_all_ready_true(room):
    await room.add_player("p2", "Bob")
    await room.set_ready("p1", True)
    await room.set_ready("p2", True)
    assert room.is_all_ready() is True


async def test_host_migration(room):
    await room.add_player("p2", "Bob")
    empty = await room.remove_player("p1")
    assert empty is False
    assert room.players["p2"].is_host is True
    assert len(room.players) == 1


async def test_remove_unknown_player(room):
    empty = await room.remove_player("ghost")
    assert empty is False
    assert len(room.players) == 1


async def test_remove_last_player_returns_empty(room):
    empty = await room.remove_player("p1")
    assert empty is True
    assert room.players == {}


def test_public_state_format(room):
    st = room.public_state()
    assert st["room_id"] == "ABC123"
    assert st["state"] == "waiting"
    assert st["max_players"] == 2
    assert len(st["players"]) == 1
    p = st["players"][0]
    assert set(p) == {"player_id", "display_name", "seat", "is_host", "ready"}


def test_get_player_ids(room):
    assert room.get_player_ids() == ["p1"]