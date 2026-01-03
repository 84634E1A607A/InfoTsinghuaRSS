#!/usr/bin/env python3
"""Test the style stripping functionality."""

from __future__ import annotations

from rss import strip_styles_from_html

def test_style_strip() -> None:
    """Test stripping styles from HTML."""
    test_html = """
    <div style="color: red; font-size: 14px;">
        <p style="margin: 10px;">Some text</p>
        <style>
            .class { color: blue; }
        </style>
        <span class="test">More text</span>
    </div>
    """

    print("Original HTML:")
    print(test_html)
    print("\n" + "=" * 80 + "\n")

    cleaned = strip_styles_from_html(test_html)

    print("Cleaned HTML:")
    print(cleaned)
    print("\n" + "=" * 80 + "\n")

    # Check that styles are removed
    assert 'style=' not in cleaned, "Style attributes should be removed"
    assert '<style>' not in cleaned, "Style tags should be removed"
    assert 'Some text' in cleaned, "Content should be preserved"

    print("✓ All tests passed!")

if __name__ == "__main__":
    test_style_strip()
