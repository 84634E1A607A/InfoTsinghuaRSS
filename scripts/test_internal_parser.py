#!/usr/bin/env python3
"""Test script for internal parser with specific URL."""

from __future__ import annotations

import logging
import sys

from scraper import InfoTsinghuaScraper

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(name)s - %(message)s"
)

def test_internal_parser() -> None:
    """Test the internal parser with a specific URL."""
    test_url = "https://info.tsinghua.edu.cn/f/info/xxfb_fg/xnzx/template/detail?xxid=75e10730b71b736922380228752713a6"

    print("=" * 80)
    print(f"Testing Internal Parser")
    print("=" * 80)
    print(f"URL: {test_url}")
    print()

    with InfoTsinghuaScraper() as scraper:
        # Extract xxid from URL
        xxid = test_url.split("xxid=")[1]
        print(f"XXID: {xxid}")
        print()

        # Check cookies and CSRF token
        print(f"Session cookies: {len(scraper._session.cookies)}")
        for cookie in scraper._session.cookies:
            print(f"  - {cookie.name}: {cookie.value[:20]}...")
        print()
        print(f"CSRF token: {scraper._csrf_token[:20]}...")
        print()

        # Fetch detail
        print("Fetching detail page...")
        detail = scraper.fetch_detail(xxid)

        print()
        print("=" * 80)
        print("RESULT")
        print("=" * 80)
        print(f"Title: {detail['title']}")
        print(f"Department: {detail['department']}")
        print(f"Publish Time: {detail['publish_time']}")
        print(f"Content length: {len(detail['content'])} chars")
        print(f"Plain text length: {len(detail.get('plain_text', ''))} chars")

        # Debug: show raw detail dict
        print("\nDEBUG - Raw detail dict:")
        for key, value in detail.items():
            if key == 'content' and value:
                print(f"  {key}: {len(value)} chars (first 200): {value[:200]}")
            else:
                print(f"  {key}: {value}")
        print()

        # Show first 200 chars of content
        if detail['content']:
            print("Content preview (first 200 chars):")
            print(detail['content'][:200])
            print()

if __name__ == "__main__":
    test_internal_parser()
