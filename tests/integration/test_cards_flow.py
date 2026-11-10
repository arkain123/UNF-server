import pytest
import asyncio

import config
from tests.integration.ws_client import TestClient


async def _start_match(ws_server):
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
    state = await a.wait_for("room_state")
    pid_by_nick = {
        p["display_name"]: p["player_id"]
        for p in state["payload"]["room"]["players"]
    }
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
    await a.send("start_match")
    await a.wait_for("match_started", timeout=3.0)
    await b.wait_for("match_started", timeout=3.0)
    return a, b, pid_by_nick


async def test_train_new_card(ws_server):
    a, b, pids = await _start_match(ws_server)
    await a.send("train_card", {"card_id": "fireball", "card_level": 1})
    msg = await a.wait_for("card_trained", timeout=2.0)
    assert msg["payload"]["card_id"] == "fireball"
    assert msg["payload"]["level"] == 1
    await a.close()
    await b.close()


async def test_train_rejects_invalid_level(ws_server):
    a, b, pids = await _start_match(ws_server)
    await a.send("train_card", {
        "card_id": "fireball",
        "card_level": config.TRAINING_MAX_CARD_LEVEL + 1,
    })
    err = await a.wait_for("card_error", timeout=2.0)
    assert err["payload"]["error"] == "CARD_LEVEL_INVALID"
    await a.close()
    await b.close()


async def test_card_level_up_broadcasts(ws_server):
    a, b, pids = await _start_match(ws_server)
    await a.send("train_card", {"card_id": "fireball", "card_level": 1})
    await a.wait_for("card_trained")

    await a.send("card_level_up", {"card_id": "fireball", "new_level": 2})
    upd = await a.wait_for("card_level_updated", timeout=2.0)
    assert upd["payload"]["card_id"] == "fireball"
    assert upd["payload"]["level"] == 2
    await a.close()
    await b.close()


async def test_card_level_up_rejects_jump(ws_server):
    a, b, pids = await _start_match(ws_server)
    await a.send("train_card", {"card_id": "fireball", "card_level": 1})
    await a.wait_for("card_trained")

    await a.send("card_level_up", {"card_id": "fireball", "new_level": 5})
    upd = await a.wait_for("card_level_updated", timeout=2.0)
    assert upd["payload"]["level"] == 1  # unchanged
    await a.close()
    await b.close()


async def test_card_level_up_unknown_card(ws_server):
    a, b, pids = await _start_match(ws_server)
    await a.send("card_level_up", {"card_id": "ghost", "new_level": 2})
    err = await a.wait_for("card_error", timeout=2.0)
    assert err["payload"]["error"] == "CARD_NOT_FOUND"
    await a.close()
    await b.close()


async def test_use_card_broadcasts_to_both(ws_server):
    a, b, pids = await _start_match(ws_server)
    alice_id, bob_id = pids["Alice"], pids["Bob"]
    await a.send("train_card", {"card_id": "fireball", "card_level": 1})
    await a.wait_for("card_trained")

    await a.send("use_card", {
        "card_id": "fireball",
        "card_level": 1,
        "target_player_id": bob_id,
    })
    for c in (a, b):
        msg = await c.wait_for("card_used", timeout=2.0)
        assert msg["payload"]["card_id"] == "fireball"
        assert msg["payload"]["level"] == 1
        assert msg["payload"]["by_player_id"] == alice_id
        assert msg["payload"]["target_player_id"] == bob_id
    await a.close()
    await b.close()


async def test_use_card_not_owned(ws_server):
    a, b, pids = await _start_match(ws_server)
    await a.send("use_card", {
        "card_id": "ghost",
        "card_level": 1,
        "target_player_id": "bob",
    })
    err = await a.wait_for("card_error", timeout=2.0)
    assert err["payload"]["error"] == "CARD_NOT_OWNED"
    await a.close()
    await b.close()


async def test_use_card_level_mismatch(ws_server):
    a, b, pids = await _start_match(ws_server)
    await a.send("train_card", {"card_id": "fireball", "card_level": 1})
    await a.wait_for("card_trained")

    await a.send("use_card", {
        "card_id": "fireball",
        "card_level": 2,
        "target_player_id": "bob",
    })
    err = await a.wait_for("card_error", timeout=2.0)
    assert err["payload"]["error"] == "CARD_LEVEL_MISMATCH"
    await a.close()
    await b.close()