#!/usr/bin/env python3
"""Test content parsers with sample HTML from explore_output."""

from pathlib import Path

from parsers import get_parser


def test_parser_with_file(index: int, expected_pattern: str) -> None:
    """Test a parser with a sample HTML file.

    Args:
        index: The item index (e.g., 15 for item_015.html)
        expected_pattern: Expected pattern type
    """
    html_file = Path(f"scripts/explore_output/item_{index:03d}.html")

    if not html_file.exists():
        print(f"✗ Item {index:03d}: File not found")
        return

    html = html_file.read_text(encoding="utf-8")

    # For testing, we need a URL - construct a dummy one based on expected pattern
    test_urls = {
        "internal": "https://info.tsinghua.edu.cn/f/info/xxfb_fg/xnzx/template/detail?xxid=test",
        "external_career_cic_tsinghua_edu_cn": "https://career.cic.tsinghua.edu.cn/xsglxt/f/jyxt/anony/showZwxx?zpxxid=test",
        "external_xxbg_cic_tsinghua_edu_cn": "http://xxbg.cic.tsinghua.edu.cn/oath/detail.jsp?boardid=test",
        "external_ghxt_cic_tsinghua_edu_cn": "http://ghxt.cic.tsinghua.edu.cn/ghxt/detail.jsp?boardid=test",
        "external_hq_tsinghua_edu_cn": "http://hq.tsinghua.edu.cn/front/frontAction.do?ms=gotoThird",
        "external_kyybgxx_cic_tsinghua_edu_cn": "http://kyybgxx.cic.tsinghua.edu.cn/kybg/detail.jsp?boardid=test",
    }

    url = test_urls.get(expected_pattern, "")

    parser = get_parser(url, html)

    if parser is None:
        print(f"✗ Item {index:03d} ({expected_pattern}): No parser found")
        return

    try:
        result = parser.parse(url, html)

        print(f"\n{'='*60}")
        print(f"Item {index:03d} ({expected_pattern})")
        print(f"Parser: {parser.__class__.__name__}")
        print(f"{'='*60}")

        if result["title"]:
            print(f"Title: {result['title'][:80]}...")
        else:
            print("Title: [NOT FOUND]")

        content_len = len(result["plain_text"])
        print(f"Content length: {content_len} chars")

        if content_len > 0:
            preview = result["plain_text"][:200].replace("\n", " ")
            print(f"Preview: {preview}...")
        else:
            print("Preview: [EMPTY]")

        if result["department"]:
            print(f"Department: {result['department']}")

        if result["publish_time"]:
            print(f"Time: {result['publish_time']}")

        # Check if parsing was successful
        success = bool(result["title"] and len(result["plain_text"]) > 50)
        print(f"\n{'✓' if success else '✗'} Parsing {'successful' if success else 'failed'}")

    except Exception as e:
        print(f"✗ Item {index:03d}: Error during parsing: {e}")


def main() -> None:
    """Test parsers with sample files."""
    print("="*60)
    print("Testing Content Parsers")
    print("="*60)

    # Test cases based on our exploration
    test_cases = [
        # (index, expected_pattern)
        (15, "internal"),  # Internal page
        (1, "external_career_cic_tsinghua_edu_cn"),  # Career page
        (14, "external_xxbg_cic_tsinghua_edu_cn"),  # XXBG page
        (25, "external_ghxt_cic_tsinghua_edu_cn"),  # GHXT page
        (26, "external_hq_tsinghua_edu_cn"),  # HQ page
        (29, "external_kyybgxx_cic_tsinghua_edu_cn"),  # KYYBGXX page
    ]

    for index, pattern in test_cases:
        test_parser_with_file(index, pattern)

    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)


if __name__ == "__main__":
    main()
