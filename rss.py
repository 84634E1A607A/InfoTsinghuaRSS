"""RSS feed generation for scraped articles."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedgenerator
from database import get_db_connection


FEED_TITLE = "清华大学信息门户"
FEED_DESCRIPTION = "清华大学信息门户最新通知"
FEED_LINK = "https://info.tsinghua.edu.cn"


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


def generate_rss(limit: int = 100) -> str:
    """Generate RSS feed from database articles.

    Args:
        limit: Maximum number of articles to include

    Returns:
        RSS feed as XML string
    """
    feed = feedgenerator.Rss201rev2Feed(
        title=FEED_TITLE,
        link=FEED_LINK,
        description=FEED_DESCRIPTION,
        language="zh-CN",
    )

    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT xxid, title, content, department, category, publish_time, url
            FROM articles
            ORDER BY publish_time DESC
            LIMIT ?
            """,
            (limit,),
        )
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
