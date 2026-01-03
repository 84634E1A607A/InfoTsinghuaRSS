#!/usr/bin/env python3
"""Check samples from new domains to see if they need dedicated parsers."""

from database import get_recent_articles
from parsers import get_parser


def check_domain_samples() -> None:
    """Check article samples from different domains."""
    articles = get_recent_articles(limit=100)

    # Group by domain
    from collections import defaultdict
    by_domain = defaultdict(list)

    for article in articles:
        url = article["url"]
        domain = url.split("/")[2] if "/" in url else "unknown"
        by_domain[domain].append(article)

    print("="*70)
    print("Domain Analysis")
    print("="*70)

    for domain, articles_list in sorted(by_domain.items()):
        print(f"\n{domain} ({len(articles_list)} articles)")

        # Check first article
        if articles_list:
            article = articles_list[0]
            url = article["url"]
            content_len = len(article.get("content", ""))

            # Test parser detection
            # We need to fetch the HTML to test parser detection
            # For now, just show content stats

            print(f"  Sample: {article['title'][:50]}...")
            print(f"  Content length: {content_len} chars")

            if content_len > 100:
                print(f"  ✓ Has content")
            else:
                print(f"  ✗ Missing or short content")


if __name__ == "__main__":
    check_domain_samples()
