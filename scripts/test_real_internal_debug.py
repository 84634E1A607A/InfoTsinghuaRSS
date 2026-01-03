#!/usr/bin/env python3
"""Test InternalParser with debug output."""

import logging
from scraper import InfoTsinghuaScraper

logging.basicConfig(level=logging.DEBUG)

# Test URL from database
test_xxid = "f98729acfad3ea46c0f80ebf396a0d68"

print(f"Testing with xxid: {test_xxid}\n")

# Create scraper and fetch
with InfoTsinghuaScraper() as scraper:
    result = scraper.fetch_detail(test_xxid)

print("\n=== FINAL RESULT ===")
print(f"Title: {result.get('title', '')[:80]}")
print(f"Content length: {len(result.get('content', ''))} chars")
print(f"Department: {result.get('department', '')}")
