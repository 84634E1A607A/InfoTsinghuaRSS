"""Parser for internal info.tsinghua.edu.cn pages."""

from __future__ import annotations

from typing import Any

from bs4 import Tag

from parsers.base import BaseParser


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

    def parse(self, url: str, html: str) -> dict[str, Any]:
        """Parse internal page content.

        Args:
            url: The URL being parsed
            html: The HTML content to parse

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
