import json

from .ws_client import TestClient


async def test_invalid_json_ignored(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    await a.ws.send("not-json-at-all")
    await a.send("create_room")
    r = await a.wait_for("room_created")
    assert r["payload"]["room_id"]
    await a.close()


async def test_missing_type_ignored(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    await a.ws.send(json.dumps({"payload": {"x": 1}}))
    await a.send("create_room")
    r = await a.wait_for("room_created")
    assert r["payload"]["room_id"]
    await a.close()


async def test_non_object_json_ignored(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    await a.ws.send(json.dumps([1, 2, 3]))
    await a.ws.send(json.dumps(42))
    await a.ws.send(json.dumps("string"))
    await a.send("create_room")
    r = await a.wait_for("room_created")
    assert r["payload"]["room_id"]
    await a.close()


async def test_unknown_type_ignored(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    await a.send("totally_unknown_action", {"x": 1})
    await a.send("create_room")
    r = await a.wait_for("room_created")
    assert r["payload"]["room_id"]
    await a.close()


async def test_oversized_message_ignored(ws_server):
    import config

    a = TestClient(ws_server, "alice")
    await a.connect()

    huge = json.dumps({
        "type": "create_room",
        "payload": {"junk": "x" * (config.MAX_MESSAGE_BYTES + 100)},
    })
    assert len(huge) > config.MAX_MESSAGE_BYTES

    await a.ws.send(huge)
    await a.no_message(timeout=0.3)

    await a.send("create_room")
    r = await a.wait_for("room_created")
    assert r["payload"]["room_id"]
    await a.close()


async def test_payload_not_dict_tolerated(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect(set_nickname=False)

    await a.ws.send(json.dumps({
        "type": "set_nickname",
        "payload": "Alice",
    }))
    await a.send("set_nickname", {"nickname": "Alice"})
    r = await a.wait_for("nickname_set")
    assert r["payload"]["nickname"] == "Alice"
    await a.close()


async def test_empty_message_ignored(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    await a.ws.send("")
    await a.send("create_room")
    r = await a.wait_for("room_created")
    assert r["payload"]["room_id"]
    await a.close()


async def test_multiple_bad_then_good(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    for bad in ["{", "}", "[]", "null", "true", "123"]:
        await a.ws.send(bad)
    await a.send("create_room")
    r = await a.wait_for("room_created")
    assert r["payload"]["room_id"]
    await a.close()