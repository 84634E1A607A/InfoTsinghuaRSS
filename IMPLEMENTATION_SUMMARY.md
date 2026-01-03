# OAuth Authentication Implementation Summary

## Overview

A complete GitLab OAuth authentication system has been added to the RSS feeder application with token-based access control and per-user rate limiting.

## Files Created

### 1. `auth_db.py` - Authentication Database Layer
- **Users table**: Stores GitLab user information (id, username, email, name, avatar_url)
- **Auth tokens table**: Stores UUID-based API tokens with metadata
- **Rate limit tracking table**: Tracks per-user rate limit counters
- **Functions**:
  - `init_auth_db()`: Initialize authentication tables
  - `create_or_update_user()`: Create/update user from GitLab data
  - `create_auth_token()`: Generate new UUID token
  - `validate_auth_token()`: Validate token and return user data
  - `list_user_tokens()`: List all tokens for a user
  - `delete_auth_token()`: Delete a token
  - `rotate_auth_token()`: Rotate a token (delete old, create new)
  - `check_rate_limit()`: Check and enforce rate limits
  - `cleanup_old_rate_limit_data()`: Clean up old rate limit records

### 2. `auth.py` - Authentication & Authorization Module
- **OAuthStateManager**: CSRF protection for OAuth flow
- **GitLab OAuth Integration**:
  - `get_gitlab_authorization_url()`: Generate OAuth authorization URL
  - `exchange_gitlab_code()`: Exchange authorization code for access token
  - `get_gitlab_user_info()`: Fetch user info from GitLab
  - `handle_gitlab_callback()`: Process OAuth callback
- **Authentication Dependencies**:
  - `get_current_user()`: Require authentication
  - `get_current_user_optional()`: Optional authentication
- **RateLimitMiddleware**: Per-user rate limiting (1 req/sec, 10 req/hour)
- **TokenManagement**: Token CRUD operations

### 3. `OAUTH_SETUP.md` - Setup Documentation
- Complete setup guide for GitLab OAuth
- Usage examples for all endpoints
- Security considerations
- Configuration options

### 4. `.env.example` - Environment Configuration Template
- OAuth configuration template
- Includes pre-generated SESSION_SECRET

### 5. `scripts/test_oauth_setup.py` - Test Script
- Verify OAuth configuration
- Check database tables
- Display usage instructions

## Files Modified

### 1. `pyproject.toml`
Added dependencies:
- `authlib>=1.3.0`: OAuth library
- `httpx>=0.26.0`: Async HTTP client for OAuth
- `pydantic>=2.5.0`: Data validation
- `python-multipart>=0.0.6`: Form data parsing

### 2. `config.py`
Added configuration sections:
- **OAuth Authentication Settings**:
  - `OAUTH_ENABLED`: Enable/disable auth (env: OAUTH_ENABLED)
  - `GITLAB_URL`: GitLab instance URL (env: GITLAB_URL)
  - `GITLAB_CLIENT_ID`: OAuth client ID (env: GITLAB_CLIENT_ID)
  - `GITLAB_CLIENT_SECRET`: OAuth client secret (env: GITLAB_CLIENT_SECRET)
  - `GITLAB_REDIRECT_URI`: OAuth callback URL (env: GITLAB_REDIRECT_URI)
  - `GITLAB_SCOPES`: OAuth scopes
  - `SESSION_SECRET`: Session secret for CSRF (env: SESSION_SECRET)

- **Auth Token Settings**:
  - `TOKEN_ROTATION_DAYS`: Token rotation period (default: 90)
  - `MAX_TOKENS_PER_USER`: Max tokens per user (default: 10)

- **Per-User Rate Limiting**:
  - `USER_RATE_LIMIT_PER_SECOND`: 1 request/second
  - `USER_RATE_LIMIT_PER_HOUR`: 10 requests/hour
  - `RATE_LIMIT_WINDOW_SECOND`: 1 second window
  - `RATE_LIMIT_WINDOW_HOUR`: 3600 second window (1 hour)

### 3. `app.py`
- Integrated authentication middleware
- Added OAuth endpoints:
  - `GET /auth/login`: Redirect to GitLab OAuth
  - `GET /auth/callback`: Handle OAuth callback
- Added token management endpoints:
  - `GET /auth/tokens`: List user's tokens
  - `POST /auth/tokens`: Create new token
  - `DELETE /auth/tokens/{token}`: Delete token
  - `POST /auth/tokens/{token}/rotate`: Rotate token
- Updated `/rss` endpoint to require authentication (when enabled)
- Updated `/` endpoint to show auth status and user info
- Added `init_auth_db()` to lifespan

