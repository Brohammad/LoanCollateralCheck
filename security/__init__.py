"""
Security Module

Comprehensive security implementation including:
- Input validation and sanitization
- Rate limiting (token bucket + Redis)
- Authentication (API keys + JWT)
- Authorization (RBAC)
- Security headers
- Audit logging
- CORS configuration
"""

from .validation import (
    InputValidator,
    UserMessageRequest,
    RAGSearchRequest,
    SessionRequest,
    CandidateSearchRequest,
    FeedbackRequest,
    ConfigUpdateRequest,
    StandardResponse,
    ErrorResponse,
    ValidationErrorResponse
)

from .rate_limiter import (
    TokenBucket,
    RateLimiter,
    RateLimitMiddleware,
    get_rate_limiter,
    init_rate_limiter,
    rate_limit_dependency,
    rate_limit
)

from .auth import (
    APIKeyAuth,
    JWTAuth,
    AuthManager,
    User,
    TokenData,
    Token,
    get_current_user,
    get_current_user_api_key,
    get_current_user_jwt,
    require_roles,
    require_api_key,
    pwd_context,
    api_key_header,
    bearer_scheme
)

from .headers import (
    SecurityHeadersMiddleware,
    CORSSecurityMiddleware,
    RequestValidationMiddleware,
    setup_security_headers
)

from .audit import (
    AuditEventType,
    AuditSeverity,
    AuditEvent,
    AuditLogger,
    get_audit_logger,
    init_audit_logger
)

from .cors import (
    CORSConfig,
    DynamicCORSMiddleware,
    setup_cors,
    setup_dynamic_cors,
    get_cors_config,
    DEVELOPMENT_CORS,
    STAGING_CORS,
    PRODUCTION_CORS
)

__all__ = [
    # Validation
    "InputValidator",
    "UserMessageRequest",
    "RAGSearchRequest",
    "SessionRequest",
    "CandidateSearchRequest",
    "FeedbackRequest",
    "ConfigUpdateRequest",
    "StandardResponse",
    "ErrorResponse",
    "ValidationErrorResponse",
    
    # Rate Limiting
    "TokenBucket",
    "RateLimiter",
    "RateLimitMiddleware",
    "get_rate_limiter",
    "init_rate_limiter",
    "rate_limit_dependency",
    "rate_limit",
    
    # Authentication
    "APIKeyAuth",
    "JWTAuth",
    "AuthManager",
    "User",
    "TokenData",
    "Token",
    "get_current_user",
    "get_current_user_api_key",
    "get_current_user_jwt",
    "require_roles",
    "require_api_key",
    "pwd_context",
    "api_key_header",
    "bearer_scheme",
    
    # Security Headers
    "SecurityHeadersMiddleware",
    "CORSSecurityMiddleware",
    "RequestValidationMiddleware",
    "setup_security_headers",
    
    # Audit Logging
    "AuditEventType",
    "AuditSeverity",
    "AuditEvent",
    "AuditLogger",
    "get_audit_logger",
    "init_audit_logger",
    
    # CORS
    "CORSConfig",
    "DynamicCORSMiddleware",
    "setup_cors",
    "setup_dynamic_cors",
    "get_cors_config",
    "DEVELOPMENT_CORS",
    "STAGING_CORS",
    "PRODUCTION_CORS",
]


def setup_all_security(
    app,
    environment: str = "development",
    enable_rate_limiting: bool = True,
    enable_cors: bool = True,
    enable_security_headers: bool = True,
    enable_audit_logging: bool = True,
    redis_url: str = None
):
    """
    Setup all security components on FastAPI app
    
    Args:
        app: FastAPI application
        environment: Environment (development, staging, production)
        enable_rate_limiting: Enable rate limiting
        enable_cors: Enable CORS
        enable_security_headers: Enable security headers
        enable_audit_logging: Enable audit logging
        redis_url: Redis URL for rate limiting
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Initialize audit logging
    if enable_audit_logging:
        init_audit_logger()
        logger.info("Audit logging initialized")
    
    # Setup rate limiting
    if enable_rate_limiting:
        init_rate_limiter(redis_url=redis_url)
        logger.info("Rate limiting initialized")
    
    # Setup CORS
    if enable_cors:
        setup_cors(app, environment=environment)
        logger.info("CORS configured")
    
    # Setup security headers
    if enable_security_headers:
        setup_security_headers(
            app,
            enable_csp=True,
            enable_hsts=(environment == "production")
        )
        logger.info("Security headers configured")
    
    logger.info(f"All security components initialized for {environment} environment")
