"""FastAPI application for RSS feed generation with scheduled scraping."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from auth import (
    get_current_user,
    get_current_user_from_path,
    get_current_user_optional,
    get_gitlab_authorization_url,
    handle_gitlab_callback,
)
from auth_db import (
    init_auth_db,
)
from config import (
    API_DESCRIPTION,
    API_TITLE,
    API_VERSION,
    MAX_PAGES_PER_RUN,
    MAX_RSS_ITEMS,
    MIN_SCRAPE_INTERVAL,
    OAUTH_ENABLED,
    RATE_LIMIT_WINDOW_HOUR,
    RATE_LIMIT_WINDOW_SECOND,
    RSS_CACHE_MAX_AGE,
    SCRAPE_INTERVAL,
    SERVER_HOST,
    SERVER_PORT,
    USER_RATE_LIMIT_PER_HOUR,
    USER_RATE_LIMIT_PER_SECOND,
)
from database import (
    current_timestamp_ms,
    get_last_scrape_time,
    get_recent_articles,
    init_db,
    set_last_scrape_time,
)
from rate_limit import check_rate_limit
from rss import generate_rss, validate_category_input
from scraper import ArticleStateEnum, InfoTsinghuaScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = AsyncIOScheduler()


async def scrape_articles() -> None:
    """Scrape articles and save to database."""
    # Check if we scraped recently
    last_scrape = get_last_scrape_time()
    now = current_timestamp_ms()

    if last_scrape:
        time_since_last_scrape = (now - last_scrape) / 1000  # Convert to seconds
        if time_since_last_scrape < MIN_SCRAPE_INTERVAL:
            logger.info(
                f"Skipping scrape: last scrape was {time_since_last_scrape:.1f} seconds ago (minimum: {MIN_SCRAPE_INTERVAL}s)"
            )
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
                        logger.info(
                            f"Reached article {item.get('xxid')} with publish_time {publish_time} < cutoff {cutoff_time_ms}, stopping"
                        )
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
                        logger.warning(
                            f"Skipping item {item.get('xxid', 'UNKNOWN')} due to error: {e}"
                        )
                        continue
                else:
                    # Continue to next page if inner loop didn't break
                    continue

                # Break outer loop if inner loop broke (reached cutoff)
                break

            logger.info(
                f"Fetched {total_items} items total. Saved {new_count} new articles, updated {updated_count} existing articles, skipped {skipped_count} existing, {error_count} errors"
            )

            # Update last scrape time
            scrape_end_time = current_timestamp_ms()
            set_last_scrape_time(scrape_end_time)
            logger.info("Updated last scrape timestamp")

    except Exception as e:
        logger.error(f"Error during scrape: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Initialize database
    init_db()
    init_auth_db()
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
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
async def root(
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> Response:
    """Root endpoint serving token management HTML."""
    html_path = Path(__file__).parent / "templates" / "tokens.html"

    if not html_path.exists():
        return Response(
            content="<h1>Info Tsinghua RSS Feed</h1><p>Templates not found</p>",
            media_type="text/html",
        )

    html_content = html_path.read_text(encoding="utf-8")
    return Response(content=html_content, media_type="text/html")


@app.get("/api/status")
async def api_status(
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """API status endpoint for frontend authentication check."""
    response = {
        "auth_enabled": OAUTH_ENABLED,
        "authenticated": current_user is not None,
    }

    if current_user:
        response["user"] = {
            "username": current_user["username"],
            "email": current_user["email"],
        }

    return response


# =============================================================================
# OAuth Endpoints
# =============================================================================


@app.get("/auth/login")
async def login():
    """Redirect to GitLab OAuth login."""
    if not OAUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth authentication is not enabled",
        )

    auth_url = get_gitlab_authorization_url(redirect_path="/")
    return RedirectResponse(auth_url)


@app.get("/auth/callback")
async def callback(code: str, state: str):
    """Handle GitLab OAuth callback and redirect to GUI."""
    if not OAUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth authentication is not enabled",
        )

    result = await handle_gitlab_callback(code, state)

    # Get existing token for user
    from auth_db import create_or_reset_user_token, get_user_token

    token = get_user_token(result["user_id"])

    if not token:
        # Create a new token
        token = create_or_reset_user_token(result["user_id"])

    # Redirect to frontend with token as query parameter
    return RedirectResponse(url=f"/?token={token}&new=true")


# =============================================================================
# Token Management Endpoints
# =============================================================================


@app.get("/auth/tokens")
async def list_tokens(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all tokens for the current user."""
    from auth_db import list_user_tokens

    tokens = list_user_tokens(current_user["user_id"])

    return tokens


