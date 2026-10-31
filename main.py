import asyncio
import argparse
import logging

import websockets

from infra.logger import setup_logger
from network.session import SessionManager
from network.dispatcher import Dispatcher
from network.websocket_handler import WebSocketHandler
from rooms.room_manager import RoomManager
from rooms.room_handlers import RoomHandlers
import config


async def run(host: str, port: int):
    log = setup_logger()

    sessions = SessionManager()
    rooms = RoomManager()
    room_handlers = RoomHandlers(sessions, rooms)
    dispatcher = Dispatcher(room_handlers)
    handler = WebSocketHandler(sessions, rooms, dispatcher)

    log.info("server listening on %s:%s", host, port)
    async with websockets.serve(handler.handle, host, port):
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            log.info("shutdown")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default=config.HOST)
    p.add_argument("--port", type=int, default=config.PORT)
    args = p.parse_args()

    try:
        asyncio.run(run(args.host, args.port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()