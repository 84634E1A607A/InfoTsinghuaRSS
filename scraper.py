#!/usr/bin/env python3
"""Scraper for info.tsinghua.edu.cn."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any

import requests

logger = logging.getLogger(__name__)

class ArticleStateEnum(IntEnum):
    NEW = 0
    UPDATED = 1
    SKIPPED = 2

class InfoTsinghuaScraper:
    """Scraper for Tsinghua University Info Portal."""

    BASE_URL = "https://info.tsinghua.edu.cn"
    LIST_URL = f"{BASE_URL}/f/info/xxfb_fg/xnzx/template/more?lmid=all"
    LIST_API = f"{BASE_URL}/b/info/xxfb_fg/xnzx/template/more"
    DETAIL_URL_TEMPLATE = f"{BASE_URL}/f/info/xxfb_fg/xnzx/template/detail?xxid={{xxid}}"

    # Rate limiting: 3 requests per second
    RATE_LIMIT = 3.0  # requests per second
    MIN_REQUEST_INTERVAL = 1.0 / RATE_LIMIT  # seconds between requests

    def __init__(self) -> None:
        """Initialize the scraper."""
        self._session: requests.Session | None = None
        self._csrf_token: str = ""
        self._last_request_time: float = 0.0

    def __enter__(self) -> InfoTsinghuaScraper:
        """Enter context manager."""
        self._init_session()
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context manager."""
        if self._session:
            self._session.close()

    def _rate_limit(self) -> None:
        """Apply rate limiting by sleeping if necessary."""
        now = time.time()
        time_since_last_request = now - self._last_request_time

        if time_since_last_request < self.MIN_REQUEST_INTERVAL:
            sleep_time = self.MIN_REQUEST_INTERVAL - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def _init_session(self) -> None:
        """Initialize session by visiting the page to get cookies and CSRF token."""
        logger.info("Initializing session...")

        self._session = requests.Session()

        # Set user agent
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        # Visit the list page to get cookies and CSRF token
        response = self._session.get(self.LIST_URL)
        response.raise_for_status()

        # Extract CSRF token from meta tag
        content = response.text
        csrf_match = re.search(r'<meta\s+name=["\']_csrf["\']\s+content=["\']([a-z0-9\-]+)', content)
        if csrf_match:
            self._csrf_token = csrf_match.group(1)
        else:
            # Try to find in script tags
            script_match = re.search(r'_csrf\s*[:=]\s*["\']([a-z0-9\-]+)', content)
            if script_match:
                self._csrf_token = script_match.group(1)
            else:
                # Last resort: check for XSRF-TOKEN in cookies
                for cookie in self._session.cookies:
                    if cookie.name in ["XSRF-TOKEN", "X-CSRF-TOKEN"]:
                        self._csrf_token = cookie.value
                        break

        logger.info(f"Got {len(self._session.cookies)} cookies and CSRF token: {self._csrf_token[:20] if self._csrf_token else 'EMPTY'}...")

    def fetch_list(
        self,
        lmid: str = "all",
        page: int = 1,
        page_size: int = 30,
    ) -> list[dict[str, Any]]:
        """Fetch the list of information items.

        Args:
            lmid: Column ID (default "all" for all columns)
            page: Page number (1-indexed)
            page_size: Number of items per page (default 30)

        Returns:
            List of information items.
        """
        if not self._session or not self._csrf_token:
            raise RuntimeError("Scraper must be used as context manager")

        params = {
            "oType": "xs",
            "lmid": lmid,
            "lydw": "",
            "currentPage": page,
            "length": page_size,
            "xxflid": "",
            "_csrf": self._csrf_token,
        }

        headers = {
            "Referer": self.LIST_URL,
            "Origin": self.BASE_URL,
        }

        self._rate_limit()
        response = self._session.post(self.LIST_API, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get("result") != "success":
            raise RuntimeError(f"API error: {data.get('msg', 'Unknown error')}")

        return data.get("object", {}).get("dataList", [])

    def fetch_detail(self, xxid: str) -> dict[str, Any]:
        """Fetch the detail page for an information item.

        Args:
            xxid: Information ID

        Returns:
            Dictionary containing detail information with keys:
                - title: Title of the information
                - content: HTML content of the information
                - department: Publishing department
                - publish_time: Publish timestamp
                - category: Category name
        """
        if not self._session:
            raise RuntimeError("Scraper must be used as context manager")

        url = self.DETAIL_URL_TEMPLATE.format(xxid=xxid)

        headers = {
            "Referer": self.LIST_URL,
        }

        self._rate_limit()
        response = self._session.get(url, headers=headers)
        response.raise_for_status()
        html = response.text

        # Extract title from h2 tag
        title = ""
        title_match = re.search(r'<h2[^>]*class="[^"]*detail-title[^"]*"[^>]*>(.*?)</h2>', html, re.DOTALL)
        if title_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        else:
            # Fallback: any h2 tag
            title_match = re.search(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
            if title_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()

        # Extract content from detail-content or content-body div
        content = ""
        content_match = re.search(r'<div[^>]*class="[^"]*detail-content[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        if not content_match:
            content_match = re.search(r'<div[^>]*class="[^"]*content-body[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        if content_match:
            content = content_match.group(0)

        # Extract metadata from detail-meta div
        department = ""
        publish_time = ""

        # Try to find department
        dept_patterns = [
            r'<span[^>]*>[^<]*发布单位[：:]\s*([^<]+)</span>',
            r'<span[^>]*class="[^"]*department[^"]*"[^>]*>([^<]+)</span>',
        ]
        for pattern in dept_patterns:
            match = re.search(pattern, html)
            if match:
                department = match.group(1).strip()
                break

        # Try to find publish time
        time_patterns = [
            r'<span[^>]*>[^<]*发布时间[：:]\s*([^<]+)</span>',
        ]
        for pattern in time_patterns:
            match = re.search(pattern, html)
            if match:
                publish_time = match.group(1).strip()
                break

        return {
            "title": title,
            "content": content,
            "department": department,
            "publish_time": publish_time,
        }

    def fetch_items(
        self,
        lmid: str = "all",
        max_pages: int | None = None,
        page_size: int = 30,
    ) -> list[dict[str, Any]]:
        """Fetch multiple pages of information items.

        Args:
            lmid: Column ID (default "all")
            max_pages: Maximum number of pages to fetch (None for unlimited)
            page_size: Number of items per page

        Returns:
            List of information items with details.
        """
        all_items = []
        page = 1

        while True:
            items = self.fetch_list(lmid=lmid, page=page, page_size=page_size)

            if not items:
                break

            all_items.extend(items)

            if max_pages and page >= max_pages:
                break

            page += 1

        return all_items

    def upsert_article(self, item: dict[str, Any]) -> ArticleStateEnum:
        """Insert or update an article from a list item.

        Args:
            item: List item dictionary from the API

        Returns:
            True if the article was newly inserted, False if updated

        Raises:
            ValueError: If required fields are missing from the item
        """
        from database import upsert_article as db_upsert

        # Validate required fields
        required_fields = ["xxid", "bt", "fbsj", "url"]
        missing_fields = [field for field in required_fields if field not in item or not item[field]]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        article = {
            "xxid": item["xxid"],
            "title": item["bt"],
            "content": "",  # Content not available in list view
            "department": item.get("dwmc", ""),
            "category": item.get("lmmc", ""),
            "publish_time": item["fbsj"],
            "url": f"{self.BASE_URL}{item['url']}",
        }

        state = db_upsert(article)
        return ArticleStateEnum(state)

    @staticmethod
    def parse_timestamp(timestamp_ms: int) -> datetime:
        """Parse millisecond timestamp to datetime.

        Args:
            timestamp_ms: Timestamp in milliseconds

        Returns:
            UTC datetime object
        """
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def main() -> None:
    """Test the scraper."""
    with InfoTsinghuaScraper() as scraper:
        # Fetch first page
        items = scraper.fetch_list(page=1)
        print(f"Fetched {len(items)} items")

        # Print first 3 items
        for item in items[:3]:
            print(f"\nTitle: {item['bt']}")
            print(f"Category: {item['lmmc']}")
            print(f"Department: {item['dwmc']}")
            print(f"Time: {item['time']}")
            print(f"URL: {scraper.BASE_URL}{item['url']}")

            # Parse timestamp
            dt = scraper.parse_timestamp(item['fbsj'])
            print(f"Publish Time: {dt.isoformat()}")


if __name__ == "__main__":
    main()
