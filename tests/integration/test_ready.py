from .ws_client import TestClient


async def test_both_ready_starts_match(ws_server):
    a = TestClient(ws_server, "alice")
    b = TestClient(ws_server, "bob")
    await a.connect()
    await b.connect()

    await a.send("create_room")
    room_id = (await a.wait_for("room_created"))["payload"]["room_id"]
    await b.send("join_room", {"room_id": room_id})
    await b.wait_for("room_joined")
    await a.wait_for("room_state")

    await a.send("set_ready", {"ready": True})
    await a.wait_for("room_state")
    await b.wait_for("room_state")

    await b.send("set_ready", {"ready": True})
    sa = await a.wait_for("match_starting")
    sb = await b.wait_for("match_starting")
    assert sa["payload"]["room_id"] == room_id
    assert sb["payload"]["room_id"] == room_id

    await a.close()
    await b.close()


async def test_unready_keeps_room_waiting(ws_server):
    a = TestClient(ws_server, "alice")
    b = TestClient(ws_server, "bob")
    await a.connect()
    await b.connect()

    await a.send("create_room")
    room_id = (await a.wait_for("room_created"))["payload"]["room_id"]
    await b.send("join_room", {"room_id": room_id})
    await b.wait_for("room_joined")
    await a.wait_for("room_state")

    await a.send("set_ready", {"ready": True})
    await a.wait_for("room_state")
    await b.wait_for("room_state")
    await a.send("set_ready", {"ready": False})

    st = await a.wait_for("room_state")
    flags = {p["display_name"]: p["ready"]
             for p in st["payload"]["room"]["players"]}
    assert flags == {"alice": False, "bob": False}

    await a.close()
    await b.close()


async def test_join_after_start_fails(ws_server):
    a = TestClient(ws_server, "alice")
    b = TestClient(ws_server, "bob")
    c = TestClient(ws_server, "carol")
    await a.connect()
    await b.connect()
    await c.connect()

    await a.send("create_room")
    room_id = (await a.wait_for("room_created"))["payload"]["room_id"]
    await b.send("join_room", {"room_id": room_id})
    await b.wait_for("room_joined")
    await a.wait_for("room_state")

    await a.send("set_ready", {"ready": True})
    await a.wait_for("room_state")
    await b.wait_for("room_state")
    await b.send("set_ready", {"ready": True})
    await a.wait_for("match_starting")
    await b.wait_for("match_starting")

    await c.send("join_room", {"room_id": room_id})
    r = await c.wait_for("room_error")
    assert r["payload"]["error"] == "ROOM_ALREADY_STARTED"

    for cl in (a, b, c):
        await cl.close()


async def test_ready_when_not_in_room(ws_server):
    a = TestClient(ws_server)
    await a.connect()
    await a.send("set_ready", {"ready": True})
    r = await a.wait_for("room_error")
    assert r["payload"]["error"] == "NOT_IN_ROOM"
    await a.close()