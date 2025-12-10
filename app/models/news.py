from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.db.session import Base


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(500), unique=True, nullable=False)
    country = Column(String(120), nullable=True)
    published_text = Column(String(120), nullable=True)
    comments = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

