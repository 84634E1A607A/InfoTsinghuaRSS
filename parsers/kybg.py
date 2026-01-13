"""Parser for kyybgxx.cic.tsinghua.edu.cn (Research Office) pages."""

from __future__ import annotations

import logging
import re
from typing import Any

from config import LIBRARY_ENCODINGS, USER_AGENT
from parsers.base import BaseParser

logger = logging.getLogger(__name__)


class KybgParser(BaseParser):
    """Parser for Research Office (科研院) announcement pages.

    This parser handles:
    - kyybgxx.cic.tsinghua.edu.cn (科研办公信息网)
    - Properly handles GBK encoding
    """

    @classmethod
    def can_parse(cls, url: str, html: str) -> bool:
        """Check if this is a Research Office page.

        Args:
            url: The URL to check
            html: The HTML content to check

        Returns:
            True if URL is from kyybgxx.cic.tsinghua.edu.cn
        """
        return "kyybgxx.cic.tsinghua.edu.cn" in url

    def parse(
        self, url: str, html: str, session: Any = None, csrf_token: str = ""
    ) -> dict[str, Any]:
        """Parse Research Office page content.

        Args:
            url: The URL being parsed
            html: The HTML content to parse (may be incorrectly encoded)
            session: Optional requests session (used to re-fetch with correct encoding)
            csrf_token: Optional CSRF token (unused)

        Returns:
            Dictionary with parsed content
        """
        result: dict[str, Any] = {
            "title": "",
            "content": "",
            "department": "科研院",
            "publish_time": "",
        }

        # Research Office pages use GBK encoding, need to fetch with correct encoding
        html_corrected = self._fetch_with_correct_encoding(url, session)
        if not html_corrected:
            logger.warning(f"Failed to fetch {url} with correct encoding")
            return result

        soup = self._make_soup(html_corrected)

        # Extract title from div with class="td1" containing span with class="style1"
        # Pattern: <td><div align="center" class="td1"><span class="style1">TITLE</span></div></td>
        div1_elem = soup.find("div", class_="td1")
        if div1_elem:
            # Look for span with class="style1"
            span = div1_elem.find("span", class_="style1")
            if span:
                title_text = span.get_text(strip=True)
                if len(title_text) > 10:
                    result["title"] = title_text

        # Fallback: try to find title in other div.td1 elements
        if not result["title"]:
            for div in soup.find_all(
                "div", class_=lambda x: x and "td1" in x.lower() if x else False
            ):
                title_text = div.get_text(strip=True)
                if len(title_text) > 10 and title_text not in ["欢迎", "登录", "首页"]:
                    result["title"] = title_text
                    break

        # Extract content - look for TABLE with class="MsoNormalTable"
        # The content is in a table with class="MsoNormalTable"
        content_table = soup.find("table", class_="MsoNormalTable")
        if content_table:
            result["content"] = self._clean_html(content_table)
        else:
            # Fallback: look for DIV align=center containing substantial content
            # Try to find one with substantial content
            for div in soup.find_all("div", align="center"):
                text = div.get_text(strip=True)
                if len(text) > 200:  # Look for substantial content
                    result["content"] = self._clean_html(div)
                    break
            else:
                # Last fallback: try to find any table with substantial content
                for table in soup.find_all("table"):
                    text = table.get_text(strip=True)
                    if len(text) > 200:  # Look for substantial content
                        result["content"] = self._clean_html(table)
                        break

        # Extract publish time from the content
        # Look for patterns like "2026年1月20日" or "2026-01-20"
        html_text = soup.get_text()
        date_match = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", html_text)
        if date_match:
            result["publish_time"] = (
                f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
            )
        else:
            # Try ISO format
            iso_match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", html_text)
            if iso_match:
                result["publish_time"] = (
                    f"{iso_match.group(1)}-{iso_match.group(2).zfill(2)}-{iso_match.group(3).zfill(2)}"
                )

        return result

    def _fetch_with_correct_encoding(self, url: str, session: Any = None) -> str | None:
        """Fetch URL with correct encoding handling.

        Research Office pages use GBK encoding. This method fetches the page
        and tries multiple encodings to get correct Chinese text.

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
            # Research Office pages use GBK encoding
            encodings = LIBRARY_ENCODINGS

            for encoding in encodings:
                try:
                    # Decode from bytes with specific encoding
                    decoded = response.content.decode(encoding)
                    # Quick check: see if we have reasonable Chinese content
                    if "科研" in decoded or "清华大学" in decoded or "td1" in decoded:
                        logger.debug(f"Successfully decoded kybg page with {encoding}")
                        return decoded
                except UnicodeDecodeError:
                    continue

            # Fallback: use apparent encoding from requests
            response.encoding = response.apparent_encoding
            return response.text

        except Exception as e:
            logger.error(f"Failed to fetch kybg page {url}: {e}")
            return None
