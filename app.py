"""FastAPI application for RSS feed generation with scheduled scraping."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Response

from database import get_last_scrape_time, get_recent_articles, init_db, set_last_scrape_time
from rss import generate_rss
from scraper import ArticleStateEnum, InfoTsinghuaScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Scrape interval in seconds (30 minutes)
# SCRAPE_INTERVAL = 30 * 60
SCRAPE_INTERVAL = 60 # Test: 1 minute

# Maximum pages to scrape per run
# MAX_PAGES_PER_RUN = 10
MAX_PAGES_PER_RUN = 30 # Test: 1 page

# Minimum time between scrapes in seconds (10 minutes)
# MIN_SCRAPE_INTERVAL = 10 * 60
MIN_SCRAPE_INTERVAL = 90 # Test: 1.5 minutes

# Maximum articles to return in RSS feed
MAX_RSS_ITEMS = 500


scheduler = AsyncIOScheduler()


async def scrape_articles() -> None:
    """Scrape articles and save to database."""
    # Check if we scraped recently
    last_scrape = get_last_scrape_time()
    now = int(datetime.now(timezone.utc).timestamp() * 1000)

    if last_scrape:
        time_since_last_scrape = (now - last_scrape) / 1000  # Convert to seconds
        if time_since_last_scrape < MIN_SCRAPE_INTERVAL:
            logger.info(f"Skipping scrape: last scrape was {time_since_last_scrape:.1f} seconds ago (minimum: {MIN_SCRAPE_INTERVAL}s)")
            return

    logger.info("Starting scrape...")

    try:
        with InfoTsinghuaScraper() as scraper:
            # Calculate cutoff time: last_scrape - scrape_interval
            # We stop processing when we reach articles older than this
            cutoff_time_ms = last_scrape - (SCRAPE_INTERVAL * 1000) if last_scrape else 0

            new_count = 0
            updated_count = 0
            skipped_count = 0
            error_count = 0
            total_items = 0

            # Fetch and process pages one at a time
            for page in range(1, MAX_PAGES_PER_RUN + 1):
                items = scraper.fetch_list(lmid="all", page=page, page_size=30)
                if not items:
                    logger.info(f"No more items on page {page}, stopping")
                    break

                total_items += len(items)
                logger.info(f"Fetched page {page}: {len(items)} items")

                for item in items:
                    # Check if article publish time is before cutoff
                    publish_time = item.get("fbsj", 0)
                    if publish_time < cutoff_time_ms:
                        logger.info(f"Reached article {item.get('xxid')} with publish_time {publish_time} < cutoff {cutoff_time_ms}, stopping")
                        break

                    try:
                        # Insert or update article using scraper method
                        state = scraper.upsert_article(item)
                        if state == ArticleStateEnum.NEW:
                            new_count += 1
                        elif state == ArticleStateEnum.UPDATED:
                            updated_count += 1
                        else:
                            skipped_count += 1
                    except (ValueError, KeyError) as e:
                        # Skip items with missing required fields
                        error_count += 1
                        logger.warning(f"Skipping item due to error: {e}")
                        logger.debug(f"Problematic item: {item}")
                        continue
                else:
                    # Continue to next page if inner loop didn't break
                    continue

                # Break outer loop if inner loop broke (reached cutoff)
                break

            logger.info(f"Fetched {total_items} items total. Saved {new_count} new articles, updated {updated_count} existing articles, skipped {skipped_count} existing, {error_count} errors")

            # Update last scrape time
            scrape_end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
            set_last_scrape_time(scrape_end_time)
            logger.info("Updated last scrape timestamp")

    except Exception as e:
        logger.error(f"Error during scrape: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Initialize database
    init_db()
    logger.info("Database initialized")

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
    logger.info(f"Scheduler started, scraping every {SCRAPE_INTERVAL} seconds")

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Scheduler shutdown")


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
    rss_xml = generate_rss(limit=MAX_RSS_ITEMS)

    return Response(
        content=rss_xml,
        media_type="application/rss+xml; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    _ = get_recent_articles(limit=1)
    return {
        "status": "healthy"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
