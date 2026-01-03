#!/usr/bin/env python3
"""Test InternalParser with API calls."""

import logging
from parsers.internal import InternalParser

logging.basicConfig(level=logging.DEBUG)

# Test URL from the user
test_url = "https://info.tsinghua.edu.cn/b/info/xxfb_fg/xnzx/template/detail?xxid=75e10730b71b736922380228752713a6"

print(f"Testing InternalParser with: {test_url}\n")

# Fetch the HTML
import requests
from constants import USER_AGENT
response = requests.get(test_url, headers={"User-Agent": USER_AGENT})
html = response.text

print(f"Fetched HTML: {len(html)} chars")
print(f"Can parse: {InternalParser.can_parse(test_url, html)}\n")

# Parse it
parser = InternalParser()
result = parser.parse(test_url, html)

print("Parsing result:")
print(f"  Title: {result['title'][:100] if result['title'] else '(empty)'}")
print(f"  Content length: {len(result['content'])} chars")
print(f"  Plain text length: {len(result['plain_text'])} chars")
print(f"  Department: {result['department']}")
print(f"  Publish time: {result['publish_time']}")
print()
print(f"Content preview (first 300 chars):")
print(result['content'][:300] if result['content'] else '(empty)')
