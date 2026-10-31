import asyncio
import json

import websockets


def make_msg(type_: str, payload: dict | None = None) -> str:
    return json.dumps({"type": type_, "payload": payload or {}})


class TestClient:
    def __init__(self, url: str, nickname: str = "tester"):
        self.url = url
        self.nickname = nickname
        self.ws = None
        self.inbox: asyncio.Queue[dict] = asyncio.Queue()
        self._reader_task = None

    async def connect(self, set_nickname: bool = True):
        self.ws = await websockets.connect(self.url)
        self._reader_task = asyncio.create_task(self._reader())
        if set_nickname:
            await self.send("set_nickname", {"nickname": self.nickname})
            await self.wait_for("nickname_set")

    async def _reader(self):
        try:
            async for raw in self.ws:
                await self.inbox.put(json.loads(raw))
        except websockets.ConnectionClosed:
            pass

    async def send(self, type_: str, payload: dict | None = None):
        await self.ws.send(make_msg(type_, payload))

    async def wait_for(self, type_: str, timeout: float = 2.0) -> dict:
        async def _loop():
            while True:
                msg = await self.inbox.get()
                if msg["type"] == type_:
                    return msg
        return await asyncio.wait_for(_loop(), timeout=timeout)

    async def no_message(self, timeout: float = 0.3) -> bool:
        try:
            msg = await asyncio.wait_for(self.inbox.get(), timeout=timeout)
            raise AssertionError(f"unexpected message: {msg}")
        except asyncio.TimeoutError:
            return True

    async def close(self):
        if self.ws:
            await self.ws.close()
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass