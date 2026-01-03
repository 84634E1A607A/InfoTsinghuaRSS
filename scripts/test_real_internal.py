#!/usr/bin/env python3
"""Test InternalParser with real internal URL."""

import logging
from scraper import InfoTsinghuaScraper

logging.basicConfig(level=logging.WARNING)

# Test URL from database
test_xxid = "f98729acfad3ea46c0f80ebf396a0d68"
test_url = "https://info.tsinghua.edu.cn/f/info/xxfb_fg/xnzx/template/detail?xxid=f98729acfad3ea46c0f80ebf396a0d68"

print(f"Testing with real internal URL: {test_url}\n")

# Create scraper and fetch
with InfoTsinghuaScraper() as scraper:
    result = scraper.fetch_detail(test_xxid)

print("\nFetch result:")
print(f"  Title: {result.get('title', '')[:100] if result.get('title') else '(empty)'}")
print(f"  Content length: {len(result.get('content', ''))} chars")
print(f"  Plain text length: {len(result.get('plain_text', ''))} chars")
print(f"  Department: {result.get('department', '')}")
print(f"  Publish time: {result.get('publish_time', '')}")
print()
if result.get('content'):
    print(f"Content preview (first 500 chars):")
    print(result['content'][:500])
else:
    print("(No content found)")
