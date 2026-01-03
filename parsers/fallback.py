"""Fallback parser for unknown page patterns."""

from __future__ import annotations

import logging
from typing import Any

from parsers.base import BaseParser

logger = logging.getLogger(__name__)


class FallbackParser(BaseParser):
    """Fallback parser for pages that don't match any specific pattern.

    This parser attempts basic content extraction and logs warnings for
    manual review of new patterns.
    """

    @classmethod
    def can_parse(cls, url: str, html: str) -> bool:
        """This parser can handle any URL (fallback).

        Args:
            url: The URL to check
            html: The HTML content to check

        Returns:
            Always returns True (as fallback)
        """
        return True

    def parse(
        self, url: str, html: str, session: Any = None, csrf_token: str = ""
    ) -> dict[str, Any]:
        """Attempt basic content extraction.

        Args:
            url: The URL being parsed
            html: The HTML content to parse
            session: Optional requests session (unused in fallback)
            csrf_token: Optional CSRF token (unused in fallback)

        Returns:
            Dictionary with basic extracted content
        """
        logger.warning(f"Using fallback parser for unknown pattern: {url}")

        result: dict[str, Any] = {
            "title": "",
            "content": "",
            "plain_text": "",
            "department": "",
            "publish_time": "",
        }

        soup = self._make_soup(html)

        # Try to find title in various common tags
        for tag in ["h1", "h2", "h3", "title"]:
            title_elem = soup.find(tag)
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if len(title_text) > 10:
                    result["title"] = title_text
                    logger.info(f"Fallback parser found title in {tag} tag")
                    break

        # Try to find content in common containers
        content_selectors = [
            "div.content",
            "div.article",
            "div.post",
            "div.main",
            "article",
            "main",
        ]

        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                text = content_elem.get_text(strip=True)
                if len(text) > 100:
                    result["content"] = self._clean_html(content_elem)
                    result["plain_text"] = text
                    logger.info(f"Fallback parser found content in {selector}")
                    break

        # If no specific container found, try to get the body content
        if not result["content"]:
            body = soup.find("body")
            if body:
                # Remove script and style elements
                for script in body(["script", "style", "nav", "header", "footer"]):
                    script.decompose()

                result["content"] = self._clean_html(body)
                result["plain_text"] = self._extract_text(body)
                logger.info("Fallback parser using body content")

        # Log extraction results
        logger.warning(
            f"Fallback parser extraction results for {url}:\n"
            f"  Title: {'✓' if result['title'] else '✗'} ({len(result['title'])} chars)\n"
            f"  Content: {'✓' if result['content'] else '✗'} ({len(result['plain_text'])} chars)"
        )

        return result
