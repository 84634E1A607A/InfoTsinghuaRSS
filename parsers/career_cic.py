"""Parser for career.cic.tsinghua.edu.cn job posting pages."""

from __future__ import annotations

from typing import Any

from parsers.base import BaseParser


class CareerCicParser(BaseParser):
    """Parser for career center job posting pages."""

    @classmethod
    def can_parse(cls, url: str, html: str) -> bool:
        """Check if this is a career center page.

        Args:
            url: The URL to check
            html: The HTML content to check

        Returns:
            True if URL is from career.cic.tsinghua.edu.cn
        """
        return "career.cic.tsinghua.edu.cn" in url

    def parse(
        self, url: str, html: str, session: Any = None, csrf_token: str = ""
    ) -> dict[str, Any]:
        """Parse career center page content.

        Args:
            url: The URL being parsed
            html: The HTML content to parse
            session: Optional requests session (unused in career parser)
            csrf_token: Optional CSRF token (unused in career parser)

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

        # Extract title - typically in h1, h2, or strong tags
        for tag in ["h1", "h2", "h3"]:
            title_elem = soup.find(tag)
            if title_elem:
                potential_title = title_elem.get_text(strip=True)
                # Filter out very short or generic titles
                if len(potential_title) > 10 and potential_title not in [
                    "用户登录",
                    "首页",
                    "通知公告",
                    "清华大学学生职业发展指导中心",
                ]:
                    result["title"] = potential_title
                    break

        # Extract content - try multiple selectors
        # First try: class="content teacher"
        content_div = soup.find("div", class_="content teacher")
        if content_div:
            result["content"] = self._clean_html(content_div)
            result["plain_text"] = self._extract_text(content_div)
        else:
            # Second try: td.td4 or similar
            content_td = soup.find("td", class_=lambda x: x and "td4" in x.split())
            if content_td:
                result["content"] = self._clean_html(content_td)
                result["plain_text"] = self._extract_text(content_td)
            else:
                # Fallback: try to find the main content area
                # Look for table cells with substantial content
                for td in soup.find_all("td", class_=True):
                    text = td.get_text(strip=True)
                    # Look for cells with substantial content (more than 100 chars)
                    if len(text) > 100:
                        result["content"] = self._clean_html(td)
                        result["plain_text"] = text
                        break

        # For career pages, department and time might not be available
        result["department"] = "学生职业发展指导中心"
        result["publish_time"] = ""

        return result
