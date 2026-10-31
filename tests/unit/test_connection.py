import json

import pytest

from network.connection import Connection
from protocol.messages import ServerMessage, MsgType


class FakeWS:
    def __init__(self):
        self.sent = []
        self.closed = False

    async def send(self, data):
        self.sent.append(data)

    async def close(self):
        self.closed = True


async def test_send_serializes_json():
    ws = FakeWS()
    conn = Connection(ws)
    await conn.send(ServerMessage(type="hello", payload={"x": 1}))
    assert len(ws.sent) == 1
    data = json.loads(ws.sent[0])
    assert data == {"type": "hello", "payload": {"x": 1}}


async def test_send_enum_type_normalized():
    ws = FakeWS()
    conn = Connection(ws)
    await conn.send(ServerMessage(type=MsgType.NICKNAME_SET, payload={"nickname": "A"}))
    data = json.loads(ws.sent[0])
    assert data["type"] == "nickname_set"


async def test_connection_has_unique_id():
    a = Connection(FakeWS())
    b = Connection(FakeWS())
    assert a.id != b.id
    assert len(a.id) == 8


async def test_close():
    ws = FakeWS()
    conn = Connection(ws)
    await conn.close()
    assert ws.closed is True