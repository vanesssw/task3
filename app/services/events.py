from datetime import datetime
from typing import Any

def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    return obj

from app.nats.client import NATS_SUBJECT, nats_client
from app.ws.manager import ws_manager


async def broadcast_change(event: str, payload: dict[str, Any]) -> None:
    safe_payload = _to_jsonable(payload)
    await ws_manager.broadcast({"event": event, "data": safe_payload})
    await nats_client.publish(NATS_SUBJECT, {"event": event, "data": safe_payload})

