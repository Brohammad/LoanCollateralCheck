# Security Quick Reference

Quick commands and examples for using the security layer.

## Setup

```python
from fastapi import FastAPI
from security import setup_all_security

app = FastAPI()

# One-line setup
setup_all_security(
    app,
    environment="production",
    redis_url="redis://localhost:6379"
)
```

## Authentication

### Create User
```python
from security import AuthManager

auth = AuthManager()
user = auth.create_user("john", "password123", "john@example.com", roles=["user"])
```

### Generate API Key
```python
api_key = auth.api_key_auth.generate_api_key("john", "Production key")
# Returns: sk_abc123def456...
```

### Login (Get JWT)
```python
token = auth.login("john", "password123")
# token.access_token, token.refresh_token
```

### Protected Route
```python
from security import get_current_user, require_roles
from fastapi import Depends

@app.get("/protected")
async def protected(user=Depends(get_current_user)):
    return {"user": user.username}

@app.get("/admin")
async def admin_only(user=Depends(require_roles(["admin"]))):
    return {"message": "Admin access"}
```

## Rate Limiting

### Apply to Route
```python
from security import rate_limit, rate_limit_dependency
from fastapi import Depends

# Method 1: Decorator
@app.post("/chat")
@rate_limit(requests_per_minute=30)
async def chat(message: str):
    return {"response": "ok"}

# Method 2: Dependency
@app.post("/search")
async def search(query: str, _=Depends(rate_limit_dependency)):
    return {"results": []}
```

### Custom Limits
```python
from security import get_rate_limiter

limiter = get_rate_limiter()
limiter.endpoint_limits["/api/expensive"] = 5  # 5 RPM
```

## Input Validation

### Validate Input
```python
from security import InputValidator, UserMessageRequest

validator = InputValidator()

# Basic validation
if validator.is_safe("user input"):
    # Process
    pass

# Pydantic model
request = UserMessageRequest(
    message="What is HELOC?",
    session_id="550e8400-e29b-41d4-a716-446655440000"
)
```

## Audit Logging

### Log Events
```python
from security import get_audit_logger

audit = get_audit_logger()

# Authentication
audit.log_login_success("john", "192.168.1.1")
audit.log_login_failure("john", "192.168.1.1", "Invalid password")

# Authorization
audit.log_access_denied("john", "/admin", "GET", "192.168.1.1", "No permission")

# Security
audit.log_injection_attempt("sql", "' OR 1=1", "192.168.1.1", "/search")
```

### Query Logs
```python
# Get user events
events = audit.get_events_by_user("john", limit=100)

# Get security violations
violations = audit.get_security_violations(limit=50)

# Get events by IP
ip_events = audit.get_events_by_ip("192.168.1.1", limit=100)
```

## Security Headers

### Setup
```python
from security import setup_security_headers

# Basic
setup_security_headers(app)

# Custom CSP
from security import SecurityHeadersMiddleware

app.add_middleware(
    SecurityHeadersMiddleware,
    enable_csp=True,
    csp_directives={
        "default-src": ["'self'"],
        "script-src": ["'self'", "https://cdn.example.com"]
    }
)
```

## CORS

### Setup
```python
from security import setup_cors

# Environment-based
setup_cors(app, environment="production")

# Custom origins
setup_cors(
    app,
    allowed_origins=["https://app.example.com"],
    allow_credentials=True
)

# Dynamic patterns
from security import setup_dynamic_cors

setup_dynamic_cors(
    app,
    allowed_origin_patterns=["https://*.example.com"]
)
```

## Testing

### Test Authentication
```bash
# Get API key
API_KEY="sk_abc123..."

# Use API key
curl -H "X-API-Key: $API_KEY" http://localhost:8000/protected

# Login and get JWT
TOKEN=$(curl -X POST http://localhost:8000/login \
  -d '{"username":"john","password":"pass"}' \
  | jq -r '.access_token')

# Use JWT
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/protected
```

### Test Rate Limiting
```bash
# Hit endpoint until rate limited
for i in {1..100}; do
  curl http://localhost:8000/chat -d '{"message":"test"}'
done

# Check rate limit headers
curl -I http://localhost:8000/chat
# X-RateLimit-Limit: 30
# X-RateLimit-Remaining: 25
# X-RateLimit-Reset: 1699123456
```

## Environment Variables

```bash
# .env file
SECRET_KEY=<min-32-character-random-key>
REDIS_URL=redis://localhost:6379
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS=https://app.example.com,https://www.example.com
```

## Common Issues

### Rate limit too strict
```python
limiter = get_rate_limiter()
limiter.endpoint_limits["/api/chat"] = 100  # Increase limit
```

### CORS not working
```python
# Ensure OPTIONS method is allowed
setup_cors(
    app,
    allowed_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)
```

### JWT expired
```python
# Use refresh token
new_token = auth.jwt_auth.refresh_access_token(refresh_token)
```

### Redis connection failed
```python
# Rate limiter automatically falls back to in-memory
# Check Redis:
import redis.asyncio as redis
r = await redis.from_url("redis://localhost:6379")
await r.ping()
```

## File Structure

```
security/
├── __init__.py          # Module exports, setup_all_security()
├── validation.py        # Input validation, Pydantic models
├── rate_limiter.py      # Token bucket, Redis rate limiting
├── auth.py             # API keys, JWT, RBAC
├── headers.py          # Security headers, CSP, HSTS
├── audit.py            # Security event logging
└── cors.py             # CORS configuration

docs/
└── SECURITY_GUIDE.md   # Complete documentation
```

## Default Limits

| Endpoint | Rate Limit |
|----------|------------|
| `/api/chat` | 30 RPM |
| `/api/search` | 100 RPM |
| `/api/health` | 1000 RPM |
| Default | 60 RPM |

## Token Expiration

| Token Type | Expiration |
|------------|------------|
| Access Token (JWT) | 30 minutes |
| Refresh Token (JWT) | 7 days |
| API Key | Never (manual revocation) |

## Security Headers Applied

- Content-Security-Policy
- Strict-Transport-Security (HSTS)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy
- Cross-Origin-Opener-Policy: same-origin
- Cross-Origin-Resource-Policy: same-origin
- Cross-Origin-Embedder-Policy: require-corp

## Complete Example

```python
from fastapi import FastAPI, Depends
from security import (
    setup_all_security,
    get_current_user,
    require_roles,
    rate_limit,
    UserMessageRequest,
    get_audit_logger
)

app = FastAPI()

# Setup security
setup_all_security(app, environment="production")

# Get components
audit = get_audit_logger()

# Public endpoint
@app.get("/health")
@rate_limit(requests_per_minute=1000)
async def health():
    return {"status": "healthy"}

# Protected endpoint
@app.post("/chat")
@rate_limit(requests_per_minute=30)
async def chat(
    request: UserMessageRequest,
    user=Depends(get_current_user)
):
    audit.log_access_granted(
        user.username,
        "/chat",
        "POST",
        "192.168.1.1"
    )
    return {"response": "AI response", "user": user.username}

# Admin endpoint
@app.get("/admin/users")
async def admin_users(user=Depends(require_roles(["admin"]))):
    return {"users": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

For detailed documentation, see `docs/SECURITY_GUIDE.md`
