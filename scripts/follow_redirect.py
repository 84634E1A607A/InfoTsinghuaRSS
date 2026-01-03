#!/usr/bin/env python3
"""Follow redirect chain for internal pages."""

import requests

from config import USER_AGENT

test_url = "https://info.tsinghua.edu.cn/f/info/xxfb_fg/xnzx/template/detail?xxid=f98729acfad3ea46c0f80ebf396a0d68"

print(f"Following redirects for: {test_url}\n")

response = requests.get(test_url, headers={"User-Agent": USER_AGENT})
print(f"Final URL: {response.url}")
print(f"Status: {response.status_code}")
print(f"Content length: {len(response.text)}")
print(f"\nFirst 500 chars:")
print(response.text[:500])
