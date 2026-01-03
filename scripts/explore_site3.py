#!/usr/bin/env python3
"""Explore info.tsinghua.edu.cn with lmid=all parameter."""

import asyncio
import json
from playwright.async_api import async_playwright


async def explore_site():
    """Navigate and analyze the target website with correct parameter."""
    target_url = "https://info.tsinghua.edu.cn/f/info/xxfb_fg/xnzx/template/more?lmid=all"

    print(f"Launching browser and navigating to {target_url}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Capture API data
        api_data = None

        async def log_response(response):
            """Log all network responses."""
            if response.request.resource_type in ["xhr", "fetch"]:
                try:
                    body = await response.text()
                    if "/template/more?" in response.url:
                        nonlocal api_data
                        api_data = json.loads(body)
                        print(f"\n*** FOUND DATA API: {api_data.get('result')} ***")
                except Exception as e:
                    pass

        page.on("response", lambda r: asyncio.create_task(log_response(r)))

        # Navigate to the page
        await page.goto(target_url, wait_until="networkidle")
        await asyncio.sleep(2)

        # Save the API data
        if api_data:
            with open("/home/ajax/tmp/info_scrapper_rss/api_data_lmid_all.json", "w", encoding="utf-8") as f:
                json.dump(api_data, f, indent=2, ensure_ascii=False)
            print("Saved API data to api_data_lmid_all.json")

            print(f"\nAPI Response structure:")
            print(f"  result: {api_data.get('result')}")
            print(f"  msg: {api_data.get('msg')}")
            if api_data.get('object'):
                obj = api_data['object']
                print(f"  object type: {type(obj)}")
                print(f"  object keys: {list(obj.keys()) if isinstance(obj, dict) else 'N/A'}")
                if isinstance(obj, dict) and 'dataList' in obj:
                    print(f"  dataList length: {len(obj['dataList'])}")
                    if obj['dataList']:
                        print(f"\n  First item sample:")
                        first_item = obj['dataList'][0]
                        for key, value in list(first_item.items())[:10]:
                            print(f"    {key}: {value}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(explore_site())
