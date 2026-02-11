"""
Rate Limiter for API Endpoints

Implements token bucket rate limiting with:
- Per-IP rate limiting
- Per-API-key rate limiting
- Sliding window algorithm
- Redis backend support (with in-memory fallback)
- Configurable limits per endpoint
- Rate limit headers in responses
"""

import time
from typing import Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from functools import wraps
import logging

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False otherwise
        """
        async with self.lock:
            # Refill tokens based on time elapsed
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + (elapsed * self.refill_rate)
            )
            self.last_refill = now
            
            # Try to consume tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Calculate wait time until tokens are available
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Wait time in seconds
        """
        if self.tokens >= tokens:
            return 0.0
        
        needed = tokens - self.tokens
        return needed / self.refill_rate


class RateLimiter:
    """
    Rate limiter with multiple strategies
    
    Supports:
    - IP-based rate limiting
    - API key-based rate limiting
    - Endpoint-specific limits
    - Sliding window algorithm
    """
    
    def __init__(
        self,
        default_requests_per_minute: int = 60,
        default_burst: int = 10,
        enable_redis: bool = False,
        redis_url: Optional[str] = None
    ):
        """
        Initialize rate limiter
        
        Args:
            default_requests_per_minute: Default rate limit
            default_burst: Default burst capacity
            enable_redis: Use Redis for distributed rate limiting
            redis_url: Redis connection URL
        """
        self.default_rpm = default_requests_per_minute
        self.default_burst = default_burst
        self.enable_redis = enable_redis
        self.redis_url = redis_url
        
        # In-memory storage (fallback or primary)
        self.buckets: Dict[str, TokenBucket] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
        
        # Endpoint-specific limits
        self.endpoint_limits: Dict[str, Tuple[int, int]] = {
            # endpoint: (requests_per_minute, burst)
            "/api/chat": (30, 5),
            "/api/search": (100, 20),
            "/api/health": (1000, 100),
            "/api/history": (60, 10),
        }
        
        # Redis client (if enabled)
        self.redis_client = None
        if enable_redis:
            try:
                import redis.asyncio as redis
                self.redis_client = redis.from_url(redis_url or "redis://localhost:6379")
                logger.info("Redis rate limiting enabled")
            except ImportError:
                logger.warning("Redis not available, using in-memory rate limiting")
                self.enable_redis = False
    
    def _get_bucket_key(self, request: Request) -> str:
        """
        Get unique key for rate limit bucket
        
        Args:
            request: FastAPI request object
            
        Returns:
            Unique bucket key
        """
        # Prefer API key if available
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def _get_limits(self, request: Request) -> Tuple[int, int]:
        """
        Get rate limits for endpoint
        
        Args:
            request: FastAPI request object
            
        Returns:
            Tuple of (requests_per_minute, burst)
        """
        path = request.url.path
        
        # Check for exact match
        if path in self.endpoint_limits:
            return self.endpoint_limits[path]
        
        # Check for prefix match
        for endpoint, limits in self.endpoint_limits.items():
            if path.startswith(endpoint):
                return limits
        
        return (self.default_rpm, self.default_burst)
    
    async def _cleanup_old_buckets(self):
        """Remove stale buckets to prevent memory leaks"""
        if time.time() - self.last_cleanup < self.cleanup_interval:
            return
        
        self.last_cleanup = time.time()
        
        # Remove buckets older than 10 minutes
        cutoff = time.time() - 600
        old_keys = [
            key for key, bucket in self.buckets.items()
            if bucket.last_refill < cutoff
        ]
        
        for key in old_keys:
            del self.buckets[key]
        
        if old_keys:
            logger.info(f"Cleaned up {len(old_keys)} stale rate limit buckets")
    
    async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict[str, str]]:
        """
        Check if request is within rate limits
        
        Args:
            request: FastAPI request object
            
        Returns:
            Tuple of (is_allowed, headers)
        """
        bucket_key = self._get_bucket_key(request)
        rpm, burst = self._get_limits(request)
        
        # Calculate refill rate (tokens per second)
        refill_rate = rpm / 60.0
        
        # Get or create bucket
        if bucket_key not in self.buckets:
            self.buckets[bucket_key] = TokenBucket(burst, refill_rate)
        
        bucket = self.buckets[bucket_key]
        
        # Try to consume a token
        allowed = await bucket.consume(1)
        
        # Calculate rate limit headers
        headers = {
            "X-RateLimit-Limit": str(rpm),
            "X-RateLimit-Remaining": str(int(bucket.tokens)),
            "X-RateLimit-Reset": str(int(time.time() + bucket.get_wait_time(1))),
        }
        
        if not allowed:
            retry_after = int(bucket.get_wait_time(1)) + 1
            headers["Retry-After"] = str(retry_after)
        
        # Periodic cleanup
        await self._cleanup_old_buckets()
        
        return allowed, headers
    
    async def check_rate_limit_redis(self, request: Request) -> Tuple[bool, Dict[str, str]]:
        """
        Check rate limit using Redis (distributed)
        
        Args:
            request: FastAPI request object
            
        Returns:
            Tuple of (is_allowed, headers)
        """
        if not self.redis_client:
            return await self.check_rate_limit(request)
        
        bucket_key = self._get_bucket_key(request)
        rpm, burst = self._get_limits(request)
        
        now = time.time()
        window = 60  # 1 minute window
        
        try:
            # Sliding window counter
            key = f"rate_limit:{bucket_key}"
            
            # Remove old entries
            await self.redis_client.zremrangebyscore(key, 0, now - window)
            
            # Count requests in current window
            count = await self.redis_client.zcard(key)
            
            headers = {
                "X-RateLimit-Limit": str(rpm),
                "X-RateLimit-Remaining": str(max(0, rpm - count)),
                "X-RateLimit-Reset": str(int(now + window)),
            }
            
            if count >= rpm:
                headers["Retry-After"] = str(window)
                return False, headers
            
            # Add current request
            await self.redis_client.zadd(key, {str(now): now})
            await self.redis_client.expire(key, window)
            
            headers["X-RateLimit-Remaining"] = str(max(0, rpm - count - 1))
            return True, headers
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}, falling back to in-memory")
            return await self.check_rate_limit(request)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def init_rate_limiter(
    requests_per_minute: int = 60,
    burst: int = 10,
    enable_redis: bool = False,
    redis_url: Optional[str] = None
):
    """
    Initialize global rate limiter
    
    Args:
        requests_per_minute: Default rate limit
        burst: Default burst capacity
        enable_redis: Use Redis for distributed limiting
        redis_url: Redis connection URL
    """
    global _rate_limiter
    _rate_limiter = RateLimiter(
        default_requests_per_minute=requests_per_minute,
        default_burst=burst,
        enable_redis=enable_redis,
        redis_url=redis_url
    )
    logger.info(f"Rate limiter initialized: {requests_per_minute} RPM, burst={burst}")