@app.post("/auth/tokens/{token}/rotate")
async def rotate_token(
    current_user: dict[str, Any] = Depends(get_current_user_from_path),
) -> dict[str, str]:
    """Rotate an auth token (create new, delete old)."""
    from auth_db import rotate_user_token

    new_token = rotate_user_token(current_user["user_id"])

    if not new_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "token": new_token,
        "message": "Token rotated successfully",
        "instructions": "Use the new token with ?token= query parameter to access /rss",
    }


@app.delete("/auth/user")
async def delete_user(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Delete the current user and all associated data."""
    from auth_db import delete_user

    deleted = delete_user(current_user["user_id"])

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {"message": "User deleted successfully"}


# =============================================================================
# RSS Feed Endpoint (Protected)
# =============================================================================


@app.get("/rss")
async def rss_feed(
    category_in: list[str] | None = Query(
        None, description="Categories to filter in (only these categories)"
    ),
    category_not_in: list[str] | None = Query(
        None, alias="not_in", description="Categories to filter out (exclude these categories)"
    ),
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> Response:
    """Generate and return RSS feed (requires authentication).

    Query Parameters:
    - category_in: Filter to only include articles with these categories (e.g., ?category_in=通知&category_in=公告)
    - not_in: Exclude articles with these categories (e.g., ?not_in=招聘&not_in=讲座)
    - token: Authentication token (required if OAuth enabled)

    Authentication:
    - Use ?token= query parameter
    - Get a token by visiting /auth/login (GitLab OAuth)

    Rate Limiting:
    - Authenticated users: 1 request/second, 10 requests/hour
    """
    if OAUTH_ENABLED and not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Visit /auth/login to authenticate",
        )

    # Apply per-user rate limiting for authenticated users
    remaining_second = USER_RATE_LIMIT_PER_SECOND
    remaining_hour = USER_RATE_LIMIT_PER_HOUR

    if current_user:
        user_id = current_user["user_id"]

        # Check per-second rate limit
        allowed_second, remaining_second = check_rate_limit(
            user_id=user_id,
            window_seconds=RATE_LIMIT_WINDOW_SECOND,
            max_requests=USER_RATE_LIMIT_PER_SECOND,
        )

        if not allowed_second:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: maximum 1 request per second",
                headers={
                    "X-RateLimit-Limit-Second": str(USER_RATE_LIMIT_PER_SECOND),
                    "X-RateLimit-Remaining-Second": "0",
                    "X-RateLimit-Limit-Hour": str(USER_RATE_LIMIT_PER_HOUR),
                    "X-RateLimit-Remaining-Hour": str(remaining_hour),
                    "Retry-After": "1",
                },
            )

        # Check per-hour rate limit
        allowed_hour, remaining_hour = check_rate_limit(
            user_id=user_id,
            window_seconds=RATE_LIMIT_WINDOW_HOUR,
            max_requests=USER_RATE_LIMIT_PER_HOUR,
        )

        if not allowed_hour:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: maximum 10 requests per hour",
                headers={
                    "X-RateLimit-Limit-Second": str(USER_RATE_LIMIT_PER_SECOND),
                    "X-RateLimit-Remaining-Second": str(remaining_second),
                    "X-RateLimit-Limit-Hour": str(USER_RATE_LIMIT_PER_HOUR),
                    "X-RateLimit-Remaining-Hour": "0",
                    "Retry-After": "3600",
                },
            )

    # Validate category inputs
    category_in = validate_category_input(category_in)
    category_not_in = validate_category_input(category_not_in)

    rss_xml = generate_rss(
        limit=MAX_RSS_ITEMS,
        categories_in=category_in,
        categories_not_in=category_not_in,
    )

    response_headers = {
        "Cache-Control": f"public, max-age={RSS_CACHE_MAX_AGE}",
    }

    # Add rate limit headers if authenticated
    if current_user:
        response_headers.update(
            {
                "X-RateLimit-Limit-Second": str(USER_RATE_LIMIT_PER_SECOND),
                "X-RateLimit-Remaining-Second": str(remaining_second),
                "X-RateLimit-Limit-Hour": str(USER_RATE_LIMIT_PER_HOUR),
                "X-RateLimit-Remaining-Hour": str(remaining_hour),
            }
        )

    return Response(
        content=rss_xml,
        media_type="application/rss+xml; charset=utf-8",
        headers=response_headers,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    _ = get_recent_articles(limit=1)
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
