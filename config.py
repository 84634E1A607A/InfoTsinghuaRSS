"""Configuration for the Info Tsinghua RSS scraper application."""

from __future__ import annotations

import os
from pathlib import Path


# =============================================================================
# Application Settings
# =============================================================================

# Application metadata
APP_NAME = "InfoTsinghuaRSS"
APP_VERSION = "0.0.1"
APP_DESCRIPTION = "RSS feed for Tsinghua University Info Portal"


# =============================================================================
# HTTP Client Settings
# =============================================================================

# User agent for all HTTP requests
USER_AGENT = f"{APP_NAME}/{APP_VERSION}"

# Default timeout for HTTP requests (seconds)
HTTP_TIMEOUT = 10


# =============================================================================
# Scraper Settings
# =============================================================================

# Base URL for info.tsinghua.edu.cn
BASE_URL = "https://info.tsinghua.edu.cn"

# URL endpoints
LIST_URL = f"{BASE_URL}/f/info/xxfb_fg/xnzx/template/more?lmid=all"
LIST_API = f"{BASE_URL}/b/info/xxfb_fg/xnzx/template/more"
DETAIL_URL_TEMPLATE = f"{BASE_URL}/f/info/xxfb_fg/xnzx/template/detail?xxid={{xxid}}"

# Rate limiting: requests per second
RATE_LIMIT = 3.0
MIN_REQUEST_INTERVAL = 1.0 / RATE_LIMIT  # seconds between requests


# =============================================================================
# Scheduler Settings
# =============================================================================

# Scrape interval in seconds (15 minutes for production)
SCRAPE_INTERVAL = 15 * 60
# SCRAPE_INTERVAL = 60  # Test: 1 minute

# Minimum time between scrapes in seconds (10 minutes)
MIN_SCRAPE_INTERVAL = 10 * 60
# MIN_SCRAPE_INTERVAL = 90  # Test: 1.5 minutes

# Maximum pages to scrape per run
MAX_PAGES_PER_RUN = 10
# MAX_PAGES_PER_RUN = 5  # Test: fewer pages


# =============================================================================
# Database Settings
# =============================================================================

# Database file path
DB_PATH = Path("info_rss.db")

# Database schema version (for future migrations)
DB_SCHEMA_VERSION = 1


# =============================================================================
# RSS Feed Settings
# =============================================================================

# Feed metadata
FEED_TITLE = "清华大学信息门户"
FEED_DESCRIPTION = "清华大学信息门户最新通知"
FEED_LINK = BASE_URL
FEED_LANGUAGE = "zh-CN"

# Maximum articles to return in RSS feed
MAX_RSS_ITEMS = 100

# Maximum allowed items in RSS feed (hard limit)
MAX_RSS_ITEMS_LIMIT = 1000

# Cache control for RSS feed (seconds)
RSS_CACHE_MAX_AGE = 300  # 5 minutes


# =============================================================================
# API Server Settings
# =============================================================================

# FastAPI app metadata
API_TITLE = "Tsinghua Info RSS"
API_DESCRIPTION = "RSS feed for Tsinghua University Info Portal"
API_VERSION = "1.0.0"

# Server host and port
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000


# =============================================================================
# Parser Settings
# =============================================================================

# Encodings to try for library pages (in order)
LIBRARY_ENCODINGS = ["utf-8-sig", "gbk", "gb2312", "gb18030", "utf-8"]


# =============================================================================
# Rate Limiting Settings
# =============================================================================

# Rate limiting for RSS endpoints (requests per minute)
RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_PERIOD = 60  # seconds


# =============================================================================
# OAuth Authentication Settings
# =============================================================================

# Enable/disable OAuth authentication
OAUTH_ENABLED = os.getenv("OAUTH_ENABLED", "true").lower() == "true"

# GitLab OAuth configuration
GITLAB_URL = os.getenv("GITLAB_URL", "https://git.tsinghua.edu.cn")
GITLAB_CLIENT_ID = os.getenv("GITLAB_CLIENT_ID", "")
GITLAB_CLIENT_SECRET = os.getenv("GITLAB_CLIENT_SECRET", "")

# OAuth redirect URI (must match GitLab app configuration)
GITLAB_REDIRECT_URI = os.getenv("GITLAB_REDIRECT_URI", "http://localhost:8000/auth/callback")

# OAuth scopes
GITLAB_SCOPES = ["read_user"]

# Session secret for OAuth state
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SESSION_SECRET = os.getenv("SESSION_SECRET", "")


# =============================================================================
# Auth Token Settings
# =============================================================================

# Token rotation: force rotation after N days
TOKEN_ROTATION_DAYS = 90

# Maximum active tokens per user
MAX_TOKENS_PER_USER = 10


# =============================================================================
# Per-User Rate Limiting Settings
# =============================================================================

# Rate limits per authenticated user (requests / period)
USER_RATE_LIMIT_PER_SECOND = 1
USER_RATE_LIMIT_PER_HOUR = 10

# Rate limit windows
RATE_LIMIT_WINDOW_SECOND = 1  # 1 second window
RATE_LIMIT_WINDOW_HOUR = 3600  # 1 hour window
