from .ws_client import TestClient


async def test_create_returns_room(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    await a.send("create_room")
    r = await a.wait_for("room_created")
    assert len(r["payload"]["room_id"]) == 6
    assert r["payload"]["room"]["state"] == "waiting"
    await a.close()


async def test_cannot_create_twice(ws_server):
    a = TestClient(ws_server)
    await a.connect()
    await a.send("create_room")
    await a.wait_for("room_created")
    await a.send("create_room")
    r = await a.wait_for("room_error")
    assert r["payload"]["error"] == "ALREADY_IN_ROOM"
    await a.close()


async def test_cannot_join_own_room(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    await a.send("create_room")
    room_id = (await a.wait_for("room_created"))["payload"]["room_id"]

    await a.send("join_room", {"room_id": room_id})
    r = await a.wait_for("room_error")
    assert r["payload"]["error"] == "ALREADY_IN_ROOM"
    await a.close()