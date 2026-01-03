# OAuth Authentication Setup

This application now supports GitLab OAuth authentication for accessing the RSS feed.

## Features

- **GitLab OAuth Integration**: Users authenticate via their GitLab account
- **Token-Based Authentication**: UUID-based tokens for RSS feed access
- **Token Management**: Create, list, rotate, and delete auth tokens
- **Per-User Rate Limiting**: 1 request/second, 10 requests/hour per user
- **Token Rotation**: Automatic token rotation support

## Setup

### 1. Create GitLab OAuth Application

1. Go to your GitLab instance (e.g., https://gitlab.com)
2. Navigate to: User Settings → Applications
3. Create a new application with:
   - **Redirect URI**: `http://localhost:8000/auth/callback` (or your production URL)
   - **Scopes**: `read_user` (minimum required)
4. Copy the **Application ID** and **Secret**

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OAUTH_ENABLED=true
GITLAB_URL=https://gitlab.com
GITLAB_CLIENT_ID=your_application_id
GITLAB_CLIENT_SECRET=your_secret
GITLAB_REDIRECT_URI=http://localhost:8000/auth/callback
SESSION_SECRET=your_random_secret
```

Generate a session secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Install Dependencies

```bash
uv sync
```

### 4. Run the Application

```bash
uv run app.py
```

## Usage

### Getting an Access Token

1. **Authenticate via GitLab**:
   ```bash
   curl http://localhost:8000/auth/login
   ```
   This redirects you to GitLab for authentication.

2. **After Callback**: You'll receive a token in the response:
   ```json
   {
     "token": "uuid-here",
     "instructions": "Use this token with X-API-Token header"
   }
   ```

### Accessing the RSS Feed

#### Method 1: Using X-API-Token Header

```bash
curl -H "X-API-Token: your-uuid-token" http://localhost:8000/rss
```

#### Method 2: Using Query Parameter

```bash
curl "http://localhost:8000/rss?token=your-uuid-token"
```

#### Method 3: Using Bearer Token

```bash
curl -H "Authorization: Bearer your-uuid-token" http://localhost:8000/rss
```

### Token Management

All token management endpoints require authentication.

#### List Your Tokens

```bash
curl -H "X-API-Token: your-uuid-token" http://localhost:8000/auth/tokens
```

#### Create a New Token

```bash
curl -X POST \
  -H "X-API-Token: your-uuid-token" \
  -H "Content-Type: application/json" \
  -d '{"name": "My RSS Reader"}' \
  http://localhost:8000/auth/tokens
```

#### Delete a Token

```bash
curl -X DELETE \
  -H "X-API-Token: your-uuid-token" \
  http://localhost:8000/auth/tokens/token-to-delete
```

#### Rotate a Token

```bash
curl -X POST \
  -H "X-API-Token: your-uuid-token" \
  http://localhost:8000/auth/tokens/token-to-rotate/rotate
```

## Rate Limiting

Each authenticated user is rate-limited to:
- **1 request per second**
- **10 requests per hour**

Rate limit status is returned in response headers:
```
X-RateLimit-Limit-Second: 1
X-RateLimit-Remaining-Second: 0
X-RateLimit-Limit-Hour: 10
X-RateLimit-Remaining-Hour: 9
```

## Configuration Options

### Disable OAuth

To disable authentication and allow open access:

```env
OAUTH_ENABLED=false
```

### Self-Hosted GitLab

Change the `GITLAB_URL`:

```env
GITLAB_URL=https://gitlab.example.com
```

### Token Limits

Adjust in `config.py`:
- `MAX_TOKENS_PER_USER`: Maximum tokens per user (default: 10)
- `TOKEN_ROTATION_DAYS`: Token rotation period (default: 90)

### Rate Limits

Adjust in `config.py`:
- `USER_RATE_LIMIT_PER_SECOND`: Requests per second (default: 1)
- `USER_RATE_LIMIT_PER_HOUR`: Requests per hour (default: 10)

## Security Considerations

1. **Keep Secrets Safe**: Never commit `.env` to version control
2. **HTTPS**: Use HTTPS in production for OAuth callbacks
3. **Token Storage**: Store tokens securely in your RSS reader
4. **Token Rotation**: Regularly rotate tokens for better security
5. **Rate Limiting**: Helps prevent abuse but monitor usage patterns

## Database Schema

The authentication system adds three tables:

- **users**: GitLab user information
- **auth_tokens**: User API tokens
- **rate_limit_tracking**: Rate limiting data

All tables are automatically created on application startup.
