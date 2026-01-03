Your overall goal is to create an RSS feeder to get updates from info.tsinghua.edu.cn and generate RSS feed.
Write your code clean, with type annotations and inline docs. Don't generate doc files.
You have git repository initialized, create commit and manage gitignore as needed.

## Current State
- Working scraper at `scraper.py` (uses only `requests` library, no BeautifulSoup or Playwright)
- Working venv at `.venv` (dependencies: requests)
- Scraper extracts data via API at `https://info.tsinghua.edu.cn/b/info/xxfb_fg/xnzx/template/more`
- Requires CSRF token from meta tag and session cookies
