"""Base parser interface for content extraction."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from bs4 import BeautifulSoup, Tag


class BaseParser(ABC):
    """Base class for content parsers."""

    @classmethod
    @abstractmethod
    def can_parse(cls, url: str, html: str) -> bool:
        """Check if this parser can handle the given URL and HTML.

        Args:
            url: The URL to check
            html: The HTML content to check

        Returns:
            True if this parser can handle the content
        """
        pass

    @abstractmethod
    def parse(self, url: str, html: str, session: Any = None, csrf_token: str = "") -> dict[str, Any]:
        """Parse content from the given URL and HTML.

        Args:
            url: The URL being parsed
            html: The HTML content to parse
            session: Optional requests session with cookies
            csrf_token: Optional CSRF token for API requests

        Returns:
            Dictionary with keys:
                - title: Article title
                - content: HTML content
                - plain_text: Plain text content
                - department: Publishing department (if available)
                - publish_time: Publish time string (if available)
        """
        pass

    def _make_soup(self, html: str) -> BeautifulSoup:
        """Create BeautifulSoup object from HTML.

        Args:
            html: HTML string

        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, "html.parser")

    def _clean_html(self, element: Tag) -> str:
        """Clean HTML element by removing scripts and styles.

        Args:
            element: BeautifulSoup Tag element

        Returns:
            Cleaned HTML string
        """
        # Remove script and style tags
        for script in element(["script", "style"]):
            script.decompose()

        return str(element)

    def _extract_text(self, element: Tag) -> str:
        """Extract and clean text from HTML element.

        Args:
            element: BeautifulSoup Tag element

        Returns:
            Cleaned text string
        """
        # Get text and clean up whitespace
        text = element.get_text(separator=' ', strip=True)

        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()
