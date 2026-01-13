"""Content parsers for different article patterns."""

from __future__ import annotations

import logging

from parsers.base import BaseParser
from parsers.career_cic import CareerCicParser
from parsers.fallback import FallbackParser
from parsers.internal import InternalParser
from parsers.kybg import KybgParser
from parsers.library import LibraryParser
from parsers.myhome import MyhomeParser
from parsers.simple_table import SimpleTableParser

logger = logging.getLogger(__name__)

__all__ = [
    "BaseParser",
    "InternalParser",
    "CareerCicParser",
    "SimpleTableParser",
    "MyhomeParser",
    "LibraryParser",
    "KybgParser",
    "FallbackParser",
]

# Parser registry for automatic selection (ordered by priority)
PARSERS: list[type[BaseParser]] = [
    InternalParser,
    MyhomeParser,
    KybgParser,
    CareerCicParser,
    LibraryParser,
    SimpleTableParser,
]


def get_parser(url: str, html: str) -> BaseParser:
    """Get appropriate parser for the given URL and HTML content.

    Args:
        url: The URL to parse
        html: The HTML content to parse

    Returns:
        Appropriate parser instance (always returns at least FallbackParser)
    """
    # Try specific parsers first
    for parser_class in PARSERS:
        if parser_class.can_parse(url, html):
            logger.debug(f"Using {parser_class.__name__} for {url}")
            return parser_class()

    # Fallback to catch-all parser
    logger.warning(f"No specific parser found for {url}, using FallbackParser")
    return FallbackParser()
