import pytest
import asyncio

from tests.integration.ws_client import TestClient


async def _setup_ready_room(ws_server):
    a = TestClient(ws_server, "alice")
    b = TestClient(ws_server, "bob")
    await a.connect()
    await b.connect()

    await a.send("set_nickname", {"nickname": "Alice"})
    await a.wait_for("nickname_set", timeout=3.0)
    await b.send("set_nickname", {"nickname": "Bob"})
    await b.wait_for("nickname_set", timeout=3.0)

    await a.send("create_room")
    room_id = (await a.wait_for("room_created"))["payload"]["room_id"]
    await b.send("join_room", {"room_id": room_id})
    await b.wait_for("room_joined")
    await a.wait_for("room_state")

    await a.send("set_ready", {"ready": True})
    await b.send("set_ready", {"ready": True})

    deadline = asyncio.get_event_loop().time() + 3.0
    while asyncio.get_event_loop().time() < deadline:
        try:
            st = await a.wait_for("room_state", timeout=1.0)
        except asyncio.TimeoutError:
            break
        players = st["payload"]["room"]["players"]
        if len(players) == 2 and all(p["ready"] for p in players):
            break
    else:
        raise AssertionError("both players never became ready")

    return a, b, room_id


async def test_start_match_broadcasts_to_both(ws_server):
    a, b, _ = await _setup_ready_room(ws_server)
    await a.send("start_match")
    for c in (a, b):
        await c.wait_for("match_started", timeout=3.0)
        await c.wait_for("match_starting", timeout=3.0)
    await a.close()
    await b.close()


async def test_start_match_requires_host(ws_server):
    a, b, _ = await _setup_ready_room(ws_server)

    # Bob is not the host.
    await b.send("start_match")
    err = await b.wait_for("room_error", timeout=2.0)
    assert err["payload"]["error"] == "HOST_REQUIRED"

    await a.close()
    await b.close()


async def test_start_match_requires_all_ready(ws_server):
    a = TestClient(ws_server, "alice")
    b = TestClient(ws_server, "bob")
    await a.connect()
    await b.connect()
    await a.send("set_nickname", {"nickname": "Aaa"})
    await a.wait_for("nickname_set", timeout=3.0)
    await b.send("set_nickname", {"nickname": "Bbb"})
    await b.wait_for("nickname_set", timeout=3.0)
    await a.send("create_room")
    room_id = (await a.wait_for("room_created", timeout=3.0))["payload"]["room_id"]
    await b.send("join_room", {"room_id": room_id})
    await b.wait_for("room_joined", timeout=3.0)
    await a.wait_for("room_state", timeout=3.0)

    await a.send("start_match")
    err = await a.wait_for("room_error", timeout=3.0)
    assert err["payload"]["error"] in ("NOT_ALL_READY", "ROOM_ALREADY_STARTED")

    await a.close()
    await b.close()