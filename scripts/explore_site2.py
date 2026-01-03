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

        # Capture all API requests
        api_responses = []

        def log_request(request):
            """Log all network requests."""
            if request.resource_type in ["xhr", "fetch"]:
                print(f"[REQUEST] {request.method} {request.url}")

        async def log_response(response):
            """Log all network responses."""
            if response.request.resource_type in ["xhr", "fetch"]:
                try:
                    body = await response.text()
                    print(f"[RESPONSE] {response.status} {response.url[:100]}")
                    # Save all API responses
                    if body and len(body) < 10000:  # Reasonable size
                        try:
                            data = json.loads(body)
                            api_responses.append({
                                "url": response.url,
                                "status": response.status,
                                "data": data
                            })
                            print(f"  -> JSON captured: {data.get('result', 'N/A')}")
                        except:
                            print(f"  -> Not JSON")
                except Exception as e:
                    print(f"  -> Error: {e}")

        page.on("request", log_request)
        page.on("response", lambda r: asyncio.create_task(log_response(r)))

        # Navigate to the page
        await page.goto(target_url, wait_until="networkidle")

        # Wait for all XHR requests to complete
        await asyncio.sleep(3)

        # Save all API responses
        with open("/home/ajax/tmp/info_scrapper_rss/all_api_responses.json", "w", encoding="utf-8") as f:
            json.dump(api_responses, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(api_responses)} API responses to all_api_responses.json")

        # Print summary of all responses
        print("\n" + "="*80)
        print("API Response Summary:")
        for i, resp in enumerate(api_responses):
            print(f"\n{i+1}. {resp['url'][:80]}")
            print(f"   Status: {resp['status']}")
            if isinstance(resp['data'], dict):
                print(f"   Result: {resp['data'].get('result', 'N/A')}")
                print(f"   Msg: {resp['data'].get('msg', 'N/A')}")
                if 'object' in resp['data'] and isinstance(resp['data']['object'], dict):
                    obj_keys = list(resp['data']['object'].keys())
                    print(f"   Object keys: {obj_keys}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(explore_site())
