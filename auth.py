"""Authentication and authorization module for OAuth and token management."""

from __future__ import annotations

import secrets
from typing import Any

import httpx
from fastapi import HTTPException, Query, status

from auth_db import (
    create_or_update_user,
    validate_auth_token,
)
from config import (
    GITLAB_CLIENT_ID,
    GITLAB_CLIENT_SECRET,
    GITLAB_REDIRECT_URI,
    GITLAB_SCOPES,
    GITLAB_URL,
    SESSION_SECRET,
)


class OAuthStateManager:
    """Manage OAuth state parameters for CSRF protection."""

    def __init__(self) -> None:
        self._states: dict[str, Any] = {}

    def generate_state(self, redirect_path: str = "/") -> str:
        """Generate a secure state token.

        Args:
            redirect_path: Path to redirect to after successful auth

        Returns:
            State token
        """
        if not SESSION_SECRET:
            raise ValueError("SESSION_SECRET must be configured")

        state = secrets.token_urlsafe(32)
        self._states[state] = {"redirect_path": redirect_path}
        return state

    def validate_state(self, state: str) -> str | None:
        """Validate and consume a state token.

        Args:
            state: State token to validate

        Returns:
            Redirect path if valid, None otherwise
        """
        return self._states.pop(state, None)

    def cleanup_old_states(self, max_age_seconds: int = 600) -> None:
        """Clean up old states (should be called periodically).

        Args:
            max_age_seconds: Maximum age of state tokens
        """
        # Simple implementation: just clear all states
        # In production, you'd want to track timestamps
        if len(self._states) > 1000:
            self._states.clear()


oauth_state_manager = OAuthStateManager()


def get_gitlab_authorization_url(redirect_path: str = "/") -> str:
    """Generate GitLab OAuth authorization URL.

    Args:
        redirect_path: Path to redirect to after successful auth

    Returns:
        Authorization URL
    """
    state = oauth_state_manager.generate_state(redirect_path)

    base_url = GITLAB_URL.rstrip("/")
    auth_url = f"{base_url}/oauth/authorize"

    params = {
        "client_id": GITLAB_CLIENT_ID,
        "redirect_uri": GITLAB_REDIRECT_URI,
        "response_type": "code",
        "state": state,
        "scope": " ".join(GITLAB_SCOPES),
    }

    # Build URL with params
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{auth_url}?{query_string}"


async def exchange_gitlab_code(code: str) -> dict[str, Any]:
    """Exchange OAuth code for access token.

    Args:
        code: Authorization code from GitLab

    Returns:
        Token response with access_token

    Raises:
        HTTPException: If token exchange fails
    """
    token_url = f"{GITLAB_URL.rstrip('/')}/oauth/token"

    data = {
        "client_id": GITLAB_CLIENT_ID,
        "client_secret": GITLAB_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": GITLAB_REDIRECT_URI,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code",
            )

        return response.json()


async def get_gitlab_user_info(access_token: str) -> dict[str, Any]:
    """Get user info from GitLab using OpenID Connect userinfo endpoint.

    Args:
        access_token: OAuth access token

    Returns:
        User info dictionary

    Raises:
        HTTPException: If user info request fails
    """
    userinfo_url = f"{GITLAB_URL.rstrip('/')}/oauth/userinfo"

    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(userinfo_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch user info: {response.status_code}")
            print(f"Response: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch user info: {response.text}",
            )

        return response.json()


async def handle_gitlab_callback(code: str, state: str) -> dict[str, Any]:
    """Handle GitLab OAuth callback.

    Args:
        code: Authorization code from GitLab
        state: State parameter from callback

    Returns:
        Dictionary with user_id and redirect_path

    Raises:
        HTTPException: If callback validation fails
    """
    # Validate state
    redirect_path = oauth_state_manager.validate_state(state)
    if redirect_path is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter",
        )

    # Exchange code for token
    token_data = await exchange_gitlab_code(code)
    access_token = token_data.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No access token in response",
        )

    # Get user info
    user_info = await get_gitlab_user_info(access_token)

    # Create or update user
    user_id = create_or_update_user(user_info)

    return {
        "user_id": user_id,
        "redirect_path": redirect_path,
    }


def get_current_user_optional(
    token: str | None = Query(None),
) -> dict[str, Any] | None:
    """Get current user from token (optional).

    Args:
        token: API token from query parameter

    Returns:
        User dictionary if valid token, None otherwise
    """
    if not token:
        return None

    return validate_auth_token(token)


async def get_current_user(
    token: str = Query(...),
) -> dict[str, Any]:
    """Get current user from token (required).

    Args:
        token: API token from query parameter

    Returns:
        User dictionary

    Raises:
        HTTPException: If token is invalid or missing
    """
    user_data = validate_auth_token(token)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
        )

    return user_data


async def get_current_user_from_path(token: str) -> dict[str, Any]:
    """Get current user from path parameter token.

    Args:
        token: API token from path parameter

    Returns:
        User dictionary

    Raises:
        HTTPException: If token is invalid or missing
    """
    user_data = validate_auth_token(token)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    return user_data
