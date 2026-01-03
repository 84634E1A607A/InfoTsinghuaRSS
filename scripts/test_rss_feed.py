#!/usr/bin/env python3
"""Test RSS feed generation with style stripping."""

from __future__ import annotations

from rss import generate_rss

def test_rss_generation() -> None:
    """Generate RSS feed and check for styles."""
    print("Generating RSS feed...")
    rss_xml = generate_rss(limit=5)

    # Check for style attributes
    style_attr_count = rss_xml.count('style=')
    style_tag_count = rss_xml.count('<style')

    print(f"RSS feed generated: {len(rss_xml)} characters")
    print(f"Style attributes found: {style_attr_count}")
    print(f"Style tags found: {style_tag_count}")

    # Show first item as sample
    print("\n" + "=" * 80)
    print("SAMPLE RSS ITEM")
    print("=" * 80)

    # Find first item
    item_start = rss_xml.find('<item>')
    if item_start != -1:
        item_end = rss_xml.find('</item>', item_start) + 7
        sample_item = rss_xml[item_start:item_end]
        print(sample_item[:1000])
        print("...")

    print("\n" + "=" * 80)

    if style_attr_count > 0 or style_tag_count > 0:
        print("✗ WARNING: Styles still present in RSS feed!")
    else:
        print("✓ No styles found in RSS feed!")

if __name__ == "__main__":
    test_rss_generation()
