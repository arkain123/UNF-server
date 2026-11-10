import asyncio

import pytest

import config
from game.bubble import ClickOutcomeKind
from game.bubble_manager import BubbleManager
from protocol.messages import ServerMessage


class Recorder:

    def __init__(self):
        self.messages: list[ServerMessage] = []
        self.coin_awards: list[tuple[str, int]] = []
        self.balances: dict[str, int] = {}

    async def broadcast(self, msg: ServerMessage):
        self.messages.append(msg)

    async def coin_award(self, player_id: str, coins: int) -> int:
        self.coin_awards.append((player_id, coins))
        self.balances[player_id] = self.balances.get(player_id, 0) + coins
        return self.balances[player_id]

    def types(self) -> list[str]:
        return [m.type for m in self.messages]


@pytest.fixture
def rec():
    return Recorder()


@pytest.fixture
def bm(rec, monkeypatch):
    monkeypatch.setattr(config, "BUBBLE_REACTION_TIME_MIN_SEC", 0.0)
    return BubbleManager(
        room_id="ROOM01",
        broadcast=rec.broadcast,
        coin_award=rec.coin_award,
    )


async def _spawn_one(bm: BubbleManager) -> str:
    await bm._tick()
    spawn_msgs = [b for b in bm._bubbles.values()]
    assert spawn_msgs, "expected at least one bubble"
    return spawn_msgs[-1].bubble_id


class TestSpawn:
    async def test_tick_spawns_bubbles(self, bm, rec):
        await bm._tick()
        assert len(bm._bubbles) == config.BUBBLES_PER_SPAWN
        assert "bubble_spawn" in rec.types()

    async def test_spawn_payload_shape(self, bm, rec):
        await bm._tick()
        spawn = next(m for m in rec.messages if m.type == "bubble_spawn")
        assert spawn.payload["spawn_index"] == 1
        assert len(spawn.payload["bubbles"]) == config.BUBBLES_PER_SPAWN
        for b in spawn.payload["bubbles"]:
            assert "bubble_id" in b
            assert "spawned_at_server_ms" in b

    async def test_spawn_index_increments(self, bm, rec):
        await bm._tick()
        await bm._tick()
        spawns = [m for m in rec.messages if m.type == "bubble_spawn"]
        assert [s.payload["spawn_index"] for s in spawns] == [1, 2]

    async def test_respects_max_active(self, bm, rec, monkeypatch):
        monkeypatch.setattr(config, "BUBBLE_MAX_ACTIVE", 2)
        monkeypatch.setattr(config, "BUBBLES_PER_SPAWN", 2)
        await bm._tick()
        assert len(bm._bubbles) == 2
        await bm._tick()
        assert len(bm._bubbles) == 2

    async def test_expired_bubbles_despawned(self, bm, rec, monkeypatch):
        monkeypatch.setattr(config, "BUBBLE_LIFETIME_SEC", 0.01)
        await bm._tick()
        await asyncio.sleep(0.02)
        await bm._tick()
        assert "bubble_despawn" in rec.types()


