from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.session import get_session, AsyncSessionMaker
from app.schemas.news import NewsCreate, NewsRead, NewsUpdate
from app.services.events import broadcast_change
from app.services.news_service import get_news_or_404
from app.tasks.fetcher import run_background_fetch
from app.models.news import NewsItem
from sqlalchemy import select
from app.config import EXTERNAL_CSS_URL, EXTERNAL_HTML_URL

router = APIRouter()

templates = Jinja2Templates(directory="templates")


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


@router.get("/news", response_class=HTMLResponse)
async def news_page(request: Request, css_url: str | None = None, html_url: str | None = None):
    """Render HTML page with latest news or redirect to external HTML.

    Priority for HTML:
      1. Query param `html_url`
      2. `EXTERNAL_HTML_URL` from config
      3. Render local template

    Priority for CSS:
      1. Query param `css_url`
      2. `EXTERNAL_CSS_URL` from config
      3. None (template fallback)
    """
    # If query param provided, prefer that. Otherwise fallback to config.
    chosen_html = html_url or EXTERNAL_HTML_URL
    if chosen_html:
        # Redirect to external HTML page (preserve method via 307 temporary redirect)
        return RedirectResponse(url=chosen_html, status_code=307)

    chosen_css = css_url or EXTERNAL_CSS_URL

    async with AsyncSessionMaker() as session:
        stmt = select(NewsItem).order_by(NewsItem.id.desc()).limit(50)
        result = await session.execute(stmt)
        items = result.scalars().all()

    return templates.TemplateResponse("news.html", {"request": request, "news_list": items, "css_url": chosen_css})
