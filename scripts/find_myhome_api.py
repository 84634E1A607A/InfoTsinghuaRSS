#!/usr/bin/env python3
"""Find myhome.tsinghua.edu.cn API endpoints."""

import asyncio
import json
from playwright.async_api import async_playwright


async def analyze_myhome() -> None:
    """Analyze myhome.tsinghua.edu.cn to find content loading method."""
    # Get a myhome article ID from the database
    from database import get_recent_articles
    articles = get_recent_articles(limit=100)

    myhome_articles = [a for a in articles if "myhome.tsinghua.edu.cn" in a.get("url", "")]

    if not myhome_articles:
        print("No myhome articles found in recent 100")
        return

    article = myhome_articles[0]
    url = article["url"]

    print(f"Analyzing myhome article: {article['title'][:50]}")
    print(f"URL: {url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        api_calls = []

        async def log_response(response):
            """Log API responses."""
            if response.request.resource_type in ["xhr", "fetch"]:
                try:
                    api_url = response.url
                    status = response.status

                    # Log API calls
                    if status == 200:
                        try:
                            body = await response.text()
                            if len(body) < 10000:
                                api_calls.append({
                                    "url": api_url,
                                    "status": status,
                                    "body": body[:2000],
                                })
                                print(f"[API] {status} {api_url}")
                                print(f"      Body preview: {body[:150]}...")
                        except:
                            pass

                except Exception:
                    pass

        page.on("response", log_response)

        # Navigate and wait
        await page.goto(url, wait_until="networkidle", timeout=15000)
        await asyncio.sleep(2)

        # Get content
        content = await page.content()

        # Look for content in common containers
        selectors = [
            "#content",
            ".content",
            ".article-content",
            ".detail-content",
            "article",
            "main",
        ]

        print(f"\nChecking for content containers:")
        for selector in selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    html_len = len(await elem.inner_html())
                    print(f"  {selector}: ✓ ({len(text)} chars text, {html_len} chars HTML)")
            except:
                pass

        # Save full HTML
        with open("/tmp/myhome_page.html", "w") as f:
            f.write(content)

        # Save API calls
        with open("/tmp/myhome_api_calls.json", "w") as f:
            json.dump(api_calls, f, indent=2)

        print(f"\nSaved HTML to /tmp/myhome_page.html")
        print(f"Saved {len(api_calls)} API calls to /tmp/myhome_api_calls.json")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(analyze_myhome())
