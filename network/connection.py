import json
import logging
import uuid

from protocol.messages import ServerMessage

log = logging.getLogger("unf.server")


class Connection:
    def __init__(self, ws):
        self.id = uuid.uuid4().hex[:8]
        self.ws = ws

    async def send(self, msg: ServerMessage) -> None:
        type_str = msg.type.value if hasattr(msg.type, "value") else msg.type
        log.info("send id=%s type=%s payload=%s",
                 self.id, type_str, msg.payload)
        await self.ws.send(json.dumps({
            "type": type_str,
            "payload": msg.payload,
        }))

    async def close(self) -> None:
        await self.ws.close()