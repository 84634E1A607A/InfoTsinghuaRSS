#!/usr/bin/env python3
"""Test the full scraping pipeline with internal pages."""

from __future__ import annotations

import logging

from scraper import InfoTsinghuaScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(name)s - %(message)s"
)

def test_full_pipeline() -> None:
    """Test scraping articles with internal pages."""
    print("=" * 80)
    print("Testing Full Pipeline with Internal Pages")
    print("=" * 80)

    with InfoTsinghuaScraper() as scraper:
        # Fetch first page
        items = scraper.fetch_list(page=1, page_size=10)
        print(f"\nFetched {len(items)} items from list")

        # Count internal pages
        internal_items = []
        for item in items:
            url = f"{scraper.BASE_URL}{item['url']}"
            if "info.tsinghua.edu.cn" in url and "/template/detail" in url:
                internal_items.append(item)

        print(f"Found {len(internal_items)} internal pages")

        # Test first 3 internal items
        for i, item in enumerate(internal_items[:3], 1):
            xxid = item['xxid']
            url = f"{scraper.BASE_URL}{item['url']}"

            print(f"\n[{i}] Testing {xxid}")
            print(f"    URL: {url}")

            try:
                detail = scraper.fetch_detail(xxid)
                print(f"    ✓ Title: {detail['title'][:50]}...")
                print(f"    ✓ Content: {len(detail['content'])} chars")
                print(f"    ✓ Department: {detail['department'] or '(empty)'}")
                print(f"    ✓ Time: {detail['publish_time'] or '(empty)'}")
            except Exception as e:
                print(f"    ✗ Error: {e}")

        print("\n" + "=" * 80)
        print("Test complete!")
        print("=" * 80)

if __name__ == "__main__":
    test_full_pipeline()
