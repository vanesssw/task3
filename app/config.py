import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./news.db")
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL_SECONDS", "300"))

# Optional URL to external CSS (e.g., Yandex Cloud Storage)
EXTERNAL_CSS_URL = os.getenv("EXTERNAL_CSS_URL", "https://storage.yandexcloud.net/prodproject/news.css")
# Optional URL to external HTML page to redirect /news to (e.g., hosted in object storage)
EXTERNAL_HTML_URL = os.getenv("EXTERNAL_HTML_URL", "https://storage.yandexcloud.net/prodproject/news.html")
