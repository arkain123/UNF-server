from .ws_client import TestClient


async def test_connect_and_disconnect(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    await a.close()


async def test_no_message_before_action(ws_server):
    a = TestClient(ws_server, "alice")
    await a.connect()
    assert await a.no_message(timeout=0.3) is True
    await a.close()