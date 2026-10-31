import asyncio
import socket

import pytest
import websockets

import config
from network.session import SessionManager
from network.dispatcher import Dispatcher
from network.websocket_handler import WebSocketHandler
from rooms.room_manager import RoomManager
from rooms.room_handlers import RoomHandlers


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
async def ws_server():
    sessions = SessionManager()
    rooms = RoomManager()
    handlers = RoomHandlers(sessions, rooms)
    dispatcher = Dispatcher(handlers)
    handler = WebSocketHandler(sessions, rooms, dispatcher)

    port = _free_port()
    async with websockets.serve(
        handler.handle,
        "127.0.0.1",
        port,
        ping_interval=config.PING_INTERVAL_SEC,
        ping_timeout=config.PING_TIMEOUT_SEC,
    ):
        yield f"ws://127.0.0.1:{port}{config.WS_PATH}"
        await asyncio.sleep(0)