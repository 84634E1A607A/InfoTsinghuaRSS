#!/usr/bin/env python3
"""Check what's in the HTML from internal page."""

import requests

from constants import USER_AGENT

test_url = "https://info.tsinghua.edu.cn/b/info/xxfb_fg/xnzx/template/detail?xxid=75e10730b71b736922380228752713a6"

response = requests.get(test_url, headers={"User-Agent": USER_AGENT})
html = response.text

print(f"Status: {response.status_code}")
print(f"HTML length: {len(html)}")
print("\nHTML content:")
print(html)
