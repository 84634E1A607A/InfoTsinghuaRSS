"""Authentication database models and operations."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from config import TOKEN_ROTATION_DAYS
from database import get_db_connection


def init_auth_db() -> None:
    """Initialize authentication-related database tables."""
    with get_db_connection() as conn:
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gitlab_id TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                name TEXT,
                avatar_url TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)

        # Auth tokens table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auth_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                name TEXT,
                last_used_at INTEGER,
                expires_at INTEGER,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Rate limiting tracking table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rate_limit_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                window_start INTEGER NOT NULL,
                request_count INTEGER NOT NULL,
                UNIQUE(user_id, window_start),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_auth_tokens_token ON auth_tokens(token)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_auth_tokens_user ON auth_tokens(user_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_gitlab_id ON users(gitlab_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_rate_limit_user_window ON rate_limit_tracking(user_id, window_start)
        """)

        conn.commit()


def create_or_update_user(gitlab_user: dict[str, Any]) -> int:
    """Create or update a user from GitLab OAuth data.

    Args:
        gitlab_user: Dictionary from GitLab user info endpoint with keys:
            - id: GitLab user ID
            - username: GitLab username
            - email: User email
            - name: Full name (optional)
            - avatar_url: Avatar URL (optional)

    Returns:
        User database ID
    """
    now = int(datetime.now(timezone.utc).timestamp() * 1000)

    with get_db_connection() as conn:
        # Try to insert or update
        cursor = conn.execute(
            """
            INSERT INTO users (gitlab_id, username, email, name, avatar_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(gitlab_id) DO UPDATE SET
                username = excluded.username,
                email = excluded.email,
                name = excluded.name,
                avatar_url = excluded.avatar_url,
                updated_at = excluded.updated_at
            RETURNING id
            """,
            (
                str(gitlab_user["id"]),
                gitlab_user["username"],
                gitlab_user["email"],
                gitlab_user.get("name"),
                gitlab_user.get("avatar_url"),
                now,
                now,
            ),
        )
        result = cursor.fetchone()
        conn.commit()

        return result["id"]


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    """Get user by database ID.

    Args:
        user_id: User database ID

    Returns:
        User dictionary or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, gitlab_id, username, email, name, avatar_url, created_at, updated_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()

        return dict(row) if row else None


def get_user_by_gitlab_id(gitlab_id: str) -> dict[str, Any] | None:
    """Get user by GitLab ID.

    Args:
        gitlab_id: GitLab user ID (as string)

    Returns:
        User dictionary or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, gitlab_id, username, email, name, avatar_url, created_at, updated_at
            FROM users
            WHERE gitlab_id = ?
            """,
            (gitlab_id,),
        )
        row = cursor.fetchone()

        return dict(row) if row else None


def create_auth_token(user_id: int, name: str | None = None) -> str:
    """Create a new auth token for a user.

    Args:
        user_id: User database ID
        name: Optional token name for user identification

    Returns:
        The generated token UUID

    Raises:
        ValueError: If user has too many tokens
    """
    from config import MAX_TOKENS_PER_USER

    # Check token count
    token_count = count_user_tokens(user_id)
    if token_count >= MAX_TOKENS_PER_USER:
        raise ValueError(f"Maximum token limit ({MAX_TOKENS_PER_USER}) reached")

    # Generate token
    token = str(uuid.uuid4())
    now = int(datetime.now(timezone.utc).timestamp() * 1000)

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO auth_tokens (user_id, token, name, last_used_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, token, name, None, now),
        )
        conn.commit()

    return token


def validate_auth_token(token: str) -> dict[str, Any] | None:
    """Validate an auth token and return associated user.

    Args:
        token: Auth token UUID

    Returns:
        Dictionary with user_id and user data if valid, None otherwise
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT
                auth_tokens.user_id,
                users.id, users.gitlab_id, users.username, users.email, users.name, users.avatar_url,
                auth_tokens.last_used_at
            FROM auth_tokens
            JOIN users ON auth_tokens.user_id = users.id
            WHERE auth_tokens.token = ?
            """,
            (token,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        # Update last used timestamp
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        conn.execute(
            "UPDATE auth_tokens SET last_used_at = ? WHERE token = ?",
            (now, token),
        )
        conn.commit()

        return {
            "user_id": row["user_id"],
            "gitlab_id": row["gitlab_id"],
            "username": row["username"],
            "email": row["email"],
            "name": row["name"],
            "avatar_url": row["avatar_url"],
        }


def list_user_tokens(user_id: int) -> list[dict[str, Any]]:
    """List all tokens for a user.

    Args:
        user_id: User database ID

    Returns:
        List of token dictionaries with non-sensitive info
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, token, name, last_used_at, created_at
            FROM auth_tokens
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()

        return [dict(row) for row in rows]


