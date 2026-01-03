#!/usr/bin/env python3
"""Analyze myhome.tsinghua.edu.cn page structure."""

import asyncio
from playwright.async_api import async_playwright


async def analyze_myhome() -> None:
    """Analyze myhome page structure."""
    url = "http://myhome.tsinghua.edu.cn/Netweb_List/News_notice_Detail.aspx?code=5502"

    print(f"Analyzing: {url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Track API calls
        api_calls = []

        async def log_response(response):
            if response.request.resource_type in ["xhr", "fetch"]:
                try:
                    body = await response.text()
                    if response.status == 200 and len(body) < 5000:
                        api_calls.append({
                            "url": response.url,
                            "body": body,
                        })
                        print(f"[API] {response.url}")
                        print(f"      {body[:200]}...")
                except:
                    pass

        page.on("response", log_response)

        # Navigate
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(2)

        # Check common content selectors
        selectors = [
            "#content",
            ".content",
            "#main",
            ".main",
            ".detail-content",
            ".article-content",
            ".news-content",
            "[class*='content']",
            "[id*='content']",
        ]

        print("\nContent Elements:")
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    for i, elem in enumerate(elements[:3]):
                        text = await elem.inner_text()
                        html = await elem.inner_html()
                        print(f"  {selector}[{i}]: {len(text)} chars text, {len(html)} chars HTML")
                        if len(text) > 50 and len(text) < 500:
                            print(f"      Preview: {text[:100].strip()}...")
            except Exception as e:
                pass

        # Get full HTML
        content = await page.content()

        # Save for analysis
        with open("/tmp/myhome_page.html", "w", encoding="utf-8") as f:
            f.write(content)

        # Look for specific myhome patterns
        import re
        soup_str = content

        # Find all divs with substantial content
        div_matches = re.findall(r'<div[^>]*class="([^"]*)"[^>]*>(.{100,500})</div>', soup_str, re.DOTALL)
        if div_matches:
            print(f"\nFound {len(div_matches)} divs with substantial content")
            for class_name, text in div_matches[:3]:
                clean_text = re.sub(r'<[^>]+>', '', text).strip()
                print(f"  class='{class_name}': {len(clean_text)} chars")
                print(f"    Preview: {clean_text[:80]}...")

        # Save API calls
        import json
        with open("/tmp/myhome_api.json", "w") as f:
            json.dump(api_calls, f, indent=2)

        print(f"\nSaved HTML to /tmp/myhome_page.html")
        print(f"Saved {len(api_calls)} API calls to /tmp/myhome_api.json")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(analyze_myhome())
