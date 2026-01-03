#!/usr/bin/env python3
"""Test the full scraping and RSS generation pipeline."""

from database import init_db, get_recent_articles
from rss import generate_rss
from scraper import InfoTsinghuaScraper


def test_full_pipeline(num_items: int = 3) -> None:
    """Test full pipeline: scrape -> database -> RSS.

    Args:
        num_items: Number of items to scrape and test
    """
    print("="*60)
    print("Testing Full Scraping Pipeline")
    print("="*60)

    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    print("   ✓ Database initialized")

    # Scrape articles
    print(f"\n2. Scraping {num_items} articles...")
    with InfoTsinghuaScraper() as scraper:
        items = scraper.fetch_list(page=1, page_size=num_items)
        print(f"   ✓ Fetched {len(items)} items from feed")

        # Insert/update articles with full content
        stats = {"new": 0, "updated": 0, "skipped": 0}
        for i, item in enumerate(items, 1):
            print(f"\n   [{i}/{len(items)}] Processing: {item['bt'][:50]}...")
            try:
                state = scraper.upsert_article(item, fetch_content=True)
                if state.name == "NEW":
                    stats["new"] += 1
                    print(f"      ✓ Inserted new article")
                elif state.name == "UPDATED":
                    stats["updated"] += 1
                    print(f"      ✓ Updated existing article")
                else:
                    stats["skipped"] += 1
                    print(f"      ⊘ Skipped (unchanged)")
            except Exception as e:
                print(f"      ✗ Error: {e}")

    print(f"\n   ✓ Scraping complete: {stats['new']} new, {stats['updated']} updated, {stats['skipped']} skipped")

    # Verify database
    print(f"\n3. Verifying database...")
    articles = get_recent_articles(limit=num_items)
    print(f"   ✓ Retrieved {len(articles)} articles from database")

    for i, article in enumerate(articles[:3], 1):
        content_len = len(article.get("content", ""))
        has_content = "✓" if content_len > 100 else "✗"
        print(f"   [{i}] {has_content} {article['title'][:50]}... ({content_len} chars)")

    # Generate RSS
    print(f"\n4. Generating RSS feed...")
    rss_xml = generate_rss(limit=num_items)
    print(f"   ✓ Generated RSS feed ({len(rss_xml)} chars)")

    # Show RSS preview
    print(f"\n5. RSS Preview (first 500 chars):")
    print("   " + "-"*56)
    for line in rss_xml[:500].split("\n")[:10]:
        print(f"   {line}")
    print("   " + "-"*56)

    print("\n" + "="*60)
    print("Pipeline Test Complete")
    print("="*60)


if __name__ == "__main__":
    test_full_pipeline(num_items=3)
