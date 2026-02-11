"""
Security Headers Middleware

Implements security headers to protect against common web vulnerabilities:
- Content Security Policy (CSP)
- X-Frame-Options
- X-Content-Type-Options
- Strict-Transport-Security (HSTS)
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy
"""

from typing import Dict, Optional, List
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    
    Protects against:
    - Clickjacking
    - XSS attacks
    - MIME type sniffing
    - Information disclosure
    - Man-in-the-middle attacks
    """
    
    def __init__(
        self,
        app,
        enable_csp: bool = True,
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        csp_directives: Optional[Dict[str, List[str]]] = None,
        frame_options: str = "DENY",
        referrer_policy: str = "strict-origin-when-cross-origin"
    ):
        """
        Initialize security headers middleware
        
        Args:
            app: FastAPI application
            enable_csp: Enable Content Security Policy
            enable_hsts: Enable HTTP Strict Transport Security
            hsts_max_age: HSTS max age in seconds
            csp_directives: Custom CSP directives
            frame_options: X-Frame-Options value
            referrer_policy: Referrer-Policy value
        """
        super().__init__(app)
        self.enable_csp = enable_csp
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.frame_options = frame_options
        self.referrer_policy = referrer_policy
        
        # Default CSP directives
        self.csp_directives = csp_directives or {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-inline'"],  # Consider removing unsafe-inline
            "style-src": ["'self'", "'unsafe-inline'"],   # Consider removing unsafe-inline
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'", "data:"],
            "connect-src": ["'self'"],
            "frame-ancestors": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
        }
    
    def _build_csp_header(self) -> str:
        """
        Build Content Security Policy header value
        
        Returns:
            CSP header value
        """
        directives = []
        for directive, values in self.csp_directives.items():
            values_str = " ".join(values)
            directives.append(f"{directive} {values_str}")
        
        return "; ".join(directives)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and add security headers to response
        
        Args:
            request: Incoming request
            call_next: Next middleware/route handler
            
        Returns:
            Response with security headers
        """
        response = await call_next(request)
        
        # Content Security Policy
        if self.enable_csp:
            csp_value = self._build_csp_header()
            response.headers["Content-Security-Policy"] = csp_value
        
        # X-Frame-Options (prevent clickjacking)
        response.headers["X-Frame-Options"] = self.frame_options
        
        # X-Content-Type-Options (prevent MIME sniffing)
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection (legacy, CSP is better)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy (control referrer information)
        response.headers["Referrer-Policy"] = self.referrer_policy
        
        # Permissions-Policy (restrict browser features)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        # Strict-Transport-Security (enforce HTTPS)
        if self.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )
        
        # X-Permitted-Cross-Domain-Policies (Adobe Flash/PDF)
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # Cross-Origin-Opener-Policy (isolation)
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        
        # Cross-Origin-Resource-Policy (resource isolation)
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # Cross-Origin-Embedder-Policy (additional isolation)
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        
        # Remove server identification header
        if "server" in response.headers:
            del response.headers["server"]
        
        # Remove X-Powered-By if present
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]
        
        return response


