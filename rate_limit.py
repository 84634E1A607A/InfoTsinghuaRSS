"""In-memory rate limiting for RSS feed endpoint."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class RateLimitTracker:
    """Track rate limit for a single user."""

    second_window_start: float = 0.0
    second_count: int = 0
    hour_window_start: float = 0.0
    hour_count: int = 0


# In-memory storage for rate limiting
# user_id -> RateLimitTracker
_rate_limit_store: dict[int, RateLimitTracker] = defaultdict(RateLimitTracker)


def check_rate_limit(user_id: int, window_seconds: int, max_requests: int) -> tuple[bool, int]:
    """Check if user is within rate limit (in-memory).

    Args:
        user_id: User database ID
        window_seconds: Time window in seconds
        max_requests: Maximum requests allowed in window

    Returns:
        Tuple of (allowed, remaining_requests)
    """
    now = time.time()
    tracker = _rate_limit_store[user_id]

    if window_seconds == 1:
        # Per-second rate limit
        window_start = tracker.second_window_start
        if now - window_start >= 1.0:
            # Window expired, reset
            tracker.second_window_start = now
            tracker.second_count = 1
            return True, max_requests - 1

        if tracker.second_count >= max_requests:
            return False, 0

        tracker.second_count += 1
        remaining = max_requests - tracker.second_count
        return True, remaining
    else:
        # Per-hour rate limit
        window_start = tracker.hour_window_start
        if now - window_start >= 3600.0:
            # Window expired, reset
            tracker.hour_window_start = now
            tracker.hour_count = 1
            return True, max_requests - 1

        if tracker.hour_count >= max_requests:
            return False, 0

        tracker.hour_count += 1
        remaining = max_requests - tracker.hour_count
        return True, remaining


def cleanup_old_rate_limit_data() -> None:
    """Clean up old rate limit data (no-op for in-memory)."""
    # In implementation, we could periodically clean up old entries
    # For now, this is a no-op since the store is relatively small
    pass
