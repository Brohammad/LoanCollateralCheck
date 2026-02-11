"""
CORS Configuration

Secure Cross-Origin Resource Sharing (CORS) configuration for the API.

Provides:
- Environment-specific origin whitelisting
- Credential handling
- Method and header restrictions
- Preflight caching
"""

from typing import List, Optional
import os
import logging

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

logger = logging.getLogger(__name__)


class CORSConfig:
    """CORS configuration"""
    
    def __init__(
        self,
        environment: str = "development",
        allowed_origins: Optional[List[str]] = None,
        allow_credentials: bool = False,
        allowed_methods: Optional[List[str]] = None,
        allowed_headers: Optional[List[str]] = None,
        expose_headers: Optional[List[str]] = None,
        max_age: int = 600
    ):
        """
        Initialize CORS configuration
        
        Args:
            environment: Environment (development, staging, production)
            allowed_origins: List of allowed origins
            allow_credentials: Allow credentials
            allowed_methods: Allowed HTTP methods
            allowed_headers: Allowed request headers
            expose_headers: Headers to expose to browser
            max_age: Preflight cache duration in seconds
        """
        self.environment = environment
        self.allow_credentials = allow_credentials
        self.max_age = max_age
        
        # Set allowed origins based on environment
        if allowed_origins:
            self.allowed_origins = allowed_origins
        else:
            self.allowed_origins = self._get_default_origins()
        
        # Set allowed methods
        self.allowed_methods = allowed_methods or [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "OPTIONS",
            "PATCH"
        ]
        
        # Set allowed headers
        self.allowed_headers = allowed_headers or [
            "Accept",
            "Accept-Language",
            "Content-Type",
            "Content-Language",
            "Authorization",
            "X-API-Key",
            "X-Request-ID",
            "X-Session-ID"
        ]
        
        # Set exposed headers
        self.expose_headers = expose_headers or [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
            "X-Request-ID"
        ]
    
    def _get_default_origins(self) -> List[str]:
        """
        Get default allowed origins based on environment
        
        Returns:
            List of allowed origins
        """
        if self.environment == "production":
            # Production: Only allow specific domains
            origins = [
                "https://yourdomain.com",
                "https://www.yourdomain.com",
                "https://app.yourdomain.com",
            ]
        elif self.environment == "staging":
            # Staging: Allow staging domains
            origins = [
                "https://staging.yourdomain.com",
                "https://staging-app.yourdomain.com",
            ]
        else:
            # Development: Allow localhost
            origins = [
                "http://localhost",
                "http://localhost:3000",
                "http://localhost:8000",
                "http://localhost:8080",
                "http://127.0.0.1",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
                "http://127.0.0.1:8080",
            ]
        
        # Allow environment variable overrides
        env_origins = os.getenv("CORS_ALLOWED_ORIGINS")
        if env_origins:
            additional_origins = [o.strip() for o in env_origins.split(",")]
            origins.extend(additional_origins)
        
        return origins
    
    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary for FastAPI middleware
        
        Returns:
            Configuration dictionary
        """
        return {
            "allow_origins": self.allowed_origins,
            "allow_credentials": self.allow_credentials,
            "allow_methods": self.allowed_methods,
            "allow_headers": self.allowed_headers,
            "expose_headers": self.expose_headers,
            "max_age": self.max_age
        }


def setup_cors(
    app: FastAPI,
    environment: str = None,
    allowed_origins: List[str] = None,
    allow_credentials: bool = False
):
    """
    Setup CORS middleware on FastAPI app
    
    Args:
        app: FastAPI application
        environment: Environment (development, staging, production)
        allowed_origins: Custom allowed origins
        allow_credentials: Allow credentials
    """
    # Get environment from env var if not provided
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")
    
    # Create CORS configuration
    cors_config = CORSConfig(
        environment=environment,
        allowed_origins=allowed_origins,
        allow_credentials=allow_credentials
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        **cors_config.to_dict()
    )
    
    logger.info(
        f"CORS configured for {environment} environment with origins: "
        f"{', '.join(cors_config.allowed_origins[:3])}..."
    )


class DynamicCORSMiddleware:
    """
    Dynamic CORS middleware with runtime origin validation
    
    More flexible than static origin list, validates origins against patterns
    """
    
    def __init__(
        self,
        app,
        allowed_origin_patterns: List[str],
        allow_credentials: bool = False,
        allowed_methods: List[str] = None,
        allowed_headers: List[str] = None,
        max_age: int = 600
    ):
        """
        Initialize dynamic CORS middleware
        
        Args:
            app: FastAPI application
            allowed_origin_patterns: List of origin patterns (supports wildcards)
            allow_credentials: Allow credentials
            allowed_methods: Allowed HTTP methods
            allowed_headers: Allowed headers
            max_age: Preflight cache duration
        """
        self.app = app
        self.allowed_origin_patterns = allowed_origin_patterns
        self.allow_credentials = allow_credentials
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = allowed_headers or ["*"]
        self.max_age = max_age
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """
        Check if origin matches allowed patterns
        
        Args:
            origin: Request origin
            
        Returns:
            True if origin is allowed
        """
        import re
        
        for pattern in self.allowed_origin_patterns:
            # Convert wildcard pattern to regex
            regex_pattern = pattern.replace(".", r"\.").replace("*", ".*")
            if re.match(f"^{regex_pattern}$", origin):
                return True
        
        return False
    
    async def __call__(self, scope, receive, send):
        """Handle CORS with dynamic origin validation"""
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
                    headers[b"access-control-allow-origin"] = origin.encode()
                    
                    if self.allow_credentials:
                        headers[b"access-control-allow-credentials"] = b"true"
                    
                    # Vary header for caching
                    headers[b"vary"] = b"Origin"
                
                message["headers"] = list(headers.items())
            
            await send(message)
        
        # Handle preflight
        if scope["method"] == "OPTIONS":
            if origin and self._is_origin_allowed(origin):
                headers = [
                    (b"access-control-allow-origin", origin.encode()),
                    (b"access-control-allow-methods", ", ".join(self.allowed_methods).encode()),
                    (b"access-control-allow-headers", ", ".join(self.allowed_headers).encode()),
                    (b"access-control-max-age", str(self.max_age).encode()),
                ]
                
                if self.allow_credentials:
                    headers.append((b"access-control-allow-credentials", b"true"))
                
                await send({
                    "type": "http.response.start",
                    "status": 204,
                    "headers": headers,
                })
                await send({"type": "http.response.body", "body": b""})
                return
        
        await self.app(scope, receive, send_with_cors_headers)


def setup_dynamic_cors(
    app: FastAPI,
    allowed_origin_patterns: List[str],
    allow_credentials: bool = False
):
    """
    Setup dynamic CORS middleware
    
    Args:
        app: FastAPI application
        allowed_origin_patterns: Origin patterns (e.g., ["https://*.yourdomain.com"])
        allow_credentials: Allow credentials
    """
    app.add_middleware(
        DynamicCORSMiddleware,
        allowed_origin_patterns=allowed_origin_patterns,
        allow_credentials=allow_credentials
    )
    
    logger.info(f"Dynamic CORS configured with patterns: {allowed_origin_patterns}")


# Predefined CORS configurations
DEVELOPMENT_CORS = CORSConfig(
    environment="development",
    allow_credentials=True
)

STAGING_CORS = CORSConfig(
    environment="staging",
    allow_credentials=True
)

PRODUCTION_CORS = CORSConfig(
    environment="production",
    allow_credentials=False  # More secure for production
)


def get_cors_config(environment: str = None) -> CORSConfig:
    """
    Get CORS configuration for environment
    
    Args:
        environment: Environment name
        
    Returns:
        CORSConfig instance
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")
    
    if environment == "production":
        return PRODUCTION_CORS
    elif environment == "staging":
        return STAGING_CORS
    else:
        return DEVELOPMENT_CORS
