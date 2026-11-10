import asyncio

import pytest

import config
from tests.integration.ws_client import TestClient


async def _start_match(ws_server):
    a = TestClient(ws_server, "alice")
    b = TestClient(ws_server, "bob")
    await a.connect()
    await b.connect()
    await a.send("set_nickname", {"nickname": "Alice"})
    await a.wait_for("nickname_set")
    await b.send("set_nickname", {"nickname": "Bob"})
    await b.wait_for("nickname_set")
    await a.send("create_room")
    created = await a.wait_for("room_created")
    room_id = created["payload"]["room_id"]
    await b.send("join_room", {"room_id": room_id})
    await b.wait_for("room_joined")
    state = await a.wait_for("room_state")
    pid_by_nick = {
        p["display_name"]: p["player_id"]
        for p in state["payload"]["room"]["players"]
    }
    await a.send("set_ready", {"ready": True})
    await b.send("set_ready", {"ready": True})
    await a.wait_for("room_state", timeout=2.0)
    await a.send("start_match")
    await a.wait_for("match_started", timeout=3.0)
    await b.wait_for("match_started", timeout=3.0)
    return a, b, pid_by_nick


async def test_bubbles_spawn_after_match_start(ws_server, monkeypatch):
    monkeypatch.setattr(config, "BUBBLE_SPAWN_INTERVAL_SEC", 0.05)
    monkeypatch.setattr(config, "BUBBLE_REACTION_TIME_MIN_SEC", 0.0)
    a, b, pids = await _start_match(ws_server)
    msg = await a.wait_for("bubble_spawn", timeout=3.0)
    assert msg["payload"]["spawn_index"] == 1
    assert len(msg["payload"]["bubbles"]) == config.BUBBLES_PER_SPAWN
    for bb in msg["payload"]["bubbles"]:
        assert "bubble_id" in bb
        assert "spawned_at_server_ms" in bb
    await a.close()
    await b.close()


async def test_first_click_awards_coins(ws_server, monkeypatch):
    monkeypatch.setattr(config, "BUBBLE_SPAWN_INTERVAL_SEC", 0.05)
    monkeypatch.setattr(config, "BUBBLE_REACTION_TIME_MIN_SEC", 0.0)

    a, b, pids = await _start_match(ws_server)
    alice_id = pids["Alice"]
    spawn = await a.wait_for("bubble_spawn", timeout=3.0)
    bid = spawn["payload"]["bubbles"][0]["bubble_id"]

    await a.send("bubble_click", {"bubble_id": bid, "client_ts": 0})

    for c in (a, b):
        res = await c.wait_for("bubble_result", timeout=2.0)
        assert res["payload"]["bubble_id"] == bid
        assert res["payload"]["winner_player_id"] == alice_id
        assert res["payload"]["coins_awarded"] == config.BUBBLE_REWARD_COINS

    upd = await a.wait_for("coin_update", timeout=2.0)
    assert upd["payload"]["player_id"] == alice_id 
    assert upd["payload"]["delta"] == config.BUBBLE_REWARD_COINS
    await a.close()
    await b.close()


async def test_second_click_rejected_too_late(ws_server, monkeypatch):
    monkeypatch.setattr(config, "BUBBLE_SPAWN_INTERVAL_SEC", 0.05)
    monkeypatch.setattr(config, "BUBBLE_REACTION_TIME_MIN_SEC", 0.0)

    a, b, pids = await _start_match(ws_server)
    spawn = await a.wait_for("bubble_spawn", timeout=3.0)
    bid = spawn["payload"]["bubbles"][0]["bubble_id"]

    await a.send("bubble_click", {"bubble_id": bid})
    await a.wait_for("bubble_result", timeout=2.0)

    await b.send("bubble_click", {"bubble_id": bid})
    err = await b.wait_for("bubble_error", timeout=2.0)
    assert err["payload"]["error"] == "TOO_LATE"
    await a.close()
    await b.close()


async def test_unknown_bubble_click(ws_server, monkeypatch):
    monkeypatch.setattr(config, "BUBBLE_REACTION_TIME_MIN_SEC", 0.0)
    a, b, pids = await _start_match(ws_server)
    await a.send("bubble_click", {"bubble_id": "deadbeef"})
    err = await a.wait_for("bubble_error", timeout=2.0)
    assert err["payload"]["error"] == "UNKNOWN"
    await a.close()
    await b.close()


async def test_click_before_match_rejected(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    await a.send("set_nickname", {"nickname": "Alice"})
    await a.wait_for("nickname_set")
    await a.send("create_room")
    await a.wait_for("room_created")

    await a.send("bubble_click", {"bubble_id": "x"})
    err = await a.wait_for("card_error", timeout=2.0)
    assert err["payload"]["error"] == "NOT_IN_MATCH"
    await a.close()


async def test_race_two_players_click_same_bubble(ws_server, monkeypatch):
    monkeypatch.setattr(config, "BUBBLE_SPAWN_INTERVAL_SEC", 0.05)
    monkeypatch.setattr(config, "BUBBLE_REACTION_TIME_MIN_SEC", 0.0)

    a, b, pids = await _start_match(ws_server)
    spawn = await a.wait_for("bubble_spawn", timeout=3.0)
    bid = spawn["payload"]["bubbles"][0]["bubble_id"]

    await asyncio.gather(
        a.send("bubble_click", {"bubble_id": bid}),
        b.send("bubble_click", {"bubble_id": bid}),
    )

    res_a = await a.wait_for("bubble_result", timeout=2.0)
    res_b = await b.wait_for("bubble_result", timeout=2.0)
    assert res_a["payload"]["bubble_id"] == bid
    assert res_b["payload"]["bubble_id"] == bid
    assert (res_a["payload"]["winner_player_id"]
            == res_b["payload"]["winner_player_id"])
    assert res_a["payload"]["winner_player_id"] in (pids["Alice"], pids["Bob"])

    alice_id = pids["Alice"]
    bob_id = pids["Bob"]
    loser = b if res_a["payload"]["winner_player_id"] == alice_id else a
    err = await loser.wait_for("bubble_error", timeout=2.0)
    assert err["payload"]["error"] == "TOO_LATE"

    await a.close()
    await b.close()


async def test_match_ended_on_timeout(ws_server, monkeypatch):
    monkeypatch.setattr(config, "BUBBLE_ROUND_DURATION_SEC", 0.1)
    monkeypatch.setattr(config, "BUBBLE_SPAWN_INTERVAL_SEC", 0.05)

    a, b, pids = await _start_match(ws_server)
    for c in (a, b):
        end = await c.wait_for("match_ended", timeout=3.0)
        assert end["payload"]["room_id"]
        assert "coins" in end["payload"]
    await a.close()
    await b.close()