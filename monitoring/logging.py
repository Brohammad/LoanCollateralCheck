"""
Structured Logging Configuration

Provides structured logging with JSON output for production,
pretty console output for development, and automatic PII masking.
"""

import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from structlog.processors import JSONRenderer
from structlog.stdlib import add_log_level, add_logger_name


# PII patterns to mask
PII_PATTERNS = {
    'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
    'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    'credit_card': re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
    'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    'api_key': re.compile(r'\b[A-Za-z0-9]{32,}\b'),
}


def mask_pii(text: str) -> str:
    """
    Mask PII in text strings
    
    Args:
        text: Text potentially containing PII
    
    Returns:
        Text with PII masked
    """
    if not isinstance(text, str):
        return text
    
    masked = text
    
    # Mask emails
    masked = PII_PATTERNS['email'].sub(
        lambda m: m.group(0)[:2] + '***@' + m.group(0).split('@')[1],
        masked
    )
    
    # Mask phone numbers
    masked = PII_PATTERNS['phone'].sub('***-***-****', masked)
    
    # Mask SSN
    masked = PII_PATTERNS['ssn'].sub('***-**-****', masked)
    
    # Mask credit cards
    masked = PII_PATTERNS['credit_card'].sub(
        lambda m: m.group(0)[:4] + '-****-****-' + m.group(0)[-4:],
        masked
    )
    
    # Mask IP addresses
    masked = PII_PATTERNS['ip_address'].sub(
        lambda m: '.'.join(m.group(0).split('.')[:2]) + '.*.*',
        masked
    )
    
    return masked


def pii_masking_processor(logger, method_name, event_dict):
    """
    Structlog processor to mask PII in log messages
    
    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary
    
    Returns:
        Event dictionary with PII masked
    """
    # Mask event message
    if 'event' in event_dict:
        event_dict['event'] = mask_pii(str(event_dict['event']))
    
    # Mask all string values in event dict
    for key, value in event_dict.items():
        if isinstance(value, str):
            event_dict[key] = mask_pii(value)
        elif isinstance(value, dict):
            event_dict[key] = {
                k: mask_pii(v) if isinstance(v, str) else v
                for k, v in value.items()
            }
    
    return event_dict


def add_timestamp(logger, method_name, event_dict):
    """
    Add ISO 8601 timestamp to log events
    
    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary
    
    Returns:
        Event dictionary with timestamp
    """
    event_dict['timestamp'] = datetime.utcnow().isoformat() + 'Z'
    return event_dict


def add_context(logger, method_name, event_dict):
    """
    Add context information to log events
    
    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary
    
    Returns:
        Event dictionary with context
    """
    # Context can be bound to logger using structlog.bind()
    # This processor ensures context is included in output
    return event_dict


def setup_logging(
    log_level: str = "INFO",
    json_logs: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    Configure structured logging for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output JSON format (for production)
        log_file: Optional log file path
    """
    # Convert log level string to int
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
        stream=sys.stdout
    )
    
    # Processors for all logs
    processors = [
        add_timestamp,
        add_log_level,
        add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        pii_masking_processor,
        add_context,
    ]
    
    # Choose renderer based on environment
    if json_logs:
        # Production: JSON output
        processors.append(JSONRenderer())
    else:
        # Development: Pretty console output
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        
        # Use JSON format for file logs
        file_handler.setFormatter(
            logging.Formatter('%(message)s')
        )
        
        logging.root.addHandler(file_handler)


def get_logger(name: str, **context) -> structlog.BoundLogger:
    """
    Get a logger instance with optional context
    
    Args:
        name: Logger name (usually __name__)
        **context: Additional context to bind to logger
    
    Returns:
        Structured logger instance
    
    Example:
        logger = get_logger(__name__, request_id="123", session_id="abc")
        logger.info("user_action", action="login", user_id="456")
    """
    logger = structlog.get_logger(name)
    
    if context:
        logger = logger.bind(**context)
    
    return logger


class LogContext:
    """
    Context manager for temporary log context
    
    Usage:
        logger = get_logger(__name__)
        
        with LogContext(logger, request_id="123"):
            logger.info("processing_request")
            # Logs will include request_id
    """
    
    def __init__(self, logger: structlog.BoundLogger, **context):
        """
        Initialize log context
        
        Args:
            logger: Logger instance
            **context: Context to bind temporarily
        """
        self.logger = logger
        self.context = context
        self.bound_logger = None
    
    def __enter__(self) -> structlog.BoundLogger:
        """Enter context and return bound logger"""
        self.bound_logger = self.logger.bind(**self.context)
        return self.bound_logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context"""
        # Context is automatically removed when logger goes out of scope
        pass


# Pre-configured loggers for common components
def get_api_logger(request_id: str, endpoint: str, method: str) -> structlog.BoundLogger:
    """Get logger for API requests"""
    return get_logger(
        "api",
        request_id=request_id,
        endpoint=endpoint,
        method=method
    )


def get_agent_logger(agent_name: str, session_id: str) -> structlog.BoundLogger:
    """Get logger for agent operations"""
    return get_logger(
        "agent",
        agent_name=agent_name,
        session_id=session_id
    )


def get_database_logger(operation: str) -> structlog.BoundLogger:
    """Get logger for database operations"""
    return get_logger(
        "database",
        operation=operation
    )


def get_cache_logger(cache_level: str) -> structlog.BoundLogger:
    """Get logger for cache operations"""
    return get_logger(
        "cache",
        cache_level=cache_level
    )


# Example log messages for reference
EXAMPLE_LOGS = {
    "request_started": {
        "level": "INFO",
        "event": "request_started",
        "example": {
            "request_id": "uuid-here",
            "endpoint": "/api/query",
            "method": "POST",
            "user_agent": "Mozilla/5.0...",
        }
    },
    "request_completed": {
        "level": "INFO",
        "event": "request_completed",
        "example": {
            "request_id": "uuid-here",
            "duration_ms": 1234,
            "status_code": 200,
            "intent": "question",
            "tokens_used": 3500,
            "cache_hit": True,
        }
    },
    "intent_classified": {
        "level": "INFO",
        "event": "intent_classified",
        "example": {
            "session_id": "session-uuid",
            "intent": "question",
            "confidence": 0.95,
        }
    },
    "rag_search_started": {
        "level": "DEBUG",
        "event": "rag_search_started",
        "example": {
            "query": "What is collateral?",
            "search_types": ["vector", "web"],
        }
    },
    "rag_search_completed": {
        "level": "INFO",
        "event": "rag_search_completed",
        "example": {
            "duration_ms": 850,
            "results_count": 5,
            "sources": ["vector_db", "web"],
        }
    },
    "planner_iteration": {
        "level": "DEBUG",
        "event": "planner_iteration",
        "example": {
            "iteration": 1,
            "response_length": 250,
        }
    },
    "critique_evaluation": {
        "level": "INFO",
        "event": "critique_evaluation",
        "example": {
            "iteration": 1,
            "overall_score": 0.87,
            "accuracy_score": 0.9,
            "completeness_score": 0.85,
            "clarity_score": 0.85,
            "approved": True,
        }
    },
    "error_occurred": {
        "level": "ERROR",
        "event": "error_occurred",
        "example": {
            "component": "gemini_client",
            "error_type": "timeout",
            "error_message": "API timeout after 15s",
            "retry_attempt": 1,
        }
    },
}
