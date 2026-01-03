"""Parser for lib.tsinghua.edu.cn pages with GBK/UTF-8-SIG encoding."""

from __future__ import annotations

import logging
from typing import Any

from bs4 import BeautifulSoup

from config import LIBRARY_ENCODINGS, USER_AGENT
from parsers.base import BaseParser

logger = logging.getLogger(__name__)


class LibraryParser(BaseParser):
    """Parser for Tsinghua University Library pages."""

    @classmethod
    def can_parse(cls, url: str, html: str) -> bool:
        """Check if this is a library page.

        Args:
            url: The URL to check
            html: The HTML content to check

        Returns:
            True if URL is from lib.tsinghua.edu.cn
        """
        return "lib.tsinghua.edu.cn" in url

    def parse(self, url: str, html: str, session: Any = None, csrf_token: str = "") -> dict[str, Any]:
        """Parse library page content.

        Args:
            url: The URL being parsed
            html: The HTML content to parse (may be incorrectly encoded)
            session: Optional requests session (used to re-fetch with correct encoding)
            csrf_token: Optional CSRF token (not used for library pages)

        Returns:
            Dictionary with parsed content
        """
        result: dict[str, Any] = {
            "title": "",
            "content": "",
            "plain_text": "",
            "department": "",
            "publish_time": "",
        }

        # Library pages often have encoding issues, need to fetch with correct encoding
        html_corrected = self._fetch_with_correct_encoding(url, session)
        if not html_corrected:
            logger.warning(f"Failed to fetch {url} with correct encoding")
            return result

        soup = self._make_soup(html_corrected)

        # Extract title from h2
        title_elem = soup.find("h2")
        if not title_elem:
            title_elem = soup.find("h1")

        if title_elem:
            result["title"] = title_elem.get_text(strip=True)

        # Extract content from div.v_news_content
        content_elem = soup.find("div", class_="v_news_content")
        if content_elem:
            result["content"] = self._clean_html(content_elem)
            result["plain_text"] = self._extract_text(content_elem)

        # Extract publish time from div.date
        time_elem = soup.find("div", class_="date")
        if time_elem:
            result["publish_time"] = time_elem.get_text(strip=True)

        # Department is always "图书馆" (Library) for these pages
        result["department"] = "图书馆"

        logger.debug(f"Successfully parsed library page {url}")
        return result

    def _fetch_with_correct_encoding(self, url: str, session: Any = None) -> str | None:
        """Fetch URL with correct encoding handling.

        Library pages often declare wrong encoding in headers. This method
        fetches the page and tries multiple encodings to get correct Chinese text.

        Args:
            url: The URL to fetch
            session: Optional requests session to use

        Returns:
            Correctly decoded HTML string or None on failure
        """
        import requests

        try:
            # Use provided session or create new one
            req_session = session if session else requests.Session()
            # Set user agent if we created a new session
            if not session:
                req_session.headers.update({"User-Agent": USER_AGENT})

            # Fetch with allow_redirects to follow any redirects
            response = req_session.get(url, timeout=10, allow_redirects=True)

            # Try to detect encoding from content
            # Library pages often use GBK but declare ISO-8859-1
            encodings = LIBRARY_ENCODINGS

            for encoding in encodings:
                try:
                    # Decode from bytes with specific encoding
                    decoded = response.content.decode(encoding)
                    # Quick check: see if we have reasonable Chinese content
                    if "图书馆" in decoded or "v_news_content" in decoded:
                        logger.debug(f"Successfully decoded library page with {encoding}")
                        return decoded
                except UnicodeDecodeError:
                    continue

            # Fallback: use apparent encoding from requests
            response.encoding = response.apparent_encoding
            return response.text

        except Exception as e:
            logger.error(f"Failed to fetch library page {url}: {e}")
            return None
