from .ws_client import TestClient


async def test_join_ok(ws_server):
    a = TestClient(ws_server, "alice")
    b = TestClient(ws_server, "bob")
    await a.connect()
    await b.connect()

    await a.send("create_room")
    room_id = (await a.wait_for("room_created"))["payload"]["room_id"]

    await b.send("join_room", {"room_id": room_id})
    r = await b.wait_for("room_joined")
    assert r["payload"]["room_id"] == room_id

    st = await a.wait_for("room_state")
    names = {p["display_name"] for p in st["payload"]["room"]["players"]}
    assert names == {"alice", "bob"}
    await a.close()
    await b.close()


async def test_join_lowercase_normalized(ws_server):
    a = TestClient(ws_server, "alice")
    b = TestClient(ws_server, "bob")
    await a.connect()
    await b.connect()

    await a.send("create_room")
    room_id = (await a.wait_for("room_created"))["payload"]["room_id"]

    await b.send("join_room", {"room_id": room_id.lower()})
    r = await b.wait_for("room_joined")
    assert r["payload"]["room_id"] == room_id
    await a.close()
    await b.close()


async def test_join_unknown(ws_server):
    a = TestClient(ws_server)
    await a.connect()
    await a.send("join_room", {"room_id": "ZZZZZZ"})
    r = await a.wait_for("room_error")
    assert r["payload"]["error"] == "ROOM_NOT_FOUND"
    await a.close()


async def test_join_empty_code(ws_server):
    a = TestClient(ws_server)
    await a.connect()
    await a.send("join_room", {"room_id": ""})
    r = await a.wait_for("room_error")
    assert r["payload"]["error"] == "INVALID_ROOM_CODE"
    await a.close()


async def test_join_missing_code(ws_server):
    a = TestClient(ws_server)
    await a.connect()
    await a.send("join_room", {})
    r = await a.wait_for("room_error")
    assert r["payload"]["error"] == "INVALID_ROOM_CODE"
    await a.close()


async def test_room_full(ws_server):
    clients = [TestClient(ws_server, f"p{i}") for i in range(3)]
    for c in clients:
        await c.connect()

    a, b, c = clients
    await a.send("create_room")
    room_id = (await a.wait_for("room_created"))["payload"]["room_id"]

    await b.send("join_room", {"room_id": room_id})
    await b.wait_for("room_joined")
    await a.wait_for("room_state")

    await c.send("join_room", {"room_id": room_id})
    r = await c.wait_for("room_error")
    assert r["payload"]["error"] == "ROOM_FULL"

    for cl in clients:
        await cl.close()


async def test_join_second_room_denied(ws_server):
    a = TestClient(ws_server, "alice")
    b = TestClient(ws_server, "bob")
    c = TestClient(ws_server, "carol")
    for cl in (a, b, c):
        await cl.connect()

    await a.send("create_room")
    room_a = (await a.wait_for("room_created"))["payload"]["room_id"]

    await c.send("create_room")
    room_c = (await c.wait_for("room_created"))["payload"]["room_id"]

    await b.send("join_room", {"room_id": room_a})
    await b.wait_for("room_joined")

    await b.send("join_room", {"room_id": room_c})
    r = await b.wait_for("room_error")
    assert r["payload"]["error"] == "ALREADY_IN_ROOM"

    for cl in (a, b, c):
        await cl.close()