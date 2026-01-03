#!/usr/bin/env python3
"""Explore feed content patterns using playwright to understand different article types."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright

from scraper import InfoTsinghuaScraper


class ContentPatternAnalyzer:
    """Analyze content patterns from feed items."""

    def __init__(self, output_dir: Path = Path("scripts/explore_output")) -> None:
        """Initialize analyzer.

        Args:
            output_dir: Directory to save exploration results
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.patterns: dict[str, list[dict[str, str]]] = {}

    async def analyze_item(self, page, item: dict[str, str], index: int) -> dict[str, str] | None:
        """Analyze a single feed item to determine its content pattern.

        Args:
            page: Playwright page instance
            item: Feed item dict with title, url, etc.
            index: Item index for naming

        Returns:
            Pattern info dict or None if analysis failed
        """
        url = item["url"]
        print(f"\n[{index}] Analyzing: {item['title'][:60]}...")
        print(f"    URL: {url}")

        try:
            # Navigate to the page
            response = await page.goto(url, wait_until="networkidle", timeout=15000)

            if response is None:
                print(f"    ✗ Failed to load page")
                return None

            # Check for redirects
            final_url = page.url
            is_redirected = final_url != url

            if is_redirected:
                print(f"    ⚠ Redirected to: {final_url}")
                domain = final_url.split("/")[2]
                pattern_type = f"external_{domain.replace('.', '_')}"
            else:
                print(f"    ✓ Same domain page")
                pattern_type = "internal"

            # Get page content
            content = await page.content()

            # Save HTML for analysis
            html_file = self.output_dir / f"item_{index:03d}.html"
            html_file.write_text(content, encoding="utf-8")

            # Take screenshot
            screenshot_file = self.output_dir / f"item_{index:03d}.png"
            await page.screenshot(path=str(screenshot_file), full_page=True)

            # Analyze content structure
            analysis = {
                "index": index,
                "title": item["title"],
                "original_url": url,
                "final_url": final_url,
                "is_redirected": is_redirected,
                "pattern_type": pattern_type,
                "status_code": response.status,
                "html_file": str(html_file),
                "screenshot": str(screenshot_file),
            }

            # Extract key elements based on pattern
            if pattern_type == "internal":
                analysis.update(await self._analyze_internal(page, content))
            else:
                analysis.update(await self._analyze_external(page, content, final_url))

            print(f"    Pattern: {pattern_type}")
            return analysis

        except Exception as e:
            print(f"    ✗ Error: {e}")
            return None

    async def _analyze_internal(self, page, content: str) -> dict[str, str]:
        """Analyze internal (same-domain) page content.

        Args:
            page: Playwright page instance
            content: HTML content

        Returns:
            Analysis dict
        """
        analysis: dict[str, str] = {}

        # Check for common content containers
        selectors = [
            "detail-content",
            "content-body",
            "article-content",
            "post-content",
            "main-content",
            "article-body",
            "entry-content",
        ]

        found_selectors = []
        for selector in selectors:
            if await page.query_selector(f".{selector}"):
                found_selectors.append(selector)

        analysis["content_selectors"] = ", ".join(found_selectors) if found_selectors else "none_found"

        # Check if content is complete or needs fetching
        content_div = await page.query_selector(".detail-content, .content-body")
        if content_div:
            text_content = await content_div.inner_text()
            analysis["has_content"] = "yes"
            analysis["content_length"] = str(len(text_content))
            analysis["content_preview"] = text_content[:200]
        else:
            analysis["has_content"] = "no"

        return analysis

    async def _analyze_external(self, page, content: str, url: str) -> dict[str, str]:
        """Analyze external (redirected) page content.

        Args:
            page: Playwright page instance
            content: HTML content
            url: Final URL

        Returns:
            Analysis dict
        """
        analysis: dict[str, str] = {}
        analysis["domain"] = url.split("/")[2]

        # Detect common external platforms
        platform_selectors = {
            "mp.weixin.qq.com": ".rich_media_content",
            "weixin.qq.com": ".rich_media_content",
            "news.tsinghua.edu.cn": ".article-content, .content",
            "www.tsinghua.edu.cn": ".content, .article",
        }

        found_platform = None
        for platform, selector in platform_selectors.items():
            if platform in url:
                found_platform = platform
                if await page.query_selector(selector):
                    analysis["content_selector"] = selector
                    content_div = await page.query_selector(selector)
                    if content_div:
                        text_content = await content_div.inner_text()
                        analysis["content_length"] = str(len(text_content))
                        analysis["content_preview"] = text_content[:200]
                break

        if found_platform:
            analysis["platform"] = found_platform
        else:
            analysis["platform"] = "unknown"

        return analysis

    def save_results(self) -> None:
        """Save analysis results to JSON."""
        results_file = self.output_dir / "pattern_analysis.json"

        # Convert to list format
        all_patterns = []
        for pattern_type, items in self.patterns.items():
            for item in items:
                item["pattern_category"] = pattern_type
                all_patterns.append(item)

        results_file.write_text(
            json.dumps(all_patterns, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"\n✓ Results saved to {results_file}")

        # Generate summary
        summary = {
            "total_items": sum(len(items) for items in self.patterns.values()),
            "patterns": {
                pattern_type: len(items)
                for pattern_type, items in self.patterns.items()
            }
        }

        summary_file = self.output_dir / "summary.json"
        summary_file.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"✓ Summary saved to {summary_file}")
        print(f"\nSummary:")
        for pattern, count in summary["patterns"].items():
            print(f"  {pattern}: {count}")


async def main() -> None:
    """Main exploration function."""
    print("=== Feed Content Pattern Explorer ===\n")

    # First, fetch list of items using the scraper
    print("Fetching feed items...")
    with InfoTsinghuaScraper() as scraper:
        items = scraper.fetch_list(page=1, page_size=30)

    print(f"Fetched {len(items)} items\n")

    # Prepare full URLs
    base_url = "https://info.tsinghua.edu.cn"
    feed_items = [
        {
            "title": item.get("bt", ""),
            "url": urljoin(base_url, item.get("url", "")),
            "department": item.get("dwmc", ""),
            "category": item.get("lmmc", ""),
        }
        for item in items
    ]

    # Initialize analyzer
    analyzer = ContentPatternAnalyzer()

    # Launch browser
    print("Launching browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Analyze each item
        for i, item in enumerate(feed_items, 1):
            result = await analyzer.analyze_item(page, item, i)

            if result:
                pattern_type = result["pattern_type"]
                if pattern_type not in analyzer.patterns:
                    analyzer.patterns[pattern_type] = []
                analyzer.patterns[pattern_type].append(result)

            # Be nice to the server
            await asyncio.sleep(1)

        await browser.close()

    # Save results
    analyzer.save_results()

    print("\n=== Exploration Complete ===")
    print(f"Check {analyzer.output_dir} for detailed results")


if __name__ == "__main__":
    asyncio.run(main())
