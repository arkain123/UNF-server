from .ws_client import TestClient


async def test_leave_returns_ack(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    await a.send("create_room")
    await a.wait_for("room_created")

    await a.send("leave_room")
    r = await a.wait_for("room_left")
    assert r["payload"]["room_id"]
    await a.close()


async def test_leave_when_not_in_room(ws_server):
    a = TestClient(ws_server)
    await a.connect()
    await a.send("leave_room")
    r = await a.wait_for("room_error")
    assert r["payload"]["error"] == "NOT_IN_ROOM"
    await a.close()


async def test_leave_host_migrates(ws_server):
    a = TestClient(ws_server, "alice")
    b = TestClient(ws_server, "bob")
    await a.connect()
    await b.connect()

    await a.send("create_room")
    room_id = (await a.wait_for("room_created"))["payload"]["room_id"]
    await b.send("join_room", {"room_id": room_id})
    await b.wait_for("room_joined")
    await a.wait_for("room_state")

    await a.send("leave_room")

    left = await b.wait_for("opponent_left")
    assert left["payload"]["player_id"]
    assert left["payload"].get("display_name") == "alice"

    st = await b.wait_for("room_state")
    players = st["payload"]["room"]["players"]
    assert len(players) == 1
    assert players[0]["display_name"] == "bob"
    assert players[0]["is_host"] is True

    await a.close()
    await b.close()


async def test_leave_can_rejoin_new_room(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()

    await a.send("create_room")
    await a.wait_for("room_created")
    await a.send("leave_room")
    await a.wait_for("room_left")

    await a.send("create_room")
    r = await a.wait_for("room_created")
    assert r["payload"]["room_id"]
    await a.close()