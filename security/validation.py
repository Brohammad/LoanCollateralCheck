"""
Input Validation and Sanitization

Provides Pydantic models and validators for all API inputs.
"""

import re
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator, UUID4
from datetime import datetime


# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    r"(\bunion\b.*\bselect\b)",
    r"(\bor\b\s+\d+\s*=\s*\d+)",
    r"(';|\";\s*--|--\s)",
    r"(\bdrop\b\s+\btable\b)",
    r"(\bexec\b|\bexecute\b)",
]

# XSS patterns  
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe",
]

# Command injection patterns
COMMAND_INJECTION_PATTERNS = [
    r"[;&|`$]",
    r"\$\(.+\)",
    r"`[^`]+`",
]


class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def check_sql_injection(text: str) -> bool:
        """Check if text contains SQL injection patterns"""
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def check_xss(text: str) -> bool:
        """Check if text contains XSS patterns"""
        for pattern in XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def check_command_injection(text: str) -> bool:
        """Check if text contains command injection patterns"""
        for pattern in COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, text):
                return True
        return False
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize text by removing HTML tags and dangerous characters"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove null bytes
        text = text.replace('\x00', '')
        return text.strip()


# Pydantic Models for Request Validation

class UserMessageRequest(BaseModel):
    """Request model for user messages"""
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[UUID4] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('message')
    def validate_message(cls, v):
        """Validate message content"""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        
        # Check for injection attacks
        if InputValidator.check_sql_injection(v):
            raise ValueError("Message contains suspicious SQL patterns")
        
        if InputValidator.check_xss(v):
            raise ValueError("Message contains suspicious XSS patterns")
        
        if InputValidator.check_command_injection(v):
            raise ValueError("Message contains suspicious command patterns")
        
        # Sanitize
        return InputValidator.sanitize_text(v)
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata"""
        if v and len(str(v)) > 10000:
            raise ValueError("Metadata too large")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "message": "What is loan collateral?",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "metadata": {"user_id": "user-123"}
            }
        }


class RAGSearchRequest(BaseModel):
    """Request model for RAG search"""
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    search_types: List[str] = Field(default=["vector", "web"])
    filters: Optional[Dict[str, str]] = None
    
    @validator('query')
    def validate_query(cls, v):
        """Validate search query"""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        
        # Basic sanitization
        if InputValidator.check_sql_injection(v):
            raise ValueError("Query contains suspicious patterns")
        
        return InputValidator.sanitize_text(v)
    
    @validator('search_types')
    def validate_search_types(cls, v):
        """Validate search types"""
        allowed = {"vector", "web", "linkedin"}
        for search_type in v:
            if search_type not in allowed:
                raise ValueError(f"Invalid search type: {search_type}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "query": "loan collateral types",
                "top_k": 5,
                "search_types": ["vector", "web"]
            }
        }


class SessionRequest(BaseModel):
    """Request model for session operations"""
    session_id: UUID4
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class HealthCheckRequest(BaseModel):
    """Request model for health checks"""
    detailed: bool = Field(default=False)
    component: Optional[str] = None
    
    @validator('component')
    def validate_component(cls, v):
        """Validate component name"""
        if v:
            allowed = {"database", "vector_db", "gemini_api", "cache", "disk_space"}
            if v not in allowed:
                raise ValueError(f"Invalid component: {v}")
        return v


class CandidateSearchRequest(BaseModel):
    """Request model for candidate search (recruitment)"""
    keywords: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = Field(None, max_length=100)
    company: Optional[str] = Field(None, max_length=100)
    max_results: int = Field(default=10, ge=1, le=50)
    
    @validator('keywords', 'location', 'company')
    def validate_text_fields(cls, v):
        """Validate text fields"""
        if v:
            return InputValidator.sanitize_text(v)
        return v


class FeedbackRequest(BaseModel):
    """Request model for user feedback"""
    response_id: str = Field(..., min_length=1, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)
    
    @validator('comment')
    def validate_comment(cls, v):
        """Validate feedback comment"""
        if v:
            if InputValidator.check_xss(v):
                raise ValueError("Comment contains suspicious patterns")
            return InputValidator.sanitize_text(v)
        return v


class ConfigUpdateRequest(BaseModel):
    """Request model for configuration updates (admin only)"""
    key: str = Field(..., min_length=1, max_length=100)
    value: Any
    
    @validator('key')
    def validate_key(cls, v):
        """Validate config key"""
        # Only allow alphanumeric and underscores
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("Invalid config key format")
        return v


# Validation decorator
def validate_request(model: type[BaseModel]):
    """Decorator to validate request using Pydantic model"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            # This is a simplified version - actual implementation
            # would integrate with FastAPI dependency injection
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Response models
class StandardResponse(BaseModel):
    """Standard API response"""
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    error_type: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    success: bool = False
    error: str = "Validation error"
    validation_errors: List[Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
