import json
import logging
from typing import Any, List, Set

from fastapi import WebSocket

logger = logging.getLogger("hltv_app")


class WebSocketManager:
    def __init__(self) -> None:
        self.active: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.add(websocket)
        logger.info("WebSocket connected (%s active)", len(self.active))

    def disconnect(self, websocket: WebSocket) -> None:
        self.active.discard(websocket)
        logger.info("WebSocket disconnected (%s active)", len(self.active))

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self.active:
            return
        data = json.dumps(message)
        stale: List[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)


ws_manager = WebSocketManager()

