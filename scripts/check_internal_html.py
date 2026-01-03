#!/usr/bin/env python3
"""Check what HTML was stored for internal pages."""

import sqlite3

db_path = "info_rss.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get internal pages
cursor.execute("""
    SELECT xxid, url, title, length(content)
    FROM articles
    WHERE url LIKE '%info.tsinghua.edu.cn%'
    ORDER BY id DESC
    LIMIT 3
""")

rows = cursor.fetchall()
print(f"Found {len(rows)} internal pages:\n")

for row in rows:
    xxid, url, title, content_len = row
    print(f"xxid: {xxid}")
    print(f"url: {url}")
    print(f"title: {title[:100] if title else '(empty)'}")
    print(f"content_length: {content_len}")
    print()

    # Extract xxid from URL
    import re
    xxid_match = re.search(r'xxid=([a-f0-9]+)', url)
    if xxid_match:
        test_xxid = xxid_match.group(1)
        print(f"xxid from URL: {test_xxid}")

    print("-" * 80)
    print()

conn.close()
