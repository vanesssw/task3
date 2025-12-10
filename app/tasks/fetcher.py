import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional, Callable

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.news import NewsItem
from app.services.events import broadcast_change

logger = logging.getLogger("hltv_app")

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None


async def fetch_latest_news(limit: int = 5) -> List[dict[str, Any]]:
    if async_playwright is None:
        logger.warning("playwright not installed, using fallback data")
        return [
            {
                "title": "Fallback news (install playwright)",
                "url": "https://www.hltv.org",
                "country": None,
                "published_text": datetime.now(timezone.utc).isoformat(),
                "comments": None,
            }
        ]

    items: List[dict[str, Any]] = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            response = await page.goto("https://www.hltv.org", wait_until="domcontentloaded", timeout=60000)
            status = response.status if response else None
            logger.info("HLTV fetch status=%s url=%s", status, response.url if response else None)
            try:
                await page.wait_for_selector("a.newsline.article", timeout=5000)
            except Exception:
                logger.warning("Selector a.newsline.article not found within timeout")
            anchors = await page.query_selector_all("a.newsline.article")
            logger.info("Found %s anchors", len(anchors))
            for anchor in anchors[:limit]:
                url = await anchor.get_attribute("href") or ""
                title_el = await anchor.query_selector(".newstext")
                title = (await title_el.inner_text()) if title_el else "No title"
                country_el = await anchor.query_selector(".newsflag")
                country = await country_el.get_attribute("title") if country_el else None
                published_el = await anchor.query_selector(".newsrecent")
                published_text = (
                    await published_el.inner_text() if published_el else None
                )
                comments_el = await anchor.query_selector(".newstc div:last-child")
                comments_raw = await comments_el.inner_text() if comments_el else None
                comments: Optional[int] = None
                if comments_raw:
                    digits = "".join(ch for ch in comments_raw if ch.isdigit())
                    comments = int(digits) if digits else None

                items.append(
                    {
                        "title": title.strip(),
                        "url": f"https://www.hltv.org{url}".strip(),
                        "country": country,
                        "published_text": published_text,
                        "comments": comments,
                    }
                )
            await browser.close()
    except Exception as exc:
        logger.warning("Playwright fetch failed: %s", exc)
        return []

    return items


async def sync_news_from_web(session: AsyncSession) -> List[NewsItem]:
    fetched = await fetch_latest_news(limit=10)
    stored: List[NewsItem] = []
    for entry in fetched:
        if not entry.get("url"):
            continue
        stmt = select(NewsItem).where(NewsItem.url == entry["url"])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            await session.execute(
                update(NewsItem)
                .where(NewsItem.id == existing.id)
                .values(
                    title=entry.get("title") or existing.title,
                    country=entry.get("country") or existing.country,
                    published_text=entry.get("published_text") or existing.published_text,
                    comments=entry.get("comments", existing.comments),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            stored.append(existing)
        else:
            item = NewsItem(
                title=entry.get("title") or "Untitled",
                url=entry["url"],
                country=entry.get("country"),
                published_text=entry.get("published_text"),
                comments=entry.get("comments"),
            )
            session.add(item)
            stored.append(item)
    await session.commit()
    return stored


async def run_background_fetch(
    session_factory: async_sessionmaker[AsyncSession], timestamp: datetime
) -> dict[str, Any]:
    async with session_factory() as session:
        stored = await sync_news_from_web(session)
        payload = {
            "timestamp": timestamp.isoformat(),
            "count": len(stored),
        }
        await broadcast_change("task.completed", payload)
        return payload


async def periodic_task(
    stop_event: asyncio.Event, session_factory: async_sessionmaker[AsyncSession], interval: int
) -> None:
    logger.info("Periodic task started, will run every %s seconds", interval)
    while not stop_event.is_set():
        try:
            logger.info("Starting periodic background fetch...")
            await run_background_fetch(session_factory, datetime.now(timezone.utc))
            logger.info("Periodic background fetch completed, waiting %s seconds", interval)
        except Exception as exc:
            logger.warning("Background fetch failed: %s", exc)
        for _ in range(interval):
            if stop_event.is_set():
                break
            await asyncio.sleep(1)

