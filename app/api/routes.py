from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.session import get_session, AsyncSessionMaker
from app.schemas.news import NewsCreate, NewsRead, NewsUpdate
from app.services.events import broadcast_change
from app.services.news_service import get_news_or_404
from app.tasks.fetcher import run_background_fetch
from app.models.news import NewsItem
from sqlalchemy import select

router = APIRouter()


@router.get("/items", response_model=List[NewsRead])
async def list_items(
    limit: int = 50, offset: int = 0, session: AsyncSession = Depends(get_session)
) -> List[NewsRead]:
    stmt = select(NewsItem).offset(offset).limit(limit).order_by(NewsItem.id.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/items/{item_id}", response_model=NewsRead)
async def get_item(item_id: int, session: AsyncSession = Depends(get_session)) -> NewsRead:
    item = await get_news_or_404(session, item_id)
    return item


@router.post("/items", response_model=NewsRead, status_code=201)
async def create_item(
    payload: NewsCreate, session: AsyncSession = Depends(get_session)
) -> NewsRead:
    item = NewsItem(**payload.dict())
    session.add(item)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail="Item with this URL already exists")
    await session.refresh(item)
    await broadcast_change("item.created", NewsRead.from_orm(item).dict())
    return item


@router.patch("/items/{item_id}", response_model=NewsRead)
async def update_item(
    item_id: int, payload: NewsUpdate, session: AsyncSession = Depends(get_session)
) -> NewsRead:
    item = await get_news_or_404(session, item_id)
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(item, field, value)
    await session.commit()
    await session.refresh(item)
    await broadcast_change("item.updated", NewsRead.from_orm(item).dict())
    return item


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int, session: AsyncSession = Depends(get_session)) -> None:
    item = await get_news_or_404(session, item_id)
    await session.delete(item)
    await session.commit()
    await broadcast_change("item.deleted", {"id": item_id})


@router.post("/tasks/run")
async def run_task_now() -> dict[str, Any]:
    payload = await run_background_fetch(AsyncSessionMaker, datetime.now(timezone.utc))
    return {"status": "scheduled", **payload}

