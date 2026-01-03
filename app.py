"""FastAPI application for RSS feed generation with scheduled scraping."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Response

from database import get_recent_articles, init_db
from rss import generate_rss
from scraper import InfoTsinghuaScraper

# Scrape interval in seconds (30 minutes)
SCRAPE_INTERVAL = 30 * 60

# Maximum pages to scrape per run
MAX_PAGES_PER_RUN = 10


scheduler = AsyncIOScheduler()


async def scrape_articles() -> None:
    """Scrape articles and save to database."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting scrape...")

    try:
        with InfoTsinghuaScraper() as scraper:
            # Fetch recent articles
            items = scraper.fetch_items(lmid="all", max_pages=MAX_PAGES_PER_RUN, page_size=30)
            print(f"Fetched {len(items)} items from API")

            new_count = 0
            updated_count = 0

            for item in items:
                article = {
                    "xxid": item["xxid"],
                    "title": item["bt"],
                    "content": "",
                    "department": item.get("dwmc", ""),
                    "category": item.get("lmmc", ""),
                    "publish_time": item["fbsj"],
                    "url": f"{scraper.BASE_URL}{item['url']}",
                }

                # Insert or update article
                is_new = scraper.upsert_article(article)
                if is_new:
                    new_count += 1
                else:
                    updated_count += 1

            print(f"Saved {new_count} new articles, updated {updated_count} existing articles")

    except Exception as e:
        print(f"Error during scrape: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Initialize database
    init_db()
    print("Database initialized")

    # Start scheduler
    scheduler.add_job(
        scrape_articles,
        "interval",
        seconds=SCRAPE_INTERVAL,
        id="scrape_articles",
        replace_existing=True,
    )

    # Run initial scrape
    await scrape_articles()

    scheduler.start()
    print(f"Scheduler started, scraping every {SCRAPE_INTERVAL} seconds")

    yield

    # Shutdown
    scheduler.shutdown()
    print("Scheduler shutdown")


app = FastAPI(
    title="Tsinghua Info RSS",
    description="RSS feed for Tsinghua University Info Portal",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "Tsinghua Info RSS Feed",
        "feed_url": "/rss",
        "docs_url": "/docs",
    }


@app.get("/rss")
async def rss_feed() -> Response:
    """Generate and return RSS feed."""
    rss_xml = generate_rss(limit=500)

    return Response(
        content=rss_xml,
        media_type="application/rss+xml",
        headers={
            "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    articles = get_recent_articles(limit=1)
    return {
        "status": "healthy",
        "total_articles": len(articles),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
