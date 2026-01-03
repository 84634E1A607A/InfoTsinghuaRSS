#!/usr/bin/env python3
"""Check if InternalParser is using API or static HTML."""

import logging
import requests

# Set up logging to see parser messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s %(name)s: %(message)s'
)

from scraper import InfoTsinghuaScraper

# Patch requests.Session.post to log API calls
original_post = requests.Session.post
call_count = [0]

def logging_post(self, url, **kwargs):
    if 'info.tsinghua.edu.cn' in url and 'template/detail' in url:
        call_count[0] += 1
        print(f"\n>>> API CALL #{call_count[0]}")
        print(f"    URL: {url}")
        print(f"    Params: {kwargs.get('params', {})}")
    return original_post(self, url, **kwargs)

requests.Session.post = logging_post

# Test
test_xxid = "f98729acfad3ea46c0f80ebf396a0d68"
print(f"Testing InternalParser with xxid: {test_xxid}\n")

with InfoTsinghuaScraper() as scraper:
    result = scraper.fetch_detail(test_xxid)

print(f"\n=== RESULT ===")
print(f"Title: {result.get('title', '')[:80]}")
print(f"Content length: {len(result.get('content', ''))} chars")
print(f"Department: {result.get('department', '')}")
print(f"\nTotal API calls made: {call_count[0]}")
