import pytest

from network.session import SessionManager


class FakeConn:
    def __init__(self):
        self.id = "c1"
        self.sent = []
        self.closed = False

    async def send(self, msg):
        self.sent.append(msg)

    async def close(self):
        self.closed = True


def test_create_session():
    mgr = SessionManager()
    conn = FakeConn()
    s = mgr.create(conn)
    assert s.id == "c1"
    assert s.connection is conn
    assert s.authenticated is False
    assert s.nickname is None
    assert s.room_id is None


def test_authenticate():
    mgr = SessionManager()
    s = mgr.create(FakeConn())
    mgr.authenticate(s, "player-1")
    assert s.authenticated is True
    assert s.player_id == "player-1"
    assert mgr.get_by_player("player-1") is s


def test_get_by_player_unknown():
    mgr = SessionManager()
    assert mgr.get_by_player("ghost") is None


def test_bind_and_unbind_room():
    mgr = SessionManager()
    s = mgr.create(FakeConn())
    mgr.authenticate(s, "p1")
    mgr.bind_room(s, "ROOM1")
    assert s.room_id == "ROOM1"
    mgr.unbind_room(s)
    assert s.room_id is None


def test_destroy():
    mgr = SessionManager()
    s = mgr.create(FakeConn())
    mgr.authenticate(s, "p1")
    mgr.destroy(s)
    assert mgr.get_by_player("p1") is None
    assert s.id not in mgr.by_session