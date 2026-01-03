"""RSS feed generation for scraped articles."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

import feedgenerator

from config import (
    FEED_DESCRIPTION,
    FEED_LANGUAGE,
    FEED_LINK,
    FEED_TITLE,
    MAX_RSS_ITEMS_LIMIT,
)
from database import get_db_connection


def strip_styles_from_html(html: str) -> str:
    """Remove style attributes and style tags from HTML.

    Args:
        html: HTML string to clean

    Returns:
        HTML string with styles removed
    """
    # Remove style tags
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove style attributes from any tag
    html = re.sub(r'\s+style\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)

    # Remove class attributes (optional - remove if you want to keep classes)
    # html = re.sub(r'\s+class\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)

    # Clean up extra whitespace
    html = re.sub(r'\s+', ' ', html)
    html = re.sub(r'>\s+<', '><', html)

    return html.strip()


def generate_rss(
    limit: int = 100,
    categories_in: list[str] | None = None,
    categories_not_in: list[str] | None = None,
) -> str:
    """Generate RSS feed from database articles.

    Args:
        limit: Maximum number of articles to include (must be positive, max 1000)
        categories_in: List of categories to filter in (only these categories)
        categories_not_in: List of categories to filter out (exclude these categories)

    Returns:
        RSS feed as XML string
    """
    # Validate limit parameter
    if not isinstance(limit, int) or limit < 1:
        limit = 100
    elif limit > MAX_RSS_ITEMS_LIMIT:
        limit = MAX_RSS_ITEMS_LIMIT
    feed = feedgenerator.Rss201rev2Feed(
        title=FEED_TITLE,
        link=FEED_LINK,
        description=FEED_DESCRIPTION,
        language=FEED_LANGUAGE,
    )

    # Build query with filters
    query = """
        SELECT xxid, title, content, department, category, publish_time, url
        FROM articles
        WHERE 1=1
    """
    params: list[Any] = []

    if categories_in and len(categories_in) > 0:
        placeholders = ",".join("?" * len(categories_in))
        query += f" AND category IN ({placeholders})"
        params.extend(categories_in)

    if categories_not_in and len(categories_not_in) > 0:
        placeholders = ",".join("?" * len(categories_not_in))
        query += f" AND category NOT IN ({placeholders})"
        params.extend(categories_not_in)

    query += " ORDER BY publish_time DESC LIMIT ?"
    params.append(limit)

    with get_db_connection() as conn:
        cursor = conn.execute(query, params)
        articles = cursor.fetchall()

    for article in articles:
        article_dict = dict(article)
        publish_time = datetime.fromtimestamp(
            article_dict["publish_time"] / 1000,
            tz=timezone.utc,
        )

        # Build description with metadata
        description_parts = []
        if article_dict.get("department"):
            description_parts.append(f"<p><strong>发布单位:</strong> {article_dict['department']}</p>")
        if article_dict.get("category"):
            description_parts.append(f"<p><strong>分类:</strong> {article_dict['category']}</p>")

        # Add content if available, with styles removed
        if article_dict.get("content"):
            clean_content = strip_styles_from_html(article_dict["content"])
            description_parts.append(clean_content)

        description = "".join(description_parts) if description_parts else article_dict["title"]

        feed.add_item(
            title=article_dict["title"],
            link=article_dict["url"],
            description=description,
            pubdate=publish_time,
            unique_id=article_dict["xxid"],
        )

    return feed.writeString("utf-8")
