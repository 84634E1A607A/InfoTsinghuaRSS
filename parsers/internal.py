"""Parser for internal info.tsinghua.edu.cn pages."""

from __future__ import annotations

import logging
import re
from html import unescape
from typing import Any

import requests

from config import USER_AGENT
from parsers.base import BaseParser

logger = logging.getLogger(__name__)


class InternalParser(BaseParser):
    """Parser for internal pages on info.tsinghua.edu.cn."""

    @classmethod
    def can_parse(cls, url: str, html: str) -> bool:
        """Check if this is an internal page.

        Args:
            url: The URL to check
            html: The HTML content to check

        Returns:
            True if URL is from info.tsinghua.edu.cn detail page
        """
        is_internal = "info.tsinghua.edu.cn" in url and "/template/detail" in url
        return is_internal

    def parse(
        self, url: str, html: str, session: requests.Session | None = None, csrf_token: str = ""
    ) -> dict[str, Any]:
        """Parse internal page content.

        Args:
            url: The URL being parsed
            html: The HTML content to parse
            session: Optional requests session with cookies
            csrf_token: Optional CSRF token for API requests

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

        # Extract xxid from URL
        xxid_match = re.search(r"xxid=([a-f0-9]+)", url)
        if not xxid_match:
            logger.warning(f"Could not extract xxid from {url}")
            return self._parse_static(html, result)

        xxid = xxid_match.group(1)

        # Try to get CSRF token from: parameter, meta tag, or cookie
        token = csrf_token

        if not token:
            # Extract CSRF token from meta tag
            csrf_match = re.search(
                r'<meta\s+name=["\']_csrf["\']\s+content=["\']([a-z0-9\-]+)["\']', html
            )
            if csrf_match:
                token = csrf_match.group(1)

        if not token and session:
            # Check XSRF-TOKEN cookie
            for cookie in session.cookies:
                if cookie.name == "XSRF-TOKEN":
                    token = cookie.value
                    break

        if not token:
            logger.warning(f"Could not find CSRF token in {url}, falling back to static HTML")
            return self._parse_static(html, result)

        # Make API request
        try:
            api_url = "https://info.tsinghua.edu.cn/b/info/xxfb_fg/xnzx/template/detail"
            params = {
                "xxid": xxid,
                "preview": "",
                "_csrf": token,
            }

            # Use provided session or create new one
            req_session = session if session else requests.Session()
            # Set user agent if we created a new session
            if not session:
                req_session.headers.update({"User-Agent": USER_AGENT})
            response = req_session.post(api_url, params=params, timeout=10)

            if response.status_code != 200:
                logger.warning(f"API request failed with status {response.status_code} for {url}")
                return self._parse_static(html, result)

            data = response.json()

            # Extract content from API response
            if data.get("result") == "success" and "object" in data:
                obj = data["object"]

                # The actual data is in 'xxDto' field
                xx_dto = obj.get("xxDto", obj)

                # Extract title
                if "bt" in xx_dto:
                    result["title"] = unescape(xx_dto["bt"])

                # Extract content (HTML in 'nr' field)
                if "nr" in xx_dto:
                    content_html = xx_dto["nr"]
                    # Decode HTML entities (e.g., &lt;p&gt; -> <p>)
                    content_html = unescape(content_html)
                    result["content"] = content_html
                    # Extract plain text from HTML
                    soup = self._make_soup(f"<div>{content_html}</div>")
                    result["plain_text"] = self._extract_text(soup)

                # Extract department
                if "dw" in xx_dto:
                    result["department"] = xx_dto["dw"]

                # Extract publish time
                if "fbsj" in xx_dto:
                    result["publish_time"] = xx_dto["fbsj"]

                logger.debug(f"Successfully parsed {url} via API")
                return result
            else:
                logger.warning(f"API returned unexpected result for {url}: {data.get('result')}")
                return self._parse_static(html, result)

        except Exception as e:
            logger.warning(f"Error calling API for {url}: {e}")
            return self._parse_static(html, result)

    def _parse_static(self, html: str, result: dict[str, Any]) -> dict[str, Any]:
        """Parse static HTML fallback.

        Args:
            html: The HTML content to parse
            result: The result dict to populate

        Returns:
            Updated result dict
        """
        soup = self._make_soup(html)

        # Extract title from h2.title or div.title
        title_elem = soup.find("h2", class_=lambda x: x and "title" in x.split())
        if not title_elem:
            title_elem = soup.find("div", class_=lambda x: x and "title" in x.split())

        if title_elem:
            result["title"] = title_elem.get_text(strip=True)

        # Extract content from div.jianjie.xiangqingchakan
        content_elem = soup.find("div", class_="jianjie xiangqingchakan")
        if not content_elem:
            # Fallback: try to find any div with "jianjie" in class
            content_elem = soup.find("div", class_=lambda x: x and "jianjie" in x.split())

        if content_elem:
            result["content"] = self._clean_html(content_elem)
            result["plain_text"] = self._extract_text(content_elem)

        # Extract department from label#fromFlag
        dept_label = soup.find("label", id="fromFlag")
        if dept_label:
            span = dept_label.find("span")
            if span:
                result["department"] = span.get_text(strip=True)

        # Extract publish time from label#timeFlag
        time_label = soup.find("label", id="timeFlag")
        if time_label:
            span = time_label.find("span")
            if span:
                result["publish_time"] = span.get_text(strip=True)

        return result
