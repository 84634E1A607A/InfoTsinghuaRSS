#!/usr/bin/env python3
"""Explore info.tsinghua.edu.cn to understand its structure."""

import asyncio
import json
from playwright.async_api import async_playwright


async def explore_site():
    """Navigate and analyze the target website."""
    target_url = "https://info.tsinghua.edu.cn/f/info/xxfb_fg/xnzx/template/more"

    print(f"Launching browser and navigating to {target_url}...")

    async with async_playwright() as p:
        # Launch browser headless
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Capture the main API request
        api_data = None

        def log_request(request):
            """Log all network requests."""
            print(f"[REQUEST] {request.method} {request.url}")

        async def log_response(response):
            """Log all network responses."""
            print(f"[RESPONSE] {response.status} {response.url}")
            if response.request.resource_type in ["xhr", "fetch"]:
                try:
                    body = await response.text()
                    print(f"[RESPONSE BODY] {body[:200]}")
                    # Save the main data endpoint response
                    if "/template/more?" in response.url and "result" in body:
                        nonlocal api_data
                        api_data = json.loads(body)
                        print("\n*** FOUND MAIN DATA API ***")
                except Exception as e:
                    print(f"Error reading response: {e}")

        page.on("request", log_request)
        page.on("response", lambda r: asyncio.create_task(log_response(r)))

        # Navigate to the page
        await page.goto(target_url, wait_until="networkidle")

        # Wait a bit for all XHR requests to complete
        await asyncio.sleep(2)

        # Get page content
        content = await page.content()
        print(f"\nPage title: {await page.title()}")
        print(f"Page URL: {page.url}")

        # Save page content for analysis
        with open("/home/ajax/tmp/info_scrapper_rss/page_content.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("\nSaved page content to page_content.html")

        # Save the API data if we got it
        if api_data:
            with open("/home/ajax/tmp/info_scrapper_rss/api_data.json", "w", encoding="utf-8") as f:
                json.dump(api_data, f, indent=2, ensure_ascii=False)
            print("Saved API data to api_data.json")
            print(f"\nAPI Response structure:")
            print(f"  result: {api_data.get('result')}")
            print(f"  msg: {api_data.get('msg')}")
            if api_data.get('object'):
                obj = api_data['object']
                print(f"  object keys: {list(obj.keys()) if isinstance(obj, dict) else type(obj)}")
                if isinstance(obj, dict) and 'dataList' in obj:
                    print(f"  dataList length: {len(obj['dataList'])}")
                    if obj['dataList']:
                        print(f"  First item keys: {list(obj['dataList'][0].keys())}")

        print("\nTaking screenshot...")
        await page.screenshot(path="/home/ajax/tmp/info_scrapper_rss/screenshot.png", full_page=True)
        print("Screenshot saved to screenshot.png")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(explore_site())
