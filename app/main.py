import asyncio
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import FETCH_INTERVAL
from app.db.session import engine, AsyncSessionMaker, init_db
from app.nats.client import NATS_SUBJECT, NatsMsg, nats_client
from app.tasks.fetcher import periodic_task
from app.ws.manager import ws_manager

# Logging: use project-local logs directory by default; override with HLTV_LOG_DIR env var
LOG_DIR = os.getenv("HLTV_LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logger = logging.getLogger("hltv_app")
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,
    encoding="utf-8",
)

formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

app = FastAPI(title="HLTV News Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# Mount local static files for development (serves /static/news.css)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(api_router)


@app.websocket("/ws/items")
async def websocket_items(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


async def nats_message_handler(msg: NatsMsg) -> None:
    try:
        payload = json.loads(msg.data.decode())
    except Exception:
        logger.warning("Received non-JSON NATS message")
        return
    logger.info("NATS message received: %s", payload)

    await ws_manager.broadcast({"event": "nats.forwarded", "data": payload})

    event = payload.get("event")
    data = payload.get("data", {})
    
    if event == "item.created" and isinstance(data, dict) and data.get("url"):
        async with AsyncSessionMaker() as session:
            from app.models.news import NewsItem
            from sqlalchemy import select

            stmt = select(NewsItem).where(NewsItem.url == data.get("url"))
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing and data.get("url"):
                item = NewsItem(
                    title=data.get("title", "Untitled"),
                    url=data.get("url"),
                    country=data.get("country"),
                    published_text=data.get("published_text"),
                    comments=data.get("comments"),
                )
                session.add(item)
                await session.commit()
                logger.info("Created news item from NATS: %s", data.get("url"))
    
    elif event == "item.updated" and isinstance(data, dict) and "id" in data:
        async with AsyncSessionMaker() as session:
            from app.models.news import NewsItem
            from sqlalchemy import select, update
            
            stmt = select(NewsItem).where(NewsItem.id == data.get("id"))
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                await session.execute(
                    update(NewsItem)
                    .where(NewsItem.id == data.get("id"))
                    .values(
                        title=data.get("title", existing.title),
                        country=data.get("country", existing.country),
                        published_text=data.get("published_text", existing.published_text),
                        comments=data.get("comments", existing.comments),
                    )
                )
                await session.commit()
                logger.info("Updated news item from NATS: id=%s", data.get("id"))
    
    elif event == "item.deleted" and isinstance(data, dict) and "id" in data:
        async with AsyncSessionMaker() as session:
            from app.models.news import NewsItem
            from sqlalchemy import select
            
            stmt = select(NewsItem).where(NewsItem.id == data.get("id"))
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                await session.delete(existing)
                await session.commit()
                logger.info("Deleted news item from NATS: id=%s", data.get("id"))


stop_event = asyncio.Event()
background_task: Optional[asyncio.Task] = None



@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
    await nats_client.connect()
    await nats_client.subscribe(NATS_SUBJECT, nats_message_handler)

    global background_task, stop_event
    stop_event = asyncio.Event()
    background_task = asyncio.create_task(
        periodic_task(stop_event, AsyncSessionMaker, FETCH_INTERVAL)
    )
    logger.info("Background fetcher started every %s seconds", FETCH_INTERVAL)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    stop_event.set()
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
    await nats_client.close()
    await engine.dispose()
    logger.info("Application shutdown complete")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
