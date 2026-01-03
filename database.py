"""Database models and operations for the RSS scraper."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from config import DB_PATH


def _ensure_db_permissions() -> None:
    """Ensure database file has restrictive permissions."""
    try:
        if DB_PATH.exists():
            # Set file permissions to 0600 (owner read/write only)
            os.chmod(DB_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        # Silently fail on systems that don't support Unix permissions
        pass


@contextmanager
def get_db_connection():
    """Get a database connection with context management.

    Yields:
        sqlite3.Connection: Database connection
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database schema."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                xxid TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                department TEXT,
                category TEXT,
                publish_time INTEGER NOT NULL,
                url TEXT NOT NULL,
                digest TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS scrape_metadata (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_publish_time ON articles(publish_time DESC)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_xxid ON articles(xxid)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_digest ON articles(digest)
        """)

        conn.commit()

    # Ensure restrictive permissions on database file
    _ensure_db_permissions()


def compute_digest(article: dict[str, Any]) -> str:
    """Compute a digest hash for an article.

    Args:
        article: Article dictionary

    Returns:
        SHA256 hex digest of the article content
    """
    # Create a string with all relevant fields for deduplication
    content_str = f"{article.get('title', '')}|{article.get('content', '')}|{article.get('department', '')}|{article.get('category', '')}"
    return hashlib.sha256(content_str.encode("utf-8")).hexdigest()


def validate_article(article: dict[str, Any]) -> None:
    """Validate article data before database insertion.

    Args:
        article: Article dictionary to validate

    Raises:
        ValueError: If article data is invalid
    """
    # Validate required string fields and their lengths
    string_fields = {
        "xxid": 100,
        "title": 1000,
        "url": 2000,
        "department": 200,
        "category": 100,
    }

    for field, max_length in string_fields.items():
        if field in article and article[field] is not None:
            if not isinstance(article[field], str):
                raise ValueError(f"{field} must be string")
            if len(article[field]) > max_length:
                raise ValueError(f"{field} exceeds maximum length of {max_length}")

    # Validate publish_time is a valid timestamp
    if "publish_time" in article and not isinstance(article["publish_time"], int):
        raise ValueError("publish_time must be integer")

    # Validate content length (can be very long for HTML)
    if "content" in article and article["content"] is not None:
        if not isinstance(article["content"], str):
            raise ValueError("content must be string")
        if len(article["content"]) > 1_000_000:  # 1MB limit
            raise ValueError("content exceeds maximum length of 1MB")


def upsert_article(article: dict[str, Any]) -> int:
    """Insert or update an article.

    Args:
        article: Article dictionary with keys:
            - xxid: Article ID
            - title: Article title
            - content: Article content (HTML)
            - department: Publishing department
            - category: Article category
            - publish_time: Publish timestamp (milliseconds)
            - url: Article URL

    Returns:
        True if the article was newly inserted, False if updated or skipped
    """
    # Validate article data before insertion
    validate_article(article)

    digest = compute_digest(article)
    now = int(datetime.now(timezone.utc).timestamp() * 1000)

    with get_db_connection() as conn:
        # Check if article exists with same digest
        cursor = conn.execute("SELECT digest FROM articles WHERE xxid = ?", (article["xxid"],))
        existing = cursor.fetchone()

        # If article exists and digest is the same, skip update
        if existing and existing["digest"] == digest:
            return 2  # Skipped

        # Insert or update article
        cursor = conn.execute(
            """
            INSERT INTO articles (xxid, title, content, department, category, publish_time, url, digest, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(xxid) DO UPDATE SET
                title = excluded.title,
                content = excluded.content,
                department = excluded.department,
                category = excluded.category,
                publish_time = excluded.publish_time,
                url = excluded.url,
                digest = excluded.digest,
                updated_at = excluded.updated_at
            """,
            (
                article["xxid"],
                article["title"],
                article["content"],
                article["department"],
                article["category"],
                article["publish_time"],
                article["url"],
                digest,
                now,
                now,
            ),
        )
        conn.commit()

    # Ensure permissions remain restrictive after database modifications
    _ensure_db_permissions()

    # Return True only if it was a new insert
    return 0 if existing is None else 1  # 0: New, 1: Updated


def get_recent_articles(limit: int = 100) -> list[dict[str, Any]]:
    """Get recent articles ordered by publish time.

    Args:
        limit: Maximum number of articles to return

    Returns:
        List of article dictionaries
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT xxid, title, content, department, category, publish_time, url, created_at, updated_at
            FROM articles
            ORDER BY publish_time DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()

    return [dict(row) for row in rows]


def get_articles_since(timestamp_ms: int) -> list[dict[str, Any]]:
    """Get articles published since a given timestamp.

    Args:
        timestamp_ms: Timestamp in milliseconds

    Returns:
        List of article dictionaries
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT xxid, title, content, department, category, publish_time, url, created_at, updated_at
            FROM articles
            WHERE publish_time >= ?
            ORDER BY publish_time DESC
            """,
            (timestamp_ms,),
        )
        rows = cursor.fetchall()

    return [dict(row) for row in rows]


def article_exists(xxid: str) -> bool:
    """Check if an article exists in the database.

    Args:
        xxid: Article ID

    Returns:
        True if article exists, False otherwise
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM articles WHERE xxid = ? LIMIT 1",
            (xxid,),
        )
        return cursor.fetchone() is not None


def get_last_scrape_time() -> int | None:
    """Get the last scrape timestamp in milliseconds.

    Returns:
        Last scrape timestamp in milliseconds, or None if never scraped
    """
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT value FROM scrape_metadata WHERE key = 'last_scrape_time'")
        row = cursor.fetchone()
        return row["value"] if row else None


def set_last_scrape_time(timestamp_ms: int) -> None:
    """Set the last scrape timestamp.

    Args:
        timestamp_ms: Timestamp in milliseconds
    """
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO scrape_metadata (key, value) VALUES ('last_scrape_time', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (timestamp_ms,),
        )
        conn.commit()
