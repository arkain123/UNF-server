import asyncio
import argparse
import logging
import ssl

import websockets

from infra.logger import setup_logger
from game.match_handlers import MatchHandlers
from network.session import SessionManager
from network.dispatcher import Dispatcher
from network.websocket_handler import WebSocketHandler
from rooms.room_manager import RoomManager
from rooms.room_handlers import RoomHandlers
import config


def _build_ssl_context(cert: str, key: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    return ctx


async def run(host: str, port: int, *, use_tls: bool = False,
              cert: str | None = None, key: str | None = None):
    log = setup_logger()

    sessions = SessionManager()
    rooms = RoomManager()
    match_handlers = MatchHandlers(sessions, rooms)
    room_handlers = RoomHandlers(sessions, rooms, match_handlers)
    dispatcher = Dispatcher(room_handlers, match_handlers)
    handler = WebSocketHandler(sessions, rooms, dispatcher, match_handlers)

    ssl_ctx = _build_ssl_context(cert, key) if use_tls else None
    scheme = "wss" if use_tls else "ws"
    log.info("server listening on %s://%s:%s%s", scheme, host, port, config.WS_PATH)

    async with websockets.serve(
        handler.handle, host, port,
        ping_interval=config.PING_INTERVAL_SEC,
        ping_timeout=config.PING_TIMEOUT_SEC,
        ssl=ssl_ctx,
    ):
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            log.info("shutdown")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default=config.HOST)
    p.add_argument("--port", type=int, default=config.PORT)
    p.add_argument("--tls", action="store_true", default=config.USE_TLS,
                   help="terminate TLS directly in the server (wss://)")
    p.add_argument("--tls-cert", default=config.TLS_CERT)
    p.add_argument("--tls-key", default=config.TLS_KEY)
    args = p.parse_args()

    try:
        asyncio.run(run(
            args.host,
            args.port,
            use_tls=args.tls,
            cert=args.tls_cert,
            key=args.tls_key,
        ))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()