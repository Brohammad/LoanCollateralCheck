# Security Implementation Guide

Complete security layer implementation for the AI Agent System.

## Table of Contents
1. [Overview](#overview)
2. [Components](#components)
3. [Quick Start](#quick-start)
4. [Authentication](#authentication)
5. [Rate Limiting](#rate-limiting)
6. [Security Headers](#security-headers)
7. [Audit Logging](#audit-logging)
8. [CORS Configuration](#cors-configuration)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The security layer provides comprehensive protection through:

- **Input Validation**: SQL injection, XSS, command injection prevention
- **Rate Limiting**: Token bucket algorithm with Redis support
- **Authentication**: Dual API key + JWT token system
- **Authorization**: Role-based access control (RBAC)
- **Security Headers**: CSP, HSTS, X-Frame-Options, and more
- **Audit Logging**: Complete security event tracking
- **CORS**: Secure cross-origin resource sharing

### Security Architecture

```
┌─────────────────────────────────────────────────────┐
│              Client Request                          │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│         CORS Validation                              │
│   ✓ Origin check  ✓ Preflight handling              │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│         Rate Limiting                                │
│   ✓ Token bucket  ✓ Per-IP/API-key limits           │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│         Authentication                               │
│   ✓ API key OR JWT token  ✓ User validation         │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│         Authorization                                │
│   ✓ Role check  ✓ Permission validation             │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│         Input Validation                             │
│   ✓ SQL/XSS/Command injection  ✓ Schema validation  │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│         Request Processing                           │
│   ✓ Business logic  ✓ Database operations           │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│         Security Headers                             │
│   ✓ CSP  ✓ HSTS  ✓ X-Frame-Options                  │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│         Audit Logging                                │
│   ✓ Log all security events  ✓ Structured logs      │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│              Response to Client                      │
└─────────────────────────────────────────────────────┘
```

---

## Components

### 1. Input Validation (`security/validation.py`)

Protects against injection attacks and validates request schemas.

**Features:**
- SQL injection detection (UNION, DROP, INSERT patterns)
- XSS attack detection (<script>, javascript:, onerror patterns)
- Command injection detection (;, |, `, $( patterns)
- Pydantic model validation for all requests
- Character limits and format validation

**Usage:**
```python
from security import InputValidator, UserMessageRequest

validator = InputValidator()

# Validate text input
if validator.is_safe("user input here"):
    # Process input
    pass

# Use Pydantic models
request = UserMessageRequest(
    message="What is HELOC?",
    session_id="550e8400-e29b-41d4-a716-446655440000"
)
```

### 2. Rate Limiting (`security/rate_limiter.py`)

Token bucket algorithm prevents API abuse and DOS attacks.

**Features:**
- Token bucket algorithm with burst support
- Redis-backed distributed rate limiting
- In-memory fallback for development
- Per-IP and per-API-key limiting
- Endpoint-specific limits
- Rate limit headers (X-RateLimit-*)

**Default Limits:**
- `/api/chat`: 30 requests/minute
- `/api/search`: 100 requests/minute
- `/api/health`: 1000 requests/minute
- Default: 60 requests/minute

**Usage:**
```python
from fastapi import FastAPI, Depends
from security import rate_limit_dependency, rate_limit

app = FastAPI()

# Option 1: Dependency injection
@app.post("/api/chat")
async def chat(request: dict, _rate_limit=Depends(rate_limit_dependency)):
    return {"response": "ok"}

# Option 2: Decorator
@app.post("/api/search")
@rate_limit(requests_per_minute=100)
async def search(query: str):
    return {"results": []}

# Option 3: Middleware (applies to all routes)
from security import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)
```

### 3. Authentication (`security/auth.py`)

Dual authentication system with API keys and JWT tokens.

**Features:**
- API keys with "sk_" prefix (SHA256 hashed)
- JWT access tokens (30 min expiration)
- JWT refresh tokens (7 days expiration)
- Password hashing with bcrypt
- Role-based access control (RBAC)
- Token refresh mechanism

**Usage:**
```python
from security import AuthManager, get_current_user, require_roles
from fastapi import Depends

auth_manager = AuthManager()

# Create user
user = auth_manager.create_user(
    username="john_doe",
    password="secure_password",
    email="john@example.com",
    roles=["user", "admin"]
)

# Generate API key
api_key = auth_manager.api_key_auth.generate_api_key(
    username="john_doe",
    description="Production API key"
)

# Login (get JWT tokens)
token = auth_manager.login("john_doe", "secure_password")
print(f"Access Token: {token.access_token}")
print(f"Refresh Token: {token.refresh_token}")

# Protected route - any authentication method
@app.get("/api/protected")
async def protected_route(user=Depends(get_current_user)):
    return {"message": f"Hello {user.username}"}

# Protected route - requires specific roles
@app.get("/api/admin")
async def admin_route(user=Depends(require_roles(["admin"]))):
    return {"message": "Admin access granted"}
```

**Authentication Methods:**

1. **API Key** (recommended for server-to-server):
   ```bash
   curl -H "X-API-Key: sk_1234567890abcdef" https://api.example.com/chat
   ```

2. **JWT Token** (recommended for user sessions):
   ```bash
   # Get token
   curl -X POST https://api.example.com/login \
     -d '{"username": "john", "password": "pass"}'
   
   # Use token
   curl -H "Authorization: Bearer <access_token>" \
     https://api.example.com/chat
   ```

### 4. Security Headers (`security/headers.py`)

Comprehensive security headers protect against common web vulnerabilities.

**Headers Applied:**
- **Content-Security-Policy**: Prevents XSS attacks
- **Strict-Transport-Security**: Enforces HTTPS
- **X-Frame-Options**: Prevents clickjacking
- **X-Content-Type-Options**: Prevents MIME sniffing
- **X-XSS-Protection**: Legacy XSS protection
- **Referrer-Policy**: Controls referrer information
- **Permissions-Policy**: Restricts browser features
- **Cross-Origin-*-Policy**: Resource isolation

**Usage:**
```python
from security import setup_security_headers

# Basic setup
setup_security_headers(app)

# Custom CSP directives
from security import SecurityHeadersMiddleware

app.add_middleware(
    SecurityHeadersMiddleware,
    enable_csp=True,
    enable_hsts=True,
    csp_directives={
        "default-src": ["'self'"],
        "script-src": ["'self'", "https://trusted-cdn.com"],
        "style-src": ["'self'", "'unsafe-inline'"],
    }
)
```

### 5. Audit Logging (`security/audit.py`)

Structured logging of all security events.

**Event Types:**
- Authentication: login, logout, token refresh/expiry
- Authorization: access granted/denied, permission violations
- API Keys: created, used, revoked, invalid
- Rate Limiting: exceeded, warnings
- Security: suspicious activity, injection attempts

**Usage:**
```python
from security import get_audit_logger, AuditEventType, AuditSeverity

audit_logger = get_audit_logger()

# Log successful login
audit_logger.log_login_success(
    username="john_doe",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0"
)

# Log failed login
audit_logger.log_login_failure(
    username="john_doe",
    ip_address="192.168.1.1",
    reason="Invalid password"
)

# Log access denied
audit_logger.log_access_denied(
    username="john_doe",
    endpoint="/api/admin",
    method="GET",
    ip_address="192.168.1.1",
    reason="Insufficient permissions"
)

# Log injection attempt
audit_logger.log_injection_attempt(
    injection_type="sql",
    payload="' OR '1'='1",
    ip_address="192.168.1.1",
    endpoint="/api/search"
)

# Query audit logs
recent_violations = audit_logger.get_security_violations(limit=100)
user_events = audit_logger.get_events_by_user("john_doe", limit=50)
```

### 6. CORS Configuration (`security/cors.py`)

Secure cross-origin resource sharing configuration.

**Features:**
- Environment-specific origin whitelisting
- Credential handling
- Method and header restrictions
- Preflight caching
- Dynamic origin validation with patterns

**Usage:**
```python
from security import setup_cors

# Basic setup (environment-based)
setup_cors(app, environment="production")

# Custom origins
setup_cors(
    app,
    allowed_origins=[
        "https://app.example.com",
        "https://www.example.com"
    ],
    allow_credentials=True
)

# Dynamic patterns (supports wildcards)
from security import setup_dynamic_cors

setup_dynamic_cors(
    app,
    allowed_origin_patterns=[
        "https://*.example.com",
        "https://example.com"
    ]
)
```

**Environment Defaults:**
- **Development**: `http://localhost:*`, `http://127.0.0.1:*`
- **Staging**: `https://staging*.example.com`
- **Production**: `https://example.com`, `https://www.example.com`, `https://app.example.com`

---

## Quick Start

### Complete Security Setup

```python
from fastapi import FastAPI
from security import setup_all_security

app = FastAPI()

# Setup all security components
setup_all_security(
    app,
    environment="production",
    enable_rate_limiting=True,
    enable_cors=True,
    enable_security_headers=True,
    enable_audit_logging=True,
    redis_url="redis://localhost:6379"
)
```

### Manual Setup

```python
from fastapi import FastAPI
from security import (
    init_rate_limiter,
    setup_cors,
    setup_security_headers,
    init_audit_logger,
    RateLimitMiddleware,
    SecurityHeadersMiddleware
)

app = FastAPI()

# 1. Initialize components
init_audit_logger()
init_rate_limiter(redis_url="redis://localhost:6379")

# 2. Setup CORS
setup_cors(app, environment="production")

# 3. Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# 4. Add security headers middleware
setup_security_headers(app, enable_csp=True, enable_hsts=True)

# 5. Create protected routes
from security import get_current_user, require_roles
from fastapi import Depends

@app.get("/api/user/profile")
async def get_profile(user=Depends(get_current_user)):
    return {"username": user.username, "email": user.email}

@app.get("/api/admin/users")
async def list_users(user=Depends(require_roles(["admin"]))):
    return {"users": []}
```

---

## Authentication

### Creating Users

```python
from security import AuthManager

auth_manager = AuthManager()

# Create regular user
user = auth_manager.create_user(
    username="john_doe",
    password="SecurePass123!",
    email="john@example.com",
    full_name="John Doe",
    roles=["user"]
)

# Create admin user
admin = auth_manager.create_user(
    username="admin",
    password="AdminPass123!",
    email="admin@example.com",
    roles=["admin", "user"]
)
```

### API Key Management

```python
# Generate API key
api_key = auth_manager.api_key_auth.generate_api_key(
    username="john_doe",
    description="Production API key"
)
print(f"API Key: {api_key}")  # sk_<random_string>

# Validate API key
username = auth_manager.api_key_auth.validate_api_key(api_key)
if username:
    print(f"Valid key for user: {username}")

# List user's API keys
keys = auth_manager.api_key_auth.list_user_keys("john_doe")
for key_info in keys:
    print(f"Key: {key_info['key_prefix']}, Created: {key_info['created_at']}")

# Revoke API key
auth_manager.api_key_auth.revoke_api_key(api_key)
```

### JWT Token Flow

```python
# 1. User logs in
token = auth_manager.login("john_doe", "SecurePass123!")

# 2. Use access token for requests
# In route handler:
@app.get("/api/data")
async def get_data(user=Depends(get_current_user_jwt)):
    return {"data": "sensitive information"}

# 3. Refresh token when access token expires
new_token = auth_manager.jwt_auth.refresh_access_token(token.refresh_token)
```

### Role-Based Authorization

```python
from security import require_roles
from fastapi import Depends

# Require single role
@app.get("/api/user/dashboard")
async def user_dashboard(user=Depends(require_roles(["user"]))):
    return {"dashboard": "user data"}

# Require multiple roles (user must have ALL)
@app.get("/api/admin/settings")
async def admin_settings(user=Depends(require_roles(["admin", "superuser"]))):
    return {"settings": {}}

# Require any role (user must have AT LEAST ONE)
from security import get_current_user

@app.get("/api/moderator/reports")
async def view_reports(user=Depends(get_current_user)):
    if not any(role in user.roles for role in ["admin", "moderator"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"reports": []}
```

---

## Rate Limiting

### Configuration

```python
from security import init_rate_limiter, RateLimiter

# Initialize with Redis (production)
init_rate_limiter(redis_url="redis://localhost:6379")

# Or get limiter and configure manually
limiter = RateLimiter(
    default_limit=60,  # requests per minute
    burst_size=10,     # burst allowance
    endpoint_limits={
        "/api/chat": 30,
        "/api/search": 100,
        "/api/health": 1000
    }
)
```

### Application Methods

```python
from fastapi import FastAPI, Depends
from security import rate_limit_dependency, rate_limit

app = FastAPI()

# Method 1: Dependency (recommended)
@app.post("/api/chat")
async def chat(
    message: str,
    _rate_limit=Depends(rate_limit_dependency)
):
    return {"response": "processed"}

# Method 2: Decorator
@app.post("/api/search")
@rate_limit(requests_per_minute=100)
async def search(query: str):
    return {"results": []}

# Method 3: Custom limits per endpoint
@app.post("/api/expensive-operation")
@rate_limit(requests_per_minute=5, burst_size=2)
async def expensive_op():
    return {"status": "completed"}

# Method 4: Global middleware
from security import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)
```

### Response Headers

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1699123456
Retry-After: 15  (when rate limited)
```

### Checking Limits Programmatically

```python
from security import get_rate_limiter

limiter = get_rate_limiter()

# Check if request allowed
identifier = "192.168.1.1"  # IP address or API key
endpoint = "/api/chat"

allowed = await limiter.check_rate_limit(identifier, endpoint)
if not allowed:
    # Rate limited
    wait_time = limiter._get_wait_time(identifier, endpoint)
    print(f"Rate limited. Wait {wait_time} seconds")
```

---

## Security Headers

### Default Configuration

```python
from security import setup_security_headers

# Basic setup with defaults
setup_security_headers(app)
```

This applies:
- `Content-Security-Policy`: `default-src 'self'; script-src 'self' 'unsafe-inline'; ...`
- `Strict-Transport-Security`: `max-age=31536000; includeSubDomains; preload`
- `X-Frame-Options`: `DENY`
- `X-Content-Type-Options`: `nosniff`
- `X-XSS-Protection`: `1; mode=block`
- `Referrer-Policy`: `strict-origin-when-cross-origin`
- `Permissions-Policy`: `geolocation=(), microphone=(), camera=(), ...`

### Custom Configuration

```python
from security import SecurityHeadersMiddleware

app.add_middleware(
    SecurityHeadersMiddleware,
    enable_csp=True,
    enable_hsts=True,
    hsts_max_age=63072000,  # 2 years
    csp_directives={
        "default-src": ["'self'"],
        "script-src": [
            "'self'",
            "https://cdnjs.cloudflare.com",
            "'sha256-abc123...'"  # Allow specific inline scripts
        ],
        "style-src": ["'self'", "https://fonts.googleapis.com"],
        "img-src": ["'self'", "data:", "https:"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "connect-src": ["'self'", "https://api.example.com"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"]
    },
    frame_options="DENY",
    referrer_policy="no-referrer-when-downgrade"
)
```

### Environment-Specific Headers

```python
import os

environment = os.getenv("ENVIRONMENT", "development")

# HSTS only in production
enable_hsts = (environment == "production")

setup_security_headers(
    app,
    enable_csp=True,
    enable_hsts=enable_hsts
)
```

---

## Audit Logging

### Logging Security Events

```python
from security import get_audit_logger

audit_logger = get_audit_logger()

# Authentication events
audit_logger.log_login_success("john_doe", "192.168.1.1")
audit_logger.log_login_failure("john_doe", "192.168.1.1", "Invalid password")
audit_logger.log_logout("john_doe", "192.168.1.1")

# Authorization events
audit_logger.log_access_granted("john_doe", "/api/data", "GET", "192.168.1.1")
audit_logger.log_access_denied("john_doe", "/api/admin", "GET", "192.168.1.1", "Insufficient roles")

# API key events
audit_logger.log_api_key_created("john_doe", "sk_abc", "Production key", "192.168.1.1")
audit_logger.log_api_key_used("john_doe", "sk_abc", "/api/chat", "192.168.1.1")
audit_logger.log_api_key_revoked("john_doe", "sk_abc", "192.168.1.1", "Compromised")

# Security violations
audit_logger.log_rate_limit_exceeded("192.168.1.1", "/api/chat", 30, "192.168.1.1")
audit_logger.log_injection_attempt("sql", "' OR '1'='1", "192.168.1.1", "/api/search")
audit_logger.log_suspicious_activity(
    "Multiple failed login attempts",
    "192.168.1.1",
    details={"attempts": 5, "timespan": "60s"}
)
```

### Querying Audit Logs

```python
# Get user's recent activity
user_events = audit_logger.get_events_by_user("john_doe", limit=100)

# Get events by type
login_events = audit_logger.get_events_by_type(
    AuditEventType.LOGIN_SUCCESS,
    limit=50
)

# Get events from IP
ip_events = audit_logger.get_events_by_ip("192.168.1.1", limit=100)

# Get security violations
violations = audit_logger.get_security_violations(limit=100)

# Iterate and analyze
for event in violations:
    print(f"{event.timestamp}: {event.event_type} - {event.message}")
    print(f"  User: {event.username}, IP: {event.ip_address}")
    print(f"  Severity: {event.severity}")
```

### Integration with Middleware

```python
from fastapi import Request
from security import get_audit_logger

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    audit_logger = get_audit_logger()
    
    # Get user if authenticated
    user = getattr(request.state, "user", None)
    username = user.username if user else None
    
    # Log access
    audit_logger.log_access_granted(
        username=username,
        endpoint=request.url.path,
        method=request.method,
        ip_address=request.client.host
    )
    
    response = await call_next(request)
    return response
```

---

## CORS Configuration

### Environment-Based Setup

```python
from security import setup_cors

# Development
setup_cors(app, environment="development")
# Allows: http://localhost:*, http://127.0.0.1:*

# Staging
setup_cors(app, environment="staging")
# Allows: https://staging*.example.com

# Production
setup_cors(app, environment="production")
# Allows: https://example.com, https://www.example.com, https://app.example.com
```

### Custom Origins

```python
setup_cors(
    app,
    allowed_origins=[
        "https://app.example.com",
        "https://admin.example.com",
        "https://mobile.example.com"
    ],
    allow_credentials=True
)
```

### Dynamic Origin Patterns

```python
from security import setup_dynamic_cors

# Support wildcard subdomains
setup_dynamic_cors(
    app,
    allowed_origin_patterns=[
        "https://*.example.com",
        "https://example.com",
        "https://*.staging.example.com"
    ],
    allow_credentials=True
)
```

### Environment Variable Configuration

```bash
# .env file
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS=https://app.example.com,https://www.example.com
```

```python
import os
from security import setup_cors

# Auto-loads from environment
setup_cors(app)
```

---

## Best Practices

### 1. Environment Variables

Store secrets in environment variables, never in code:

```bash
# .env
SECRET_KEY=<strong-random-key-minimum-32-characters>
REDIS_URL=redis://localhost:6379
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS=https://app.example.com
```

```python
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise ValueError("SECRET_KEY must be at least 32 characters")
```

### 2. Rate Limiting Strategy

- **Public endpoints**: 30-60 RPM
- **Authenticated endpoints**: 60-100 RPM
- **Expensive operations**: 5-10 RPM
- **Health checks**: 1000 RPM
- **Search/read operations**: 100-200 RPM
- **Write operations**: 30-60 RPM

### 3. Authentication Strategy

**Use API keys for:**
- Server-to-server communication
- Long-lived automation scripts
- Third-party integrations
- CLI tools

**Use JWT tokens for:**
- User sessions (web/mobile)
- Short-lived access
- Frontend applications
- Microservice communication

### 4. Role Design

```python
# Good: Hierarchical roles
roles = ["user", "moderator", "admin", "superuser"]

# Better: Granular permissions
roles = [
    "user",
    "can_create_posts",
    "can_moderate_content",
    "can_manage_users",
    "admin"
]
```

### 5. Audit Log Retention

```python
# Keep last N events in memory
audit_logger.max_events = 10000

# Persist to database or file for long-term storage
import json

def save_audit_logs():
    events = audit_logger.events
    with open("audit_logs.jsonl", "a") as f:
        for event in events:
            f.write(json.dumps(event.dict()) + "\n")

# Run periodically
import schedule
schedule.every(1).hour.do(save_audit_logs)
```

### 6. Security Headers

- **Always enable** CSP, X-Frame-Options, X-Content-Type-Options
- **Production only**: HSTS (can't be disabled once set)
- **Avoid** `'unsafe-inline'` and `'unsafe-eval'` in CSP
- **Use nonces** or hashes for inline scripts/styles

### 7. Password Requirements

```python
import re

def validate_password(password: str) -> bool:
    """
    Password must:
    - Be at least 12 characters
    - Contain uppercase and lowercase
    - Contain at least one number
    - Contain at least one special character
    """
    if len(password) < 12:
        return False
    
    if not re.search(r'[A-Z]', password):
        return False
    
    if not re.search(r'[a-z]', password):
        return False
    
    if not re.search(r'\d', password):
        return False
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    
    return True
```

### 8. API Key Rotation

```python
# Rotate API keys every 90 days
from datetime import datetime, timedelta

def check_key_expiration(api_key: str, days: int = 90):
    key_info = auth_manager.api_key_auth.api_keys.get(api_key)
    if not key_info:
        return False
    
    created_at = key_info["created_at"]
    age = datetime.utcnow() - created_at
    
    if age > timedelta(days=days):
        # Send rotation reminder
        send_email(
            to=key_info["username"],
            subject="API Key Rotation Required",
            body=f"Your API key created on {created_at} should be rotated."
        )
        return True
    
    return False
```

---

## Troubleshooting

### Rate Limiting Issues

**Problem**: Rate limits too strict
```python
# Solution: Adjust limits per endpoint
from security import get_rate_limiter

limiter = get_rate_limiter()
limiter.endpoint_limits["/api/chat"] = 100  # Increase from 30 to 100 RPM
```

**Problem**: Redis connection failures
```python
# Solution: Rate limiter falls back to in-memory automatically
# Check Redis connectivity:
import redis.asyncio as redis

try:
    r = await redis.from_url("redis://localhost:6379")
    await r.ping()
    print("Redis connected")
except Exception as e:
    print(f"Redis error: {e}")
    # In-memory rate limiting will be used
```

### Authentication Issues

**Problem**: JWT token expired
```python
# Solution: Use refresh token
new_token = auth_manager.jwt_auth.refresh_access_token(refresh_token)
```

**Problem**: API key not working
```python
# Solution: Check key format and validity
api_key = "sk_your_key_here"

# Must start with "sk_"
assert api_key.startswith("sk_")

# Validate
username = auth_manager.api_key_auth.validate_api_key(api_key)
if not username:
    print("Invalid or revoked API key")
```

**Problem**: CORS preflight failures
```python
# Solution: Ensure OPTIONS method is allowed
setup_cors(
    app,
    allowed_origins=["https://app.example.com"],
    allow_credentials=True,
    allowed_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Include OPTIONS
    allowed_headers=["Content-Type", "Authorization", "X-API-Key"]
)
```

### Security Header Issues

**Problem**: CSP blocking resources
```python
# Solution: Add trusted sources to CSP directives
app.add_middleware(
    SecurityHeadersMiddleware,
    csp_directives={
        "default-src": ["'self'"],
        "script-src": ["'self'", "https://trusted-cdn.com"],
        "img-src": ["'self'", "data:", "https:"],
    }
)
```

**Problem**: HSTS causing issues in development
```python
# Solution: Only enable HSTS in production
import os

enable_hsts = os.getenv("ENVIRONMENT") == "production"
setup_security_headers(app, enable_hsts=enable_hsts)
```

### Audit Logging Issues

**Problem**: Too many logs
```python
# Solution: Adjust severity levels
audit_logger.logger.setLevel(logging.WARNING)  # Only WARNING and above

# Or filter specific event types
from security import AuditEventType

# Don't log DEBUG events
audit_logger.log_access_granted(...)  # Uses DEBUG severity, won't log
```

**Problem**: Need to export logs
```python
# Solution: Export to file
import json

events = audit_logger.events
with open("security_audit.json", "w") as f:
    json.dump([e.dict() for e in events], f, indent=2, default=str)
```

---

## Testing Security

### Test Authentication

```python
import pytest
from fastapi.testclient import TestClient

def test_api_key_authentication(client: TestClient, auth_manager: AuthManager):
    # Create user and API key
    auth_manager.create_user("test_user", "password", "test@example.com")
    api_key = auth_manager.api_key_auth.generate_api_key("test_user", "Test key")
    
    # Test with API key
    response = client.get(
        "/api/protected",
        headers={"X-API-Key": api_key}
    )
    assert response.status_code == 200

def test_jwt_authentication(client: TestClient, auth_manager: AuthManager):
    # Create user and login
    auth_manager.create_user("test_user", "password", "test@example.com")
    token = auth_manager.login("test_user", "password")
    
    # Test with JWT
    response = client.get(
        "/api/protected",
        headers={"Authorization": f"Bearer {token.access_token}"}
    )
    assert response.status_code == 200
```

### Test Rate Limiting

```python
def test_rate_limiting(client: TestClient):
    # Make requests until rate limited
    responses = []
    for i in range(100):
        response = client.get("/api/chat")
        responses.append(response)
    
    # Should eventually get 429
    assert any(r.status_code == 429 for r in responses)
    
    # Check headers
    limited_response = [r for r in responses if r.status_code == 429][0]
    assert "Retry-After" in limited_response.headers
```

### Test Security Headers

```python
def test_security_headers(client: TestClient):
    response = client.get("/")
    
    assert "Content-Security-Policy" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
```

---

## Summary

The security layer provides enterprise-grade protection through:

✅ **Input Validation**: Prevent injection attacks  
✅ **Rate Limiting**: Prevent abuse and DOS  
✅ **Authentication**: Dual API key + JWT system  
✅ **Authorization**: Role-based access control  
✅ **Security Headers**: Comprehensive protection  
✅ **Audit Logging**: Complete event tracking  
✅ **CORS**: Secure cross-origin requests  

For issues or questions, refer to the troubleshooting section or check audit logs for detailed security event information.
