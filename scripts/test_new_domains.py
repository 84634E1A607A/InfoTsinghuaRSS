#!/usr/bin/env python3
"""Test new domains with full content fetching."""

import logging
from scraper import InfoTsinghuaScraper

logging.basicConfig(level=logging.WARNING)


def test_new_domains() -> None:
    """Test scraping from new domains with full content."""
    print("="*70)
    print("Testing New Domains with Full Content Fetching")
    print("="*70)

    with InfoTsinghuaScraper() as scraper:
        # Fetch first page to get items
        items = scraper.fetch_list(page=1, page_size=30)

        # Find items from new domains
        new_domains = {}

        for item in items:
            url = f"{scraper.BASE_URL}{item.get('url', '')}"

            # Fetch detail to see where it redirects
            try:
                detail_url = f"{scraper.BASE_URL}/f/info/xxfb_fg/xnzx/template/detail?xxid={item['xxid']}"
                headers = {"Referer": scraper.LIST_URL}
                scraper._rate_limit()
                response = scraper._session.get(detail_url, headers=headers, allow_redirects=True, timeout=10)
                final_url = response.url
                domain = final_url.split("/")[2]

                if domain not in new_domains:
                    # Try to fetch full content
                    scraper._rate_limit()
                    full_detail = scraper.fetch_detail(item["xxid"])

                    content_len = len(full_detail.get("content", ""))
                    has_title = bool(full_detail.get("title"))

                    new_domains[domain] = {
                        "title": item["bt"][:50],
                        "content_len": content_len,
                        "has_title": has_title,
                        "url": final_url,
                    }

                    print(f"\n{domain}:")
                    print(f"  Title: {item['bt'][:50]}...")
                    print(f"  URL: {final_url}")
                    print(f"  Title extracted: {'✓' if has_title else '✗'}")
                    print(f"  Content length: {content_len} chars")

                    if content_len == 0 and not has_title:
                        print(f"  ⚠ WARNING: No content extracted!")

            except Exception as e:
                print(f"\nError testing {url}: {e}")

    print("\n" + "="*70)
    print(f"Found {len(new_domains)} unique domains")
    print("="*70)


if __name__ == "__main__":
    test_new_domains()
