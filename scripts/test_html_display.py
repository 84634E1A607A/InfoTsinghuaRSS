#!/usr/bin/env python3
"""Test how HTML content appears in different contexts."""

from __future__ import annotations

from html import unescape
from rss import generate_rss

def test_display() -> None:
    """Test how content appears when decoded."""
    rss_xml = generate_rss(limit=10)

    # Find first description with substantial content
    search_start = 0
    for i in range(10):
        desc_start = rss_xml.find('<description>', search_start)
        desc_end = rss_xml.find('</description>', desc_start)
        encoded_desc = rss_xml[desc_start + 13:desc_end]

        # Skip short descriptions (likely just title)
        if len(encoded_desc) < 100:
            search_start = desc_end + 1
            continue

        print(f"Testing item {i+1}...")
        print("\nAs stored in RSS (encoded for XML):")
        print(encoded_desc[:300])
        print("...\n")

        print("As RSS reader would display it (decoded):")
        decoded_desc = unescape(encoded_desc)
        print(decoded_desc[:300])
        print("...\n")

        # Check if it has proper tags
        if '<p>' in decoded_desc:
            print("✓ Content has proper <p> tags when decoded")
        else:
            print("✗ Content missing <p> tags")
        break

if __name__ == "__main__":
    test_display()
