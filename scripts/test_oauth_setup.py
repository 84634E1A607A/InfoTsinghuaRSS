#!/usr/bin/env python3
"""Test script to verify OAuth configuration and database setup."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth_db import init_auth_db
from config import (
    GITLAB_CLIENT_ID,
    GITLAB_CLIENT_SECRET,
    GITLAB_URL,
    OAUTH_ENABLED,
    SESSION_SECRET,
)
from database import get_db_connection


def check_config() -> bool:
    """Check if OAuth configuration is complete."""
    print("Checking OAuth configuration...")

    issues = []

    if not OAUTH_ENABLED:
        print("  ⚠️  OAuth is disabled")
        return True

    if not GITLAB_CLIENT_ID:
        issues.append("GITLAB_CLIENT_ID is not set")
    else:
        print(f"  ✓ GITLAB_CLIENT_ID: {GITLAB_CLIENT_ID[:8]}...")

    if not GITLAB_CLIENT_SECRET:
        issues.append("GITLAB_CLIENT_SECRET is not set")
    else:
        print(f"  ✓ GITLAB_CLIENT_SECRET: {GITLAB_CLIENT_SECRET[:8]}...")

    if not SESSION_SECRET:
        issues.append("SESSION_SECRET is not set (should be a random 32-byte hex)")
    else:
        print(f"  ✓ SESSION_SECRET: {SESSION_SECRET[:8]}...")

    print(f"  ✓ GITLAB_URL: {GITLAB_URL}")
    print(f"  ✓ OAUTH_ENABLED: {OAUTH_ENABLED}")

    if issues:
        print("\n❌ Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False

    print("\n✓ OAuth configuration is complete")
    return True


def check_database() -> bool:
    """Check if database tables are created."""
    print("\nChecking database tables...")

    try:
        init_auth_db()

        with get_db_connection() as conn:
            # Check users table
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            if cursor.fetchone():
                print("  ✓ users table exists")
            else:
                print("  ❌ users table missing")
                return False

            # Check auth_tokens table
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='auth_tokens'"
            )
            if cursor.fetchone():
                print("  ✓ auth_tokens table exists")
            else:
                print("  ❌ auth_tokens table missing")
                return False

            # Check rate_limit_tracking table
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='rate_limit_tracking'"
            )
            if cursor.fetchone():
                print("  ✓ rate_limit_tracking table exists")
            else:
                print("  ❌ rate_limit_tracking table missing")
                return False

        print("\n✓ Database tables are ready")
        return True

    except Exception as e:
        print(f"\n❌ Database error: {e}")
        return False


def print_usage_instructions() -> None:
    """Print usage instructions."""
    if not OAUTH_ENABLED:
        print("\n📖 OAuth is disabled. To enable:")
        print("   1. Set OAUTH_ENABLED=true in your environment or .env file")
        print("   2. Configure GitLab OAuth credentials")
        return

    print("\n📖 Usage Instructions:")
    print("\n1. Start the server:")
    print("   uv run app.py")

    print("\n2. Visit the login page:")
    print("   http://localhost:8000/auth/login")

    print("\n3. After authentication, you'll receive a token")

    print("\n4. Access the RSS feed:")
    print("   curl -H 'X-API-Token: YOUR_TOKEN' http://localhost:8000/rss")
    print("   # or")
    print("   curl 'http://localhost:8000/rss?token=YOUR_TOKEN'")

    print("\n5. Manage tokens:")
    print("   # List tokens")
    print("   curl -H 'X-API-Token: YOUR_TOKEN' http://localhost:8000/auth/tokens")
    print("\n   # Create new token")
    print("   curl -X POST -H 'X-API-Token: YOUR_TOKEN' \\")
    print("        -H 'Content-Type: application/json' \\")
    print('        -d \'{"name": "My RSS Reader"}\' \\')
    print("        http://localhost:8000/auth/tokens")

    print("\n6. Rate limits:")
    print("   - 1 request per second")
    print("   - 10 requests per hour")


if __name__ == "__main__":
    config_ok = check_config()
    db_ok = check_database()

    if config_ok and db_ok:
        print("\n✅ OAuth setup is complete!")
        print_usage_instructions()
        sys.exit(0)
    else:
        print("\n❌ OAuth setup has issues. Please fix them before running the application.")
        sys.exit(1)
