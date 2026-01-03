"""Authentication database models and operations."""

from __future__ import annotations

import uuid
from typing import Any

from database import current_timestamp_ms, get_db_connection


def init_auth_db() -> None:
    """Initialize authentication-related database tables."""
    with get_db_connection() as conn:
        # Users table with token column
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gitlab_id TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                name TEXT,
                avatar_url TEXT,
                token TEXT UNIQUE,
                token_last_used_at INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)

        # Create indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_gitlab_id ON users(gitlab_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_token ON users(token)
        """)

        conn.commit()


def create_or_update_user(gitlab_user: dict[str, Any]) -> int:
    """Create or update a user from GitLab OAuth data.

    Args:
        gitlab_user: Dictionary from GitLab userinfo endpoint with keys:
            - sub: GitLab user ID (OpenID Connect standard)
            - nickname: GitLab username (or preferred_username)
            - email: User email
            - name: Full name (optional)
            - picture: Avatar URL (optional)

    Returns:
        User database ID
    """
    now = current_timestamp_ms()

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
                str(gitlab_user["sub"]),
                gitlab_user.get("nickname") or gitlab_user.get("preferred_username", ""),
                gitlab_user.get("email", ""),
                gitlab_user.get("name"),
                gitlab_user.get("picture"),
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
            SELECT id, gitlab_id, username, email, name, avatar_url, token, token_last_used_at, created_at, updated_at
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
            SELECT id, gitlab_id, username, email, name, avatar_url, token, token_last_used_at, created_at, updated_at
            FROM users
            WHERE gitlab_id = ?
            """,
            (gitlab_id,),
        )
        row = cursor.fetchone()

        return dict(row) if row else None


def create_or_reset_user_token(user_id: int) -> str:
    """Create or reset a user's auth token.

    Args:
        user_id: User database ID

    Returns:
        The generated token UUID
    """
    # Generate token
    token = str(uuid.uuid4())
    now = current_timestamp_ms()

    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET token = ?, token_last_used_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (token, None, now, user_id),
        )
        conn.commit()

    return token


def get_user_token(user_id: int) -> str | None:
    """Get a user's token.

    Args:
        user_id: User database ID

    Returns:
        Token string or None if not set
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT token FROM users WHERE id = ?",
            (user_id,),
        )
        row = cursor.fetchone()

        return row["token"] if row else None


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
            SELECT id, gitlab_id, username, email, name, avatar_url, token_last_used_at
            FROM users
            WHERE token = ?
            """,
            (token,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        # Update last used timestamp
        now = current_timestamp_ms()
        conn.execute(
            "UPDATE users SET token_last_used_at = ? WHERE token = ?",
            (now, token),
        )
        conn.commit()

        return {
            "user_id": row["id"],
            "gitlab_id": row["gitlab_id"],
            "username": row["username"],
            "email": row["email"],
            "name": row["name"],
            "avatar_url": row["avatar_url"],
        }


def rotate_user_token(user_id: int) -> str | None:
    """Rotate a user's auth token.

    Args:
        user_id: User database ID

    Returns:
        New token UUID if successful, None if user not found
    """
    # Generate new token
    new_token = str(uuid.uuid4())
    now = current_timestamp_ms()

    with get_db_connection() as conn:
        # Check user exists and get old token
        cursor = conn.execute(
            "SELECT id FROM users WHERE id = ?",
            (user_id,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        # Update token
        conn.execute(
            """
            UPDATE users
            SET token = ?, token_last_used_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_token, None, now, user_id),
        )
        conn.commit()

        return new_token


def list_user_tokens(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """List tokens for a user (returns max 1 token with user info).

    Args:
        user_id: User database ID
        limit: Ignored, kept for compatibility

    Returns:
        List with single token dictionary or empty list
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, token, token_last_used_at, created_at
            FROM users
            WHERE id = ? AND token IS NOT NULL
            """,
            (user_id,),
        )
        row = cursor.fetchone()

        if not row:
            return []

        return [
            {
                "id": row["id"],
                "token": row["token"],
                "name": "API Token",
                "last_used_at": row["token_last_used_at"],
                "created_at": row["created_at"],
            }
        ]


def delete_user(user_id: int) -> bool:
    """Delete a user and all associated data.

    Args:
        user_id: User database ID

    Returns:
        True if user was deleted, False if not found
    """
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

        return cursor.rowcount > 0
