#!/usr/bin/env python3
"""Test parsers with real live data from the scraper."""

from scraper import InfoTsinghuaScraper
from parsers import get_parser


def test_live_items(num_items: int = 5) -> None:
    """Test parsers with live feed items.

    Args:
        num_items: Number of items to test
    """
    print(f"=== Testing Parsers with Live Data ({num_items} items) ===\n")

    with InfoTsinghuaScraper() as scraper:
        # Fetch list of items
        items = scraper.fetch_list(page=1, page_size=num_items)
        print(f"Fetched {len(items)} items from feed\n")

        success_count = 0
        fail_count = 0

        for i, item in enumerate(items, 1):
            xxid = item.get("xxid")
            title = item.get("bt", "")
            url = f"{scraper.BASE_URL}{item.get('url', '')}"

            print(f"[{i}] Testing: {title[:60]}...")
            print(f"    URL: {url}")

            try:
                # Fetch detail page HTML directly
                detail_url = f"{scraper.BASE_URL}/f/info/xxfb_fg/xnzx/template/detail?xxid={xxid}"
                headers = {
                    "Referer": scraper.LIST_URL,
                }
                scraper._rate_limit()
                response = scraper._session.get(detail_url, headers=headers)
                response.raise_for_status()
                html = response.text

                print(f"    ✓ Fetched detail page ({len(html)} chars)")

                # Check for redirects in the response
                final_url = response.url
                if final_url != detail_url:
                    print(f"    ⚠ Redirected to: {final_url}")
                    # Use the final URL for parser selection
                    parser = get_parser(final_url, html)
                else:
                    # Use original URL for parser selection
                    parser = get_parser(detail_url, html)

                if parser is None:
                    print(f"    ✗ No parser found for this URL pattern")
                    print(f"       Final URL: {final_url}")
                    fail_count += 1
                    continue

                # Parse content
                parsed = parser.parse(final_url, html)

                # Check results
                has_title = bool(parsed["title"])
                has_content = len(parsed["plain_text"]) > 50

                if has_title:
                    print(f"    ✓ Title extracted: {parsed['title'][:50]}...")
                else:
                    print(f"    ⚠ Title not found")

                if has_content:
                    print(f"    ✓ Content length: {len(parsed['plain_text'])} chars")
                    print(f"    Preview: {parsed['plain_text'][:100]}...")
                else:
                    print(f"    ⚠ Content too short or empty")

                if parsed["department"]:
                    print(f"    ✓ Department: {parsed['department']}")

                if parsed["publish_time"]:
                    print(f"    ✓ Time: {parsed['publish_time']}")

                # Consider successful if we have title and content
                if has_title and has_content:
                    print(f"    ✓✓ Parsing successful")
                    success_count += 1
                else:
                    print(f"    ⚠ Partial success")
                    success_count += 1  # Still count as partial success

            except Exception as e:
                print(f"    ✗ Error: {e}")
                fail_count += 1

            print()

        print("="*60)
        print(f"Results: {success_count} successful, {fail_count} failed")
        print("="*60)


if __name__ == "__main__":
    test_live_items(num_items=5)
