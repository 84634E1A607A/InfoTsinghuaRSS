"""Parser for myhome.tsinghua.edu.cn pages."""

from __future__ import annotations

from typing import Any

from parsers.base import BaseParser


class MyhomeParser(BaseParser):
    """Parser for myhome.tsinghua.edu.cn news and notice pages."""

    @classmethod
    def can_parse(cls, url: str, html: str) -> bool:
        """Check if this is a myhome page.

        Args:
            url: The URL to check
            html: The HTML content to check

        Returns:
            True if URL is from myhome.tsinghua.edu.cn
        """
        return "myhome.tsinghua.edu.cn" in url

    def parse(self, url: str, html: str, session: Any = None, csrf_token: str = "") -> dict[str, Any]:
        """Parse myhome page content.

        Args:
            url: The URL being parsed
            html: The HTML content to parse
            session: Optional requests session (unused in myhome parser)
            csrf_token: Optional CSRF token (unused in myhome parser)

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

        soup = self._make_soup(html)

        # Extract title from News_notice_DetailCtrl1_lblTitle
        title_elem = soup.find("span", id="News_notice_DetailCtrl1_lblTitle")
        if title_elem:
            result["title"] = title_elem.get_text(strip=True)

        # Extract content from News_notice_DetailCtrl1_lblquality_content
        content_elem = soup.find("span", id="News_notice_DetailCtrl1_lblquality_content")
        if content_elem:
            result["content"] = self._clean_html(content_elem)
            result["plain_text"] = self._extract_text(content_elem)

        # Extract publish time and department from lbladd_time
        time_elem = soup.find("span", id="News_notice_DetailCtrl1_lbladd_time")
        if time_elem:
            time_text = time_elem.get_text(strip=True)
            result["publish_time"] = time_text
            # Try to extract department from time text (format: "单位 发布于 时间")
            import re
            dept_match = re.search(r'^(.+?)\s+发布于', time_text)
            if dept_match:
                result["department"] = dept_match.group(1).strip()

        return result
