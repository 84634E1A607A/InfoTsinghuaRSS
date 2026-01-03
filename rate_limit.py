"""In-memory rate limiting for RSS feed endpoint."""

from __future__ import annotations

import time
from collections import defaultdict

# In-memory rate limit tracking: user_id -> [(window_start, count)]
_rate_limit_store: dict[int, dict[str, tuple[float, int]]] = defaultdict(
    lambda: {"second": (0.0, 0), "hour": (0.0, 0)}
)


def check_rate_limit(user_id: int, window_seconds: int, max_requests: int) -> tuple[bool, int]:
    """Check if user is within rate limit (in-memory).

    Args:
        user_id: User database ID
        window_seconds: Time window in seconds (1 or 3600)
        max_requests: Maximum requests allowed in window

    Returns:
        Tuple of (allowed, remaining_requests)
    """
    now = time.time()
    key = "second" if window_seconds == 1 else "hour"
    window_start, count = _rate_limit_store[user_id][key]

    if now - window_start >= window_seconds:
        _rate_limit_store[user_id][key] = (now, 1)
        return True, max_requests - 1

    if count >= max_requests:
        return False, 0

    _rate_limit_store[user_id][key] = (window_start, count + 1)
    return True, max_requests - count - 1
