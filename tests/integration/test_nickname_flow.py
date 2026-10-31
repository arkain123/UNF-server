import pytest

from .ws_client import TestClient


async def test_set_nickname_then_create(ws_server):
    a = TestClient(ws_server)
    await a.connect(set_nickname=False)

    await a.send("set_nickname", {"nickname": "Alice"})
    r = await a.wait_for("nickname_set")
    assert r["payload"]["nickname"] == "Alice"

    await a.send("create_room")
    r = await a.wait_for("room_created")
    assert r["payload"]["room"]["players"][0]["display_name"] == "Alice"
    await a.close()


async def test_nickname_locked_in_room(ws_server):
    a = TestClient(ws_server)
    await a.connect()
    await a.send("create_room")
    await a.wait_for("room_created")

    await a.send("set_nickname", {"nickname": "Hacker"})
    r = await a.wait_for("nickname_error")
    assert r["payload"]["error"] == "ALREADY_IN_ROOM"
    await a.close()


async def test_create_without_nickname(ws_server):
    a = TestClient(ws_server)
    await a.connect(set_nickname=False)
    await a.send("create_room")
    r = await a.wait_for("room_error")
    assert r["payload"]["error"] == "NICKNAME_REQUIRED"
    await a.close()


async def test_join_without_nickname(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()

    b = TestClient(ws_server)
    await b.connect(set_nickname=False)

    await a.send("create_room")
    room_id = (await a.wait_for("room_created"))["payload"]["room_id"]

    await b.send("join_room", {"room_id": room_id})
    r = await b.wait_for("room_error")
    assert r["payload"]["error"] == "NICKNAME_REQUIRED"

    await a.close()
    await b.close()


@pytest.mark.parametrize("bad,code", [
    ("", "NICKNAME_TOO_SHORT"),
    ("a", "NICKNAME_TOO_SHORT"),
    ("a" * 17, "NICKNAME_TOO_LONG"),
    ("bad!", "NICKNAME_INVALID_CHARS"),
])
async def test_nickname_validation(ws_server, bad, code):
    a = TestClient(ws_server)
    await a.connect(set_nickname=False)
    await a.send("set_nickname", {"nickname": bad})
    r = await a.wait_for("nickname_error")
    assert r["payload"]["error"] == code
    await a.close()


async def test_nickname_set_twice_before_room(ws_server):
    a = TestClient(ws_server)
    await a.connect(set_nickname=False)

    await a.send("set_nickname", {"nickname": "First"})
    await a.wait_for("nickname_set")
    await a.send("set_nickname", {"nickname": "Second"})
    r = await a.wait_for("nickname_set")
    assert r["payload"]["nickname"] == "Second"

    await a.close()