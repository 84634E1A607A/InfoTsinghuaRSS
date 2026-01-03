"""Content parsers for different article patterns."""

from __future__ import annotations

from parsers.career_cic import CareerCicParser
from parsers.internal import InternalParser
from parsers.simple_table import SimpleTableParser
from parsers.base import BaseParser

__all__ = [
    "BaseParser",
    "InternalParser",
    "CareerCicParser",
    "SimpleTableParser",
]

# Parser registry for automatic selection
PARSERS: list[type[BaseParser]] = [
    InternalParser,
    CareerCicParser,
    SimpleTableParser,
]


def get_parser(url: str, html: str) -> BaseParser | None:
    """Get appropriate parser for the given URL and HTML content.

    Args:
        url: The URL to parse
        html: The HTML content to parse

    Returns:
        Appropriate parser instance or None if no parser matches
    """
    for parser_class in PARSERS:
        if parser_class.can_parse(url, html):
            return parser_class()
    return None