class CORSSecurityMiddleware:
    """
    Secure CORS middleware with additional validation
    
    More restrictive than standard CORS middleware
    """
    
    def __init__(
        self,
        app,
        allowed_origins: List[str],
        allowed_methods: List[str] = None,
        allowed_headers: List[str] = None,
        expose_headers: List[str] = None,
        max_age: int = 600,
        allow_credentials: bool = False
    ):
        """
        Initialize CORS security middleware
        
        Args:
            app: FastAPI application
            allowed_origins: List of allowed origins
            allowed_methods: List of allowed HTTP methods
            allowed_headers: List of allowed headers
            expose_headers: List of exposed headers
            max_age: Preflight cache duration
            allow_credentials: Allow credentials
        """
        self.app = app
        self.allowed_origins = set(allowed_origins)
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = allowed_headers or ["Content-Type", "Authorization", "X-API-Key"]
        self.expose_headers = expose_headers or ["X-RateLimit-Limit", "X-RateLimit-Remaining"]
        self.max_age = max_age
        self.allow_credentials = allow_credentials
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """
        Check if origin is allowed
        
        Args:
            origin: Request origin
            
        Returns:
            True if allowed
        """
        if "*" in self.allowed_origins:
            return True
        
        return origin in self.allowed_origins
    
    async def __call__(self, scope, receive, send):
        """Handle CORS"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Get origin from headers
        headers_dict = dict(scope.get("headers", []))
        origin = headers_dict.get(b"origin", b"").decode()
        
        async def send_with_cors_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                
                # Check if origin is allowed
                if origin and self._is_origin_allowed(origin):
                    # Add CORS headers
                    headers[b"access-control-allow-origin"] = origin.encode()
                    
                    if self.allow_credentials:
                        headers[b"access-control-allow-credentials"] = b"true"
                    
                    if self.expose_headers:
                        expose = ", ".join(self.expose_headers)
                        headers[b"access-control-expose-headers"] = expose.encode()
                
                message["headers"] = list(headers.items())
            
            await send(message)
        
        # Handle preflight requests
        if scope["method"] == "OPTIONS":
            if origin and self._is_origin_allowed(origin):
                response_headers = [
                    (b"access-control-allow-origin", origin.encode()),
                    (b"access-control-allow-methods", ", ".join(self.allowed_methods).encode()),
                    (b"access-control-allow-headers", ", ".join(self.allowed_headers).encode()),
                    (b"access-control-max-age", str(self.max_age).encode()),
                ]
                
                if self.allow_credentials:
                    response_headers.append((b"access-control-allow-credentials", b"true"))
                
                await send({
                    "type": "http.response.start",
                    "status": 204,
                    "headers": response_headers,
                })
                await send({"type": "http.response.body", "body": b""})
                return
        
        await self.app(scope, receive, send_with_cors_headers)


def setup_security_headers(
    app,
    enable_csp: bool = True,
    enable_hsts: bool = True,
    enable_cors: bool = False,
    allowed_origins: List[str] = None
):
    """
    Setup security headers middleware
    
    Args:
        app: FastAPI application
        enable_csp: Enable Content Security Policy
        enable_hsts: Enable HSTS
        enable_cors: Enable CORS
        allowed_origins: Allowed CORS origins
    """
    # Add security headers middleware
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_csp=enable_csp,
        enable_hsts=enable_hsts
    )
    
    # Add CORS middleware if enabled
    if enable_cors and allowed_origins:
        app.add_middleware(
            CORSSecurityMiddleware,
            allowed_origins=allowed_origins,
            allow_credentials=False  # More secure default
        )
    
    logger.info("Security headers middleware configured")


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for validating request properties
    
    Protects against:
    - Oversized requests
    - Invalid content types
    - Malformed requests
    """
    
    def __init__(
        self,
        app,
        max_body_size: int = 10 * 1024 * 1024,  # 10 MB
        allowed_content_types: List[str] = None
    ):
        """
        Initialize request validation middleware
        
        Args:
            app: FastAPI application
            max_body_size: Maximum request body size in bytes
            allowed_content_types: List of allowed content types
        """
        super().__init__(app)
        self.max_body_size = max_body_size
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Validate request before processing
        
        Args:
            request: Incoming request
            call_next: Next middleware/route handler
            
        Returns:
            Response or error
        """
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_body_size:
                    return Response(
                        content=f"Request body too large. Maximum size: {self.max_body_size} bytes",
                        status_code=413
                    )
            except ValueError:
                return Response(
                    content="Invalid Content-Length header",
                    status_code=400
                )
        
        # Check content type for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            
            if content_type and not any(
                allowed in content_type
                for allowed in self.allowed_content_types
            ):
                return Response(
                    content=f"Content-Type not allowed. Allowed types: {', '.join(self.allowed_content_types)}",
                    status_code=415
                )
        
        response = await call_next(request)
        return response
