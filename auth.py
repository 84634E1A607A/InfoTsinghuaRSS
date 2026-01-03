"""Authentication and authorization module for OAuth and token management."""

from __future__ import annotations

import secrets
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from auth_db import (
    check_rate_limit,
    cleanup_old_rate_limit_data,
    create_auth_token,
    create_or_update_user,
    delete_auth_token,
    list_user_tokens,
    rotate_auth_token,
    validate_auth_token,
)
from config import (
    GITLAB_CLIENT_ID,
    GITLAB_CLIENT_SECRET,
    GITLAB_REDIRECT_URI,
    GITLAB_SCOPES,
    GITLAB_URL,
    RATE_LIMIT_WINDOW_HOUR,
    RATE_LIMIT_WINDOW_SECOND,
    SESSION_SECRET,
    USER_RATE_LIMIT_PER_HOUR,
    USER_RATE_LIMIT_PER_SECOND,
)

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Token", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


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


def extract_token_from_request(request: Request) -> str | None:
    """Extract authentication token from request headers or query parameters.

    Args:
        request: FastAPI request

    Returns:
        Token string if found, None otherwise
    """
    # Try X-API-Token header first
    token = request.headers.get("X-API-Token")

    # Try Bearer token
    if not token:
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]

    # Try query parameter
    if not token:
        token = request.query_params.get("token")

    return token


def get_current_user_optional(
    request: Request,
    token: str | None = Depends(api_key_header),
    query_token: str | None = None,
) -> dict[str, Any] | None:
    """Get current user from token (optional).

    Args:
        request: FastAPI request
        token: API token from header
        query_token: API token from query parameter

    Returns:
        User dictionary if valid token, None otherwise
    """
    if not token:
        # Try Bearer token
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]

    # Use query token if header token not present
    if not token and query_token:
        token = query_token

    if not token:
        return None

    user_data = validate_auth_token(token)
    return user_data


async def get_current_user(
    request: Request,
    token: str | None = Depends(api_key_header),
) -> dict[str, Any]:
    """Get current user from token (required).

    Args:
        request: FastAPI request
        token: API token from header

    Returns:
        User dictionary

    Raises:
        HTTPException: If token is invalid or missing
    """
    user_data = get_current_user_optional(request, token)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_data


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce per-user rate limiting."""

    async def dispatch(self, request: Request, call_next):
        """Process request and apply rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Get user from token if present
        token = extract_token_from_request(request)
        user_data = validate_auth_token(token) if token else None

        remaining_second = 0
        remaining_hour = 0

        if user_data:
            user_id = user_data["user_id"]

            # Check per-second rate limit
            allowed_second, remaining_second = check_rate_limit(
                user_id=user_id,
                window_seconds=RATE_LIMIT_WINDOW_SECOND,
                max_requests=USER_RATE_LIMIT_PER_SECOND,
            )

            if not allowed_second:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded: maximum 1 request per second",
                        "limit": USER_RATE_LIMIT_PER_SECOND,
                        "window": "1 second",
                    },
                )

            # Check per-hour rate limit
            allowed_hour, remaining_hour = check_rate_limit(
                user_id=user_id,
                window_seconds=RATE_LIMIT_WINDOW_HOUR,
                max_requests=USER_RATE_LIMIT_PER_HOUR,
            )

            if not allowed_hour:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded: maximum 10 requests per hour",
                        "limit": USER_RATE_LIMIT_PER_HOUR,
                        "window": "1 hour",
                    },
                )

        # Clean up old rate limit data periodically (simplified)
        # In production, use a background task
        if cleanup_old_rate_limit_data.__code__.co_code != 0:  # Simple check
            pass

        response = await call_next(request)

        # Add rate limit headers if authenticated
        if user_data:
            response.headers["X-RateLimit-Limit-Second"] = str(USER_RATE_LIMIT_PER_SECOND)
            response.headers["X-RateLimit-Remaining-Second"] = str(remaining_second)
            response.headers["X-RateLimit-Limit-Hour"] = str(USER_RATE_LIMIT_PER_HOUR)
            response.headers["X-RateLimit-Remaining-Hour"] = str(remaining_hour)

        return response


class TokenManagement:
    """Token management operations."""

    @staticmethod
    def create_token(user_id: int, name: str | None = None) -> str:
        """Create a new auth token.

        Args:
            user_id: User database ID
            name: Optional token name

        Returns:
            New token UUID

        Raises:
            HTTPException: If token creation fails
        """
        try:
            return create_auth_token(user_id, name)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @staticmethod
    def list_tokens(user_id: int) -> list[dict[str, Any]]:
        """List all tokens for a user.

        Args:
            user_id: User database ID

        Returns:
            List of token dictionaries
        """
        return list_user_tokens(user_id)

    @staticmethod
    def delete_token(token: str, user_id: int) -> bool:
        """Delete a token.

        Args:
            token: Token UUID
            user_id: User ID who owns the token

        Returns:
            True if deleted, False otherwise
        """
        return delete_auth_token(token, user_id)

    @staticmethod
    def rotate_token(token: str, user_id: int) -> str:
        """Rotate a token (delete old, create new).

        Args:
            token: Old token UUID
            user_id: User ID who owns the token

        Returns:
            New token UUID

        Raises:
            HTTPException: If rotation fails
        """
        new_token = rotate_auth_token(token, user_id)
        if not new_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found or does not belong to user",
            )
        return new_token
