from .ws_client import TestClient


async def test_disconnect_removes_from_room(ws_server):
    a = TestClient(ws_server, "alice")
    b = TestClient(ws_server, "bob")
    await a.connect()
    await b.connect()

    await a.send("create_room")
    room_id = (await a.wait_for("room_created"))["payload"]["room_id"]
    await b.send("join_room", {"room_id": room_id})
    await b.wait_for("room_joined")
    await a.wait_for("room_state")

    await a.close()

    left = await b.wait_for("opponent_left", timeout=3.0)
    assert left["payload"]["player_id"]
    st = await b.wait_for("room_state")
    assert len(st["payload"]["room"]["players"]) == 1

    await b.close()


async def test_disconnect_empty_room_destroyed(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    await a.send("create_room")
    room_id = (await a.wait_for("room_created"))["payload"]["room_id"]

    await a.close()

    b = TestClient(ws_server, "bob")
    await b.connect()
    await b.send("join_room", {"room_id": room_id})
    r = await b.wait_for("room_error")
    assert r["payload"]["error"] == "ROOM_NOT_FOUND"
    await b.close()