class TestResolveClick:
    async def test_first_click_wins(self, bm, rec):
        await bm._tick()
        bid = next(iter(bm._bubbles))
        out = await bm.resolve_click("p1", bid)
        assert out.kind is ClickOutcomeKind.WON
        assert out.coins == config.BUBBLE_REWARD_COINS

    async def test_second_click_too_late(self, bm, rec):
        await bm._tick()
        bid = next(iter(bm._bubbles))
        await bm.resolve_click("p1", bid)
        out = await bm.resolve_click("p2", bid)
        assert out.kind is ClickOutcomeKind.TOO_LATE

    async def test_unknown_bubble(self, bm, rec):
        out = await bm.resolve_click("p1", "deadbeef")
        assert out.kind is ClickOutcomeKind.UNKNOWN

    async def test_anti_bot_rejects_too_fast(self, bm, rec, monkeypatch):
        monkeypatch.setattr(config, "BUBBLE_REACTION_TIME_MIN_SEC", 0.5)
        await bm._tick()
        bid = next(iter(bm._bubbles))
        out = await bm.resolve_click("p1", bid)
        assert out.kind is ClickOutcomeKind.TOO_FAST
        assert bm._bubbles[bid].resolved is False

    async def test_expired_bubble_rejected(self, bm, rec, monkeypatch):
        monkeypatch.setattr(config, "BUBBLE_LIFETIME_SEC", 0.01)
        await bm._tick()
        bid = next(iter(bm._bubbles))
        await asyncio.sleep(0.02)
        out = await bm.resolve_click("p1", bid)
        assert out.kind is ClickOutcomeKind.EXPIRED

    async def test_concurrent_clicks_exactly_one_winner(self, bm, rec):
        await bm._tick()
        bid = next(iter(bm._bubbles))

        async def click(pid):
            return await bm.resolve_click(pid, bid)

        outs = await asyncio.gather(
            click("p1"), click("p2"), click("p3"),
        )
        wins = [o for o in outs if o.kind is ClickOutcomeKind.WON]
        assert len(wins) == 1
        # Exactly one coin award.
        assert len(rec.coin_awards) == 1


class TestCoinAward:
    async def test_winner_gets_reward(self, bm, rec):
        await bm._tick()
        bid = next(iter(bm._bubbles))
        await bm.resolve_click("p1", bid)
        assert rec.balances["p1"] == config.BUBBLE_REWARD_COINS

    async def test_bubble_result_broadcast(self, bm, rec):
        await bm._tick()
        bid = next(iter(bm._bubbles))
        await bm.resolve_click("p1", bid)
        results = [m for m in rec.messages if m.type == "bubble_result"]
        assert len(results) == 1
        p = results[0].payload
        assert p["bubble_id"] == bid
        assert p["winner_player_id"] == "p1"
        assert p["coins_awarded"] == config.BUBBLE_REWARD_COINS

    async def test_coin_update_broadcast(self, bm, rec):
        await bm._tick()
        bid = next(iter(bm._bubbles))
        await bm.resolve_click("p1", bid)
        updates = [m for m in rec.messages if m.type == "coin_update"]
        assert len(updates) == 1
        p = updates[0].payload
        assert p["player_id"] == "p1"
        assert p["delta"] == config.BUBBLE_REWARD_COINS
        assert p["balance"] == config.BUBBLE_REWARD_COINS

    async def test_multiple_wins_accumulate(self, bm, rec):
        await bm._tick()
        b1 = next(iter(bm._bubbles))
        await bm.resolve_click("p1", b1)
        await bm._tick()
        # Remaining unresolved bubble after first was resolved.
        remaining = [k for k, v in bm._bubbles.items() if not v.resolved]
        if not remaining:
            await bm._tick()
            remaining = [k for k, v in bm._bubbles.items() if not v.resolved]
        await bm.resolve_click("p1", remaining[0])
        assert rec.balances["p1"] == config.BUBBLE_REWARD_COINS * 2


class TestLifecycle:
    async def test_start_and_stop(self, bm):
        await bm.start()
        assert bm._running is True
        assert bm._spawn_task is not None
        await bm.stop()
        assert bm._running is False
        assert bm._spawn_task is None
        assert bm._bubbles == {}

    async def test_stop_is_idempotent(self, bm):
        await bm.start()
        await bm.stop()
        await bm.stop()  # should not raise

    async def test_start_is_idempotent(self, bm):
        await bm.start()
        task1 = bm._spawn_task
        await bm.start()
        assert bm._spawn_task is task1
        await bm.stop()

    async def test_spawn_loop_runs(self, bm, rec, monkeypatch):
        monkeypatch.setattr(config, "BUBBLE_SPAWN_INTERVAL_SEC", 0.01)
        await bm.start()
        await asyncio.sleep(0.05)
        await bm.stop()
        assert any(m.type == "bubble_spawn" for m in rec.messages)