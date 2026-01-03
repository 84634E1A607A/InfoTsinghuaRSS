#!/usr/bin/env python3
"""Find internal pages that don't redirect."""

import sqlite3
import requests

from config import USER_AGENT

db_path = "info_rss.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get internal pages
cursor.execute("""
    SELECT xxid, url, title
    FROM articles
    WHERE url LIKE '%info.tsinghua.edu.cn%'
    ORDER BY id DESC
    LIMIT 10
""")

rows = cursor.fetchall()
print(f"Checking {len(rows)} internal pages for redirects...\n")

non_redirecting = []

for row in rows:
    xxid, url, title = row
    
    # Follow redirects
    try:
        response = requests.get(url, allow_redirects=False, timeout=5, headers={"User-Agent": USER_AGENT})
        if response.status_code in (301, 302, 303, 307, 308):
            final_url = response.headers.get('Location', 'unknown')
            print(f"[REDIRECT] {title[:50]}")
            print(f"           -> {final_url[:80]}")
        else:
            print(f"[INTERNAL] {title[:50]}")
            print(f"           Status: {response.status_code}")
            non_redirecting.append((xxid, url, title))
    except Exception as e:
        print(f"[ERROR]   {title[:50]}")
        print(f"         {e}")
    print()

conn.close()

if non_redirecting:
    print(f"\nFound {len(non_redirecting)} non-redirecting internal pages!")
else:
    print("\nAll internal pages redirect to external domains.")
