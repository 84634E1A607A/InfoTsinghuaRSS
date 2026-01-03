#!/usr/bin/env python3
"""Scrape and analyze 600 newest articles to find any missed patterns."""

import logging
from collections import Counter, defaultdict
from datetime import datetime

from database import init_db
from scraper import InfoTsinghuaScraper, ArticleStateEnum

# Configure logging to see parser warnings
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)


def scrape_and_analyze(num_articles: int = 600, page_size: int = 30) -> None:
    """Scrape articles and analyze parsing results.

    Args:
        num_articles: Total number of articles to scrape
        page_size: Number of articles per API page
    """
    print("="*70)
    print(f"Scraping {num_articles} Articles - Pattern Analysis")
    print("="*70)

    # Initialize database
    init_db()

    # Statistics
    stats = {
        "total": 0,
        "new": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
    }

    # Track patterns by domain
    domain_patterns = Counter()
    content_lengths = []
    no_content_count = 0
    short_content_count = 0

    # Track redirects
    redirects = Counter()

    # Error tracking
    errors = []

    # Calculate pages needed
    pages_needed = (num_articles + page_size - 1) // page_size

    print(f"\nFetching {pages_needed} pages ({page_size} items per page)...\n")

    with InfoTsinghuaScraper() as scraper:
        for page in range(1, pages_needed + 1):
            print(f"[Page {page}/{pages_needed}] Fetching...", end="", flush=True)

            try:
                items = scraper.fetch_list(page=page, page_size=page_size)
                if not items:
                    print(" No items")
                    break

                print(f" Got {len(items)} items")

                for i, item in enumerate(items, 1):
                    xxid = item.get("xxid")
                    title = item.get("bt", "")
                    url = f"{scraper.BASE_URL}{item.get('url', '')}"

                    stats["total"] += 1

                    try:
                        # Fetch and parse content
                        detail_url = f"{scraper.BASE_URL}/f/info/xxfb_fg/xnzx/template/detail?xxid={xxid}"
                        headers = {"Referer": scraper.LIST_URL}

                        scraper._rate_limit()
                        response = scraper._session.get(detail_url, headers=headers, allow_redirects=True, timeout=10)
                        response.raise_for_status()

                        # Track redirects
                        final_url = response.url
                        if final_url != detail_url:
                            domain = final_url.split("/")[2]
                            redirects[domain] += 1

                        # Get content length
                        html = response.text
                        content_len = len(html)
                        content_lengths.append(content_len)

                        # Try to upsert (with rate limiting already applied)
                        state = scraper.upsert_article(item, fetch_content=False)  # Skip fetch to avoid double request
                        state_enum = ArticleStateEnum(state)

                        if state_enum == ArticleStateEnum.NEW:
                            stats["new"] += 1
                        elif state_enum == ArticleStateEnum.UPDATED:
                            stats["updated"] += 1
                        else:
                            stats["skipped"] += 1

                        # Progress indicator
                        if stats["total"] % 50 == 0:
                            print(f"  Progress: {stats['total']} articles processed", flush=True)

                    except Exception as e:
                        stats["errors"] += 1
                        error_msg = f"Error processing {xxid}: {str(e)[:100]}"
                        errors.append(error_msg)
                        logger.error(error_msg)

            except Exception as e:
                print(f" ERROR: {e}")
                logger.error(f"Error fetching page {page}: {e}")
                continue

    # Print analysis
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)

    print(f"\nArticle Processing:")
    print(f"  Total processed:  {stats['total']}")
    print(f"  New:             {stats['new']} ({stats['new']/stats['total']*100:.1f}%)" if stats['total'] > 0 else "  New:             0")
    print(f"  Updated:         {stats['updated']} ({stats['updated']/stats['total']*100:.1f}%)" if stats['total'] > 0 else "  Updated:         0")
    print(f"  Skipped:         {stats['skipped']} ({stats['skipped']/stats['total']*100:.1f}%)" if stats['total'] > 0 else "  Skipped:         0")
    print(f"  Errors:          {stats['errors']}")

    if content_lengths:
        print(f"\nContent Statistics:")
        print(f"  Avg page size:   {sum(content_lengths)//len(content_lengths):,} chars")
        print(f"  Min page size:   {min(content_lengths):,} chars")
        print(f"  Max page size:   {max(content_lengths):,} chars")

    if redirects:
        print(f"\nRedirect Destinations (Top 10):")
        for domain, count in redirects.most_common(10):
            print(f"  {domain}: {count}")

    if errors:
        print(f"\nErrors (first 10):")
        for error in errors[:10]:
            print(f"  - {error}")

    print("\n" + "="*70)
    print(f"Scraping complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


if __name__ == "__main__":
    scrape_and_analyze(num_articles=600, page_size=30)
