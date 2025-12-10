import json
import logging
from typing import Any, Callable, Optional

from app.config import NATS_URL

try:
    import nats
    from nats.aio.msg import Msg as NatsMsg
except ImportError:
    nats = None
    NatsMsg = Any

logger = logging.getLogger("hltv_app")

NATS_SUBJECT = "items.updates"


class NatsClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self.nc = None
        self.sub = None

    async def connect(self) -> None:
        if nats is None:
            logger.warning("nats package not installed; NATS disabled")
            return
        try:
            self.nc = await nats.connect(self.url, connect_timeout=2)
            logger.info("Connected to NATS: %s", self.url)
        except Exception as exc:  # pragma: no cover - сетевой код
            logger.warning("NATS connection failed: %s", exc)
            self.nc = None

    async def close(self) -> None:
        if self.nc is not None:
            await self.nc.drain()
            self.nc = None
            logger.info("NATS connection closed")

    async def publish(self, subject: str, payload: dict[str, Any]) -> None:
        if self.nc is None:
            return
        try:
            await self.nc.publish(subject, json.dumps(payload).encode())
        except Exception as exc:
            logger.warning("NATS publish failed: %s", exc)

    async def subscribe(
        self, subject: str, handler: Callable[[NatsMsg], Any]
    ) -> None:
        if self.nc is None:
            return
        try:
            self.sub = await self.nc.subscribe(subject, cb=handler)
            logger.info("Subscribed to NATS subject '%s'", subject)
        except Exception as exc:
            logger.warning("NATS subscribe failed: %s", exc)


nats_client = NatsClient(NATS_URL)

