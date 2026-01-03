"""Parser for simple table-based content pages (xxbg, ghxt, hq, etc.)."""

from __future__ import annotations

import re
from typing import Any

from parsers.base import BaseParser


class SimpleTableParser(BaseParser):
    """Parser for simple table-based content pages.

    This parser handles pages from:
    - xxbg.cic.tsinghua.edu.cn (信息办公网)
    - ghxt.cic.tsinghua.edu.cn (工会系统)
    - hq.tsinghua.edu.cn (后勤)
    - kyybgxx.cic.tsinghua.edu.cn (科研公告)
    """

    DOMAINS = [
        "xxbg.cic.tsinghua.edu.cn",
        "ghxt.cic.tsinghua.edu.cn",
        "hq.tsinghua.edu.cn",
        "kyybgxx.cic.tsinghua.edu.cn",
    ]

    @classmethod
    def can_parse(cls, url: str, html: str) -> bool:
        """Check if this is a simple table-based page.

        Args:
            url: The URL to check
            html: The HTML content to check

        Returns:
            True if URL matches one of the known domains
        """
        return any(domain in url for domain in cls.DOMAINS)

    def parse(self, url: str, html: str, session: Any = None, csrf_token: str = "") -> dict[str, Any]:
        """Parse simple table-based page content.

        Args:
            url: The URL being parsed
            html: The HTML content to parse
            session: Optional requests session (unused in simple table parser)
            csrf_token: Optional CSRF token (unused in simple table parser)

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

        # Extract title from the page
        # These pages often have title in h1, h2, or h3 tags
        for tag in ["h1", "h2", "h3"]:
            title_elem = soup.find(tag)
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if len(title_text) > 10:  # Filter out short titles
                    result["title"] = title_text
                    break

        # Fallback: try div with class="td1", "TD1" or td containing such div
        if not result["title"]:
            # First try: find div with class containing "td1"
            divs_td1 = soup.find_all("div", class_=lambda x: x and "td1" in x.lower())
            for div in divs_td1:
                title_text = div.get_text(strip=True)
                if len(title_text) > 10:
                    result["title"] = title_text
                    break

            # Second try: find td with class containing "td1"
            if not result["title"]:
                for td in soup.find_all("td", class_=lambda x: x and "td1" in x.lower()):
                    # Look for span or direct text content
                    span = td.find("span")
                    strong = td.find("strong")

                    if span:
                        title_text = span.get_text(strip=True)
                    elif strong:
                        title_text = strong.get_text(strip=True)
                    else:
                        title_text = td.get_text(strip=True)

                    if len(title_text) > 10:
                        result["title"] = title_text
                        break

        # Another fallback: try to find any div/td with align="center"
        if not result["title"]:
            for elem in soup.find_all(["div", "td"], align=True):
                # Check if it has h1/h2/h3
                for tag in ["h1", "h2", "h3"]:
                    heading = elem.find(tag)
                    if heading:
                        title_text = heading.get_text(strip=True)
                        if len(title_text) > 10:
                            result["title"] = title_text
                            break
                if result["title"]:
                    break

                # Or check for strong tag
                strong = elem.find("strong")
                if strong:
                    title_text = strong.get_text(strip=True)
                    if len(title_text) > 10:  # Filter out short titles
                        result["title"] = title_text
                        break

        # Extract content - try multiple approaches
        content_found = False

        # First try: td.td4
        content_td = soup.find("td", class_=lambda x: x and "td4" in x.split())
        if content_td:
            text = content_td.get_text(strip=True)
            if len(text) > 50:
                result["content"] = self._clean_html(content_td)
                result["plain_text"] = text
                content_found = True

        # Second try: div.content
        if not content_found:
            content_div = soup.find("div", class_=lambda x: x and "content" in x.split())
            if content_div:
                text = content_div.get_text(strip=True)
                if len(text) > 50:
                    result["content"] = self._clean_html(content_div)
                    result["plain_text"] = text
                    content_found = True

        # Third try: find p tags with substantial content
        if not content_found:
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 100:  # Look for substantial paragraphs
                    result["content"] = self._clean_html(p.parent if p.parent else p)
                    result["plain_text"] = text
                    content_found = True
                    break

        # Extract publish time from HTML text
        # Format: 发布时间：2025-12-31 or 2025年12月31日
        html_text = soup.get_text()
        time_match = re.search(r'发布时间[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})', html_text)
        if time_match:
            result["publish_time"] = time_match.group(1)
        else:
            date_match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', html_text)
            if date_match:
                result["publish_time"] = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

        # Department based on domain
        if "xxbg.cic.tsinghua.edu.cn" in url:
            result["department"] = "党政办"
        elif "ghxt.cic.tsinghua.edu.cn" in url:
            result["department"] = "清华大学工会"
        elif "hq.tsinghua.edu.cn" in url:
            result["department"] = "清华大学后勤"
        elif "kyybgxx.cic.tsinghua.edu.cn" in url:
            result["department"] = "科研院"

        return result