def delete_auth_token(token: str, user_id: int) -> bool:
    """Delete an auth token.

    Args:
        token: Auth token UUID
        user_id: User ID who owns the token

    Returns:
        True if token was deleted, False otherwise
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM auth_tokens WHERE token = ? AND user_id = ?",
            (token, user_id),
        )
        conn.commit()

        return cursor.rowcount > 0


def rotate_auth_token(old_token: str, user_id: int) -> str | None:
    """Rotate an auth token (delete old, create new).

    Args:
        old_token: Old auth token UUID
        user_id: User ID who owns the token

    Returns:
        New token UUID if successful, None otherwise
    """
    # Verify ownership
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT name FROM auth_tokens WHERE token = ? AND user_id = ?",
            (old_token, user_id),
        )
        row = cursor.fetchone()

        if not row:
            return None

        token_name = row["name"]

        # Delete old token
        conn.execute(
            "DELETE FROM auth_tokens WHERE token = ? AND user_id = ?",
            (old_token, user_id),
        )

        # Create new token
        new_token = str(uuid.uuid4())
        now = int(datetime.now(timezone.utc).timestamp() * 1000)

        conn.execute(
            """
            INSERT INTO auth_tokens (user_id, token, name, last_used_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, new_token, token_name, None, now),
        )
        conn.commit()

        return new_token


def count_user_tokens(user_id: int) -> int:
    """Count active tokens for a user.

    Args:
        user_id: User database ID

    Returns:
        Number of active tokens
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM auth_tokens WHERE user_id = ?",
            (user_id,),
        )
        result = cursor.fetchone()
        return result["count"]


def check_rate_limit(user_id: int, window_seconds: int, max_requests: int) -> tuple[bool, int]:
    """Check if user is within rate limit.

    Args:
        user_id: User database ID
        window_seconds: Time window in seconds
        max_requests: Maximum requests allowed in window

    Returns:
        Tuple of (allowed, remaining_requests)
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    window_ms = window_seconds * 1000
    window_start = (now_ms // window_ms) * window_ms

    with get_db_connection() as conn:
        # Get or create rate limit tracking for this window
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO rate_limit_tracking (user_id, window_start, request_count)
            VALUES (?, ?, 0)
            """,
            (user_id, window_start),
        )
        conn.commit()

        # Get current count
        cursor = conn.execute(
            """
            SELECT request_count FROM rate_limit_tracking
            WHERE user_id = ? AND window_start = ?
            """,
            (user_id, window_start),
        )
        result = cursor.fetchone()
        current_count = result["request_count"]

        # Check if limit exceeded
        if current_count >= max_requests:
            return False, 0

        # Increment count
        conn.execute(
            """
            UPDATE rate_limit_tracking
            SET request_count = request_count + 1
            WHERE user_id = ? AND window_start = ?
            """,
            (user_id, window_start),
        )
        conn.commit()

        remaining = max_requests - (current_count + 1)
        return True, remaining


def cleanup_old_rate_limit_data() -> None:
    """Clean up old rate limit tracking data (older than 24 hours)."""
    cutoff_ms = int(datetime.now(timezone.utc).timestamp() * 1000) - (24 * 3600 * 1000)

    with get_db_connection() as conn:
        conn.execute(
            "DELETE FROM rate_limit_tracking WHERE window_start < ?",
            (cutoff_ms,),
        )
        conn.commit()
