import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./news.db")
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL_SECONDS", "300"))

