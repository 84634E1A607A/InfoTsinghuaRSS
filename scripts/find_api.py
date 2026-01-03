#!/usr/bin/env python3
"""Use playwright to find API endpoints for content loading."""

import asyncio
import json
from playwright.async_api import async_playwright


async def find_api_endpoints(url: str) -> None:
    """Find API endpoints that load content.

    Args:
        url: The detail page URL
    """
    print(f"Analyzing: {url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        api_calls = []

        def log_request(request):
            """Log API requests."""
            if request.resource_type in ["xhr", "fetch"]:
                print(f"[REQUEST] {request.method} {request.url}")

        async def log_response(response):
            """Log API responses."""
            if response.request.resource_type in ["xhr", "fetch"]:
                try:
                    url = response.url
                    status = response.status

                    # Only log relevant API calls
                    if any(x in url for x in ["/f/", "/b/", "xxfb", "detail", "template"]):
                        print(f"[RESPONSE] {status} {url}")

                        # Try to get response body for small responses
                        if status == 200:
                            try:
                                body = await response.text()
                                if len(body) < 5000:  # Only log small responses
                                    print(f"[BODY] {body[:200]}...")
                                    api_calls.append({
                                        "url": url,
                                        "status": status,
                                        "body": body[:1000],
                                    })
                            except:
                                pass

                except Exception as e:
                    print(f"Error logging response: {e}")

        page.on("request", log_request)
        page.on("response", lambda r: asyncio.create_task(log_response(r)))

        # Navigate and wait for network to be idle
        await page.goto(url, wait_until="networkidle", timeout=15000)

        # Wait a bit more for any delayed AJAX
        await asyncio.sleep(2)

        # Get final page content
        content = await page.content()

        # Save to file for analysis
        output_file = "/tmp/internal_page_rendered.html"
        with open(output_file, "w") as f:
            f.write(content)

        # Check for xqhtml content
        xqhtml_content = await page.locator("#xqhtml").inner_html()
        print(f"\n✓ Found #xqhtml with {len(xqhtml_content)} chars of content")

        # Save API calls
        with open("/tmp/api_calls.json", "w") as f:
            json.dump(api_calls, f, indent=2)

        print(f"\nSaved rendered HTML to {output_file}")
        print(f"Saved {len(api_calls)} API calls to /tmp/api_calls.json")

        await browser.close()


if __name__ == "__main__":
    url = "https://info.tsinghua.edu.cn/f/info/xxfb_fg/xnzx/template/detail?xxid=75e10730b71b736922380228752713a6"
    asyncio.run(find_api_endpoints(url))