## API Endpoints

### Authentication Flow
1. **Login**: `GET /auth/login`
   - Redirects to GitLab OAuth

2. **Callback**: `GET /auth/callback?code=xxx&state=yyy`
   - Exchanges code for token
   - Creates user record
   - Generates API token
   - Returns token to user

### Token Management (All require authentication)

1. **List Tokens**: `GET /auth/tokens`
   ```bash
   curl -H "X-API-Token: YOUR_TOKEN" http://localhost:8000/auth/tokens
   ```

2. **Create Token**: `POST /auth/tokens`
   ```bash
   curl -X POST \
     -H "X-API-Token: YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name": "My RSS Reader"}' \
     http://localhost:8000/auth/tokens
   ```

3. **Delete Token**: `DELETE /auth/tokens/{token}`
   ```bash
   curl -X DELETE \
     -H "X-API-Token: YOUR_TOKEN" \
     http://localhost:8000/auth/tokens/TOKEN_TO_DELETE
   ```

4. **Rotate Token**: `POST /auth/tokens/{token}/rotate`
   ```bash
   curl -X POST \
     -H "X-API-Token: YOUR_TOKEN" \
     http://localhost:8000/auth/tokens/TOKEN_TO_ROTATE/rotate
   ```

### RSS Feed (Protected)

**Method 1: X-API-Token Header**
```bash
curl -H "X-API-Token: YOUR_TOKEN" http://localhost:8000/rss
```

**Method 2: Query Parameter**
```bash
curl "http://localhost:8000/rss?token=YOUR_TOKEN"
```

**Method 3: Bearer Token**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/rss
```

## Rate Limiting

### Per-User Limits
- **1 request per second**
- **10 requests per hour**

### Response Headers
```
X-RateLimit-Limit-Second: 1
X-RateLimit-Remaining-Second: 0
X-RateLimit-Limit-Hour: 10
X-RateLimit-Remaining-Hour: 9
```

### Error Response
When rate limit is exceeded:
```json
{
  "detail": "Rate limit exceeded: maximum 1 request per second",
  "limit": 1,
  "window": "1 second"
}
```

## Database Schema

### users table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gitlab_id TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    name TEXT,
    avatar_url TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
```

### auth_tokens table
```sql
CREATE TABLE auth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    name TEXT,
    last_used_at INTEGER,
    expires_at INTEGER,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### rate_limit_tracking table
```sql
CREATE TABLE rate_limit_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    window_start INTEGER NOT NULL,
    request_count INTEGER NOT NULL,
    UNIQUE(user_id, window_start),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

## Security Features

1. **CSRF Protection**: OAuth state parameter with validation
2. **UUID Tokens**: Random, unguessable tokens
3. **Token Rotation**: Support for token rotation
4. **Rate Limiting**: Per-user rate limits prevent abuse
5. **Secure Headers**: WWW-Authenticate headers on 401
6. **Token Ownership**: Users can only manage their own tokens
7. **Session Secret**: Required for state parameter signing
8. **SQL Injection Protection**: Parameterized queries throughout

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| OAUTH_ENABLED | No | true | Enable/disable authentication |
| GITLAB_URL | No | https://gitlab.com | GitLab instance URL |
| GITLAB_CLIENT_ID | Yes* | - | OAuth application ID |
| GITLAB_CLIENT_SECRET | Yes* | - | OAuth application secret |
| GITLAB_REDIRECT_URI | No | http://localhost:8000/auth/callback | OAuth callback URL |
| SESSION_SECRET | Yes* | - | Session secret (32-byte hex) |

*Required when OAUTH_ENABLED=true

## Testing

Run the test script to verify setup:
```bash
uv run python scripts/test_oauth_setup.py
```

## Next Steps for Deployment

1. **Set up GitLab OAuth application** in production
2. **Update environment variables**:
   - `GITLAB_REDIRECT_URI` to production URL
   - Set secure `GITLAB_CLIENT_ID` and `GITLAB_CLIENT_SECRET`
   - Generate and set `SESSION_SECRET`
3. **Test OAuth flow** in production environment
4. **Set up HTTPS** (required for secure OAuth in production)
5. **Monitor rate limiting** and adjust limits if needed
6. **Set up regular backups** of authentication database

## Notes

- The application continues to work without authentication if `OAUTH_ENABLED=false`
- Existing health check endpoint remains public
- Token rotation is supported but not enforced
- Rate limit data is automatically cleaned up (cleanup logic should be added as a scheduled task)
