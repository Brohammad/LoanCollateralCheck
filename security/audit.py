"""
Security Audit Logging

Comprehensive audit logging for security events including:
- Authentication events (login, logout, failures)
- Authorization failures
- API key operations
- Rate limit violations
- Security policy violations
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import traceback

from pydantic import BaseModel


# Configure audit logger
audit_logger = logging.getLogger("security.audit")
audit_logger.setLevel(logging.INFO)


class AuditEventType(str, Enum):
    """Audit event types"""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    
    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_VIOLATION = "permission_violation"
    ROLE_CHECK_FAILED = "role_check_failed"
    
    # API key events
    API_KEY_CREATED = "api_key_created"
    API_KEY_USED = "api_key_used"
    API_KEY_REVOKED = "api_key_revoked"
    API_KEY_INVALID = "api_key_invalid"
    
    # Rate limiting events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    RATE_LIMIT_WARNING = "rate_limit_warning"
    
    # Security violations
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    INVALID_INPUT = "invalid_input"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    COMMAND_INJECTION_ATTEMPT = "command_injection_attempt"
    
    # System events
    CONFIG_CHANGED = "config_changed"
    SECURITY_POLICY_UPDATED = "security_policy_updated"


class AuditSeverity(str, Enum):
    """Audit event severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    """Audit event model"""
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    username: Optional[str] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    message: str
    details: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AuditLogger:
    """
    Security audit logger
    
    Logs all security-relevant events with structured data
    """
    
    def __init__(self, logger: logging.Logger = None):
        """
        Initialize audit logger
        
        Args:
            logger: Custom logger instance
        """
        self.logger = logger or audit_logger
        self.events: List[AuditEvent] = []
        self.max_events = 10000  # Keep last N events in memory
    
    def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        message: str,
        username: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """
        Log an audit event
        
        Args:
            event_type: Type of event
            severity: Event severity
            message: Human-readable message
            username: Username if available
            user_id: User ID if available
            ip_address: Request IP address
            user_agent: User agent string
            endpoint: API endpoint
            method: HTTP method
            status_code: Response status code
            details: Additional event details
            session_id: Session identifier
            request_id: Request identifier
        """
        event = AuditEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            username=username,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            message=message,
            details=details or {},
            session_id=session_id,
            request_id=request_id
        )
        
        # Store in memory
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events.pop(0)
        
        # Log to file/stdout
        log_data = event.dict()
        
        # Map severity to log level
        if severity == AuditSeverity.DEBUG:
            self.logger.debug(json.dumps(log_data))
        elif severity == AuditSeverity.INFO:
            self.logger.info(json.dumps(log_data))
        elif severity == AuditSeverity.WARNING:
            self.logger.warning(json.dumps(log_data))
        elif severity == AuditSeverity.ERROR:
            self.logger.error(json.dumps(log_data))
        elif severity == AuditSeverity.CRITICAL:
            self.logger.critical(json.dumps(log_data))
    
    # Authentication event helpers
    def log_login_success(
        self,
        username: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log successful login"""
        self.log_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.INFO,
            message=f"User {username} logged in successfully",
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
    
    def log_login_failure(
        self,
        username: str,
        ip_address: str,
        reason: str,
        user_agent: Optional[str] = None
    ):
        """Log failed login attempt"""
        self.log_event(
            event_type=AuditEventType.LOGIN_FAILURE,
            severity=AuditSeverity.WARNING,
            message=f"Failed login attempt for user {username}: {reason}",
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"reason": reason}
        )
    
    def log_logout(
        self,
        username: str,
        ip_address: str,
        session_id: Optional[str] = None
    ):
        """Log user logout"""
        self.log_event(
            event_type=AuditEventType.LOGOUT,
            severity=AuditSeverity.INFO,
            message=f"User {username} logged out",
            username=username,
            ip_address=ip_address,
            session_id=session_id
        )
    
    def log_token_refresh(
        self,
        username: str,
        ip_address: str
    ):
        """Log token refresh"""
        self.log_event(
            event_type=AuditEventType.TOKEN_REFRESH,
            severity=AuditSeverity.INFO,
            message=f"Token refreshed for user {username}",
            username=username,
            ip_address=ip_address
        )
    
    def log_token_invalid(
        self,
        reason: str,
        ip_address: str,
        endpoint: Optional[str] = None
    ):
        """Log invalid token attempt"""
        self.log_event(
            event_type=AuditEventType.TOKEN_INVALID,
            severity=AuditSeverity.WARNING,
            message=f"Invalid token: {reason}",
            ip_address=ip_address,
            endpoint=endpoint,
            details={"reason": reason}
        )
    
    # Authorization event helpers
    def log_access_granted(
        self,
        username: str,
        endpoint: str,
        method: str,
        ip_address: str
    ):
        """Log successful authorization"""
        self.log_event(
            event_type=AuditEventType.ACCESS_GRANTED,
            severity=AuditSeverity.DEBUG,
            message=f"Access granted to {username} for {method} {endpoint}",
            username=username,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address
        )
    
    def log_access_denied(
        self,
        username: Optional[str],
        endpoint: str,
        method: str,
        ip_address: str,
        reason: str
    ):
        """Log failed authorization"""
        self.log_event(
            event_type=AuditEventType.ACCESS_DENIED,
            severity=AuditSeverity.WARNING,
            message=f"Access denied for {username or 'anonymous'} to {method} {endpoint}: {reason}",
            username=username,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            details={"reason": reason}
        )
    
    def log_permission_violation(
        self,
        username: str,
        required_roles: List[str],
        user_roles: List[str],
        endpoint: str,
        ip_address: str
    ):
        """Log permission violation"""
        self.log_event(
            event_type=AuditEventType.PERMISSION_VIOLATION,
            severity=AuditSeverity.WARNING,
            message=f"Permission violation: {username} attempted to access {endpoint} without required roles",
            username=username,
            endpoint=endpoint,
            ip_address=ip_address,
            details={
                "required_roles": required_roles,
                "user_roles": user_roles
            }
        )
    
    # API key event helpers
    def log_api_key_created(
        self,
        username: str,
        key_prefix: str,
        description: str,
        ip_address: str
    ):
        """Log API key creation"""
        self.log_event(
            event_type=AuditEventType.API_KEY_CREATED,
            severity=AuditSeverity.INFO,
            message=f"API key created for user {username}",
            username=username,
            ip_address=ip_address,
            details={
                "key_prefix": key_prefix,
                "description": description
            }
        )
    
    def log_api_key_used(
        self,
        username: str,
        key_prefix: str,
        endpoint: str,
        ip_address: str
    ):
        """Log API key usage"""
        self.log_event(
            event_type=AuditEventType.API_KEY_USED,
            severity=AuditSeverity.DEBUG,
            message=f"API key used by {username}",
            username=username,
            endpoint=endpoint,
            ip_address=ip_address,
            details={"key_prefix": key_prefix}
        )
    
    def log_api_key_revoked(
        self,
        username: str,
        key_prefix: str,
        ip_address: str,
        reason: Optional[str] = None
    ):
        """Log API key revocation"""
        self.log_event(
            event_type=AuditEventType.API_KEY_REVOKED,
            severity=AuditSeverity.INFO,
            message=f"API key revoked for user {username}",
            username=username,
            ip_address=ip_address,
            details={
                "key_prefix": key_prefix,
                "reason": reason
            }
        )
    
    def log_api_key_invalid(
        self,
        key_prefix: str,
        ip_address: str,
        endpoint: str
    ):
        """Log invalid API key attempt"""
        self.log_event(
            event_type=AuditEventType.API_KEY_INVALID,
            severity=AuditSeverity.WARNING,
            message=f"Invalid API key attempted: {key_prefix}",
            ip_address=ip_address,
            endpoint=endpoint,
            details={"key_prefix": key_prefix}
        )
    
    # Rate limiting event helpers
    def log_rate_limit_exceeded(
        self,
        identifier: str,
        endpoint: str,
        limit: int,
        ip_address: str
    ):
        """Log rate limit exceeded"""
        self.log_event(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditSeverity.WARNING,
            message=f"Rate limit exceeded for {identifier} on {endpoint}",
            ip_address=ip_address,
            endpoint=endpoint,
            details={
                "identifier": identifier,
                "limit": limit
            }
        )
    
    # Security violation helpers
    def log_suspicious_activity(
        self,
        description: str,
        ip_address: str,
        endpoint: Optional[str] = None,
        username: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log suspicious activity"""
        self.log_event(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.ERROR,
            message=f"Suspicious activity detected: {description}",
            username=username,
            ip_address=ip_address,
            endpoint=endpoint,
            details=details
        )
    
    def log_injection_attempt(
        self,
        injection_type: str,
        payload: str,
        ip_address: str,
        endpoint: str,
        username: Optional[str] = None
    ):
        """Log injection attempt"""
        if injection_type == "sql":
            event_type = AuditEventType.SQL_INJECTION_ATTEMPT
        elif injection_type == "xss":
            event_type = AuditEventType.XSS_ATTEMPT
        elif injection_type == "command":
            event_type = AuditEventType.COMMAND_INJECTION_ATTEMPT
        else:
            event_type = AuditEventType.INVALID_INPUT
        
        self.log_event(
            event_type=event_type,
            severity=AuditSeverity.CRITICAL,
            message=f"{injection_type.upper()} injection attempt detected",
            username=username,
            ip_address=ip_address,
            endpoint=endpoint,
            details={
                "injection_type": injection_type,
                "payload": payload[:100]  # Truncate for logging
            }
        )
    
    # Query helpers
    def get_events_by_user(
        self,
        username: str,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get recent events for a user"""
        return [
            event for event in self.events[-limit:]
            if event.username == username
        ]
    
    def get_events_by_type(
        self,
        event_type: AuditEventType,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get recent events of a specific type"""
        return [
            event for event in self.events[-limit:]
            if event.event_type == event_type
        ]
    
    def get_events_by_ip(
        self,
        ip_address: str,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get recent events from an IP address"""
        return [
            event for event in self.events[-limit:]
            if event.ip_address == ip_address
        ]
    
    def get_security_violations(
        self,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get recent security violations"""
        violation_types = {
            AuditEventType.SQL_INJECTION_ATTEMPT,
            AuditEventType.XSS_ATTEMPT,
            AuditEventType.COMMAND_INJECTION_ATTEMPT,
            AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.RATE_LIMIT_EXCEEDED
        }
        
        return [
            event for event in self.events[-limit:]
            if event.event_type in violation_types
        ]


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    Get global audit logger instance
    
    Returns:
        AuditLogger instance
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def init_audit_logger(logger: Optional[logging.Logger] = None):
    """
    Initialize audit logger
    
    Args:
        logger: Custom logger instance
    """
    global _audit_logger
    _audit_logger = AuditLogger(logger=logger)
