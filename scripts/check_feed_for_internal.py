#!/usr/bin/env python3
"""Check feed for internal pages."""

from scraper import InfoTsinghuaScraper

with InfoTsinghuaScraper() as scraper:
    items = scraper.fetch_items(max_pages=3)
    
    print(f"Checking {len(items)} items from feed...\n")
    
    internal_count = 0
    for item in items[:30]:
        link = item.get('link', '')
        if 'info.tsinghua.edu.cn' in link:
            internal_count += 1
            print(f"[INTERNAL] {item.get('bt', '')[:60]}")
            print(f"           {link}")
            print()
    
    if internal_count == 0:
        print("No internal pages found in first 30 items.")
        print("\nSample item:")
        item = items[0]
        print(f"  Title: {item.get('bt', '')}")
        print(f"  Link: {item.get('link', '')}")
