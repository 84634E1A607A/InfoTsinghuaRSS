"""FastAPI application for RSS feed generation with scheduled scraping."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from auth import (
    RateLimitMiddleware,
    TokenManagement,
    get_current_user,
    get_current_user_optional,
    get_gitlab_authorization_url,
    handle_gitlab_callback,
)
from auth_db import init_auth_db
from config import (
    API_DESCRIPTION,
    API_TITLE,
    API_VERSION,
    GITLAB_REDIRECT_URI,
    MAX_PAGES_PER_RUN,
    MAX_RSS_ITEMS,
    MIN_SCRAPE_INTERVAL,
    OAUTH_ENABLED,
    RATE_LIMIT_PERIOD,
    RATE_LIMIT_REQUESTS,
    RSS_CACHE_MAX_AGE,
    SCRAPE_INTERVAL,
    SERVER_HOST,
    SERVER_PORT,
)
from database import get_last_scrape_time, get_recent_articles, init_db, set_last_scrape_time
from rss import generate_rss, validate_category_input
from scraper import ArticleStateEnum, InfoTsinghuaScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
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
                        logger.warning(f"Skipping item {item.get('xxid', 'UNKNOWN')} due to error: {e}")
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

# Add rate limiting exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add per-user rate limiting middleware
app.add_middleware(RateLimitMiddleware)


@app.get("/")
async def root(
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Root endpoint with API information."""
    response = {
        "message": "Tsinghua Info RSS Feed",
        "feed_url": "/rss",
        "docs_url": "/docs",
        "auth_enabled": OAUTH_ENABLED,
    }

    if current_user:
        response["user"] = {
            "username": current_user["username"],
            "email": current_user["email"],
        }
        response["token_management"] = {
            "list_tokens": "GET /auth/tokens",
            "create_token": "POST /auth/tokens",
            "delete_token": "DELETE /auth/tokens/{token}",
            "rotate_token": "POST /auth/tokens/{token}/rotate",
        }

    return response


# =============================================================================
# OAuth Endpoints
# =============================================================================

class TokenCreateRequest(BaseModel):
    """Request model for creating a token."""

    name: str | None = None


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
    """Handle GitLab OAuth callback."""
    if not OAUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth authentication is not enabled",
        )

    result = await handle_gitlab_callback(code, state)

    # Create a token for the user
    token = TokenManagement.create_token(result["user_id"], "OAuth Login Token")

    # Redirect to frontend with token
    # For RSS readers, you might want to show the token in a page
    return {
        "message": "Authentication successful",
        "token": token,
        "user_id": result["user_id"],
        "instructions": f"Use this token with X-API-Token header or ?token= query parameter to access /rss",
    }


# =============================================================================
# Token Management Endpoints
# =============================================================================

@app.get("/auth/tokens")
async def list_tokens(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all tokens for the current user."""
    tokens = TokenManagement.list_tokens(current_user["user_id"])

    # Return safe token info (partial token)
    return [
        {
            "id": token["id"],
            "token": token["token"][:8] + "...",  # Show only first 8 chars
            "name": token["name"],
            "last_used_at": token["last_used_at"],
            "created_at": token["created_at"],
        }
        for token in tokens
    ]


@app.post("/auth/tokens")
async def create_token(
    request: TokenCreateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Create a new auth token."""
    token = TokenManagement.create_token(current_user["user_id"], request.name)

    return {
        "token": token,
        "message": "Token created successfully",
        "instructions": f"Use this token with X-API-Token header to access /rss",
    }


@app.delete("/auth/tokens/{token}")
async def delete_token(
    token: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Delete an auth token."""
    success = TokenManagement.delete_token(token, current_user["user_id"])

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )

    return {"message": "Token deleted successfully"}


@app.post("/auth/tokens/{token}/rotate")
async def rotate_token(
    token: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Rotate an auth token (create new, delete old)."""
    new_token = TokenManagement.rotate_token(token, current_user["user_id"])

    return {
        "token": new_token,
        "message": "Token rotated successfully",
        "instructions": f"Use the new token with X-API-Token header to access /rss",
    }


# =============================================================================
# RSS Feed Endpoint (Protected)
# =============================================================================


@app.get("/rss")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD}")
async def rss_feed(
    request: Request,
    category_in: list[str] | None = Query(None, description="Categories to filter in (only these categories)"),
    category_not_in: list[str] | None = Query(None, alias="not_in", description="Categories to filter out (exclude these categories)"),
    token: str | None = Query(None, description="Authentication token (can also use X-API-Token header)"),
    current_user: dict[str, Any] | None = Depends(lambda r, t=None, q=None: get_current_user_optional(r, t, q)),
) -> Response:
    """Generate and return RSS feed (requires authentication).

    Query Parameters:
    - category_in: Filter to only include articles with these categories (e.g., ?category_in=通知&category_in=公告)
    - not_in: Exclude articles with these categories (e.g., ?not_in=招聘&not_in=讲座)
    - token: Authentication token (alternative to X-API-Token header)

    Authentication:
    - Use X-API-Token header or ?token= query parameter
    - Get a token by visiting /auth/login (GitLab OAuth)
    """
    # Manually extract token from query for authentication
    if not current_user and token:
        current_user = get_current_user_optional(request, query_token=token)

    if OAUTH_ENABLED and not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Visit /auth/login to authenticate",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate category inputs
    category_in = validate_category_input(category_in)
    category_not_in = validate_category_input(category_not_in)

    rss_xml = generate_rss(
        limit=MAX_RSS_ITEMS,
        categories_in=category_in,
        categories_not_in=category_not_in,
    )

    return Response(
        content=rss_xml,
        media_type="application/rss+xml; charset=utf-8",
        headers={
            "Cache-Control": f"public, max-age={RSS_CACHE_MAX_AGE}",
        },
    )


@app.get("/health")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD}")
async def health(request: Request) -> dict[str, str]:
    """Health check endpoint."""
    _ = get_recent_articles(limit=1)
    return {
        "status": "healthy"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
