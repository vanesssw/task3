from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import NewsItem


async def get_news_or_404(session: AsyncSession, item_id: int) -> NewsItem:
    result = await session.execute(select(NewsItem).where(NewsItem.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