async def rate_limit_dependency(request: Request):
    """
    FastAPI dependency for rate limiting
    
    Usage:
        @app.get("/api/endpoint", dependencies=[Depends(rate_limit_dependency)])
    """
    limiter = get_rate_limiter()
    
    if limiter.enable_redis:
        allowed, headers = await limiter.check_rate_limit_redis(request)
    else:
        allowed, headers = await limiter.check_rate_limit(request)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers=headers
        )
    
    # Add rate limit headers to response (will be picked up by middleware)
    request.state.rate_limit_headers = headers


def rate_limit(
    requests_per_minute: Optional[int] = None,
    burst: Optional[int] = None
):
    """
    Decorator for rate limiting endpoints
    
    Args:
        requests_per_minute: Override default rate limit
        burst: Override default burst capacity
    
    Usage:
        @rate_limit(requests_per_minute=30, burst=5)
        async def my_endpoint():
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                logger.warning("No request object found for rate limiting")
                return await func(*args, **kwargs)
            
            # Check rate limit
            limiter = get_rate_limiter()
            
            # Temporarily override limits if specified
            original_limits = None
            if requests_per_minute or burst:
                path = request.url.path
                original_limits = limiter.endpoint_limits.get(path)
                rpm = requests_per_minute or limiter.default_rpm
                b = burst or limiter.default_burst
                limiter.endpoint_limits[path] = (rpm, b)
            
            try:
                if limiter.enable_redis:
                    allowed, headers = await limiter.check_rate_limit_redis(request)
                else:
                    allowed, headers = await limiter.check_rate_limit(request)
                
                if not allowed:
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Rate limit exceeded"},
                        headers=headers
                    )
                
                # Store headers for middleware to add to response
                request.state.rate_limit_headers = headers
                
                return await func(*args, **kwargs)
                
            finally:
                # Restore original limits
                if original_limits:
                    limiter.endpoint_limits[path] = original_limits
                elif requests_per_minute or burst:
                    limiter.endpoint_limits.pop(path, None)
        
        return wrapper
    return decorator


class RateLimitMiddleware:
    """Middleware to add rate limit headers to all responses"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                # Add rate limit headers if present
                headers = dict(message.get("headers", []))
                
                # Check if request has rate limit headers
                if hasattr(scope.get("state"), "rate_limit_headers"):
                    rate_headers = scope["state"].rate_limit_headers
                    for key, value in rate_headers.items():
                        headers[key.lower().encode()] = value.encode()
                    
                    message["headers"] = list(headers.items())
            
            await send(message)
        
        await self.app(scope, receive, send_with_headers)
