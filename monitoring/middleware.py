"""
FastAPI Middleware for Monitoring

Integrates metrics collection, logging, and tracing into FastAPI
application lifecycle.
"""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from monitoring.metrics import metrics_collector
from monitoring.logging import get_api_logger
from monitoring.tracing import trace_span, add_span_attributes


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive monitoring middleware for FastAPI
    
    Provides:
    - Automatic metrics collection for all requests
    - Structured logging with request context
    - Distributed tracing spans
    - Request/response timing
    """
    
    def __init__(
        self,
        app: ASGIApp,
        service_name: str = "ai-agent-system"
    ):
        """
        Initialize monitoring middleware
        
        Args:
            app: FastAPI application
            service_name: Service name for tracing
        """
        super().__init__(app)
        self.service_name = service_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with monitoring
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
        
        Returns:
            Response from handler
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract request info
        method = request.method
        path = request.url.path
        endpoint = self._normalize_endpoint(path)
        
        # Create logger with request context
        logger = get_api_logger(
            request_id=request_id,
            endpoint=endpoint,
            method=method
        )
        
        # Log request start
        logger.info(
            "request_started",
            path=path,
            user_agent=request.headers.get("user-agent", "unknown"),
            client_host=request.client.host if request.client else "unknown"
        )
        
        # Start timing
        start_time = time.time()
        
        # Track in-progress requests
        with metrics_collector.track_http_in_progress(method, endpoint):
            # Create trace span for entire request
            with trace_span(
                f"{method} {endpoint}",
                attributes={
                    "http.method": method,
                    "http.url": str(request.url),
                    "http.scheme": request.url.scheme,
                    "http.host": request.url.hostname,
                    "http.target": path,
                    "request.id": request_id,
                }
            ) as span:
                try:
                    # Process request
                    response = await call_next(request)
                    
                    # Calculate duration
                    duration = time.time() - start_time
                    
                    # Add response attributes to span
                    if span:
                        add_span_attributes(
                            http_status_code=response.status_code,
                            response_time_ms=round(duration * 1000, 2)
                        )
                    
                    # Record metrics
                    metrics_collector.record_http_request(
                        method=method,
                        endpoint=endpoint,
                        status_code=response.status_code,
                        duration=duration
                    )
                    
                    # Log request completion
                    logger.info(
                        "request_completed",
                        status_code=response.status_code,
                        duration_ms=round(duration * 1000, 2)
                    )
                    
                    # Add request ID to response headers
                    response.headers["X-Request-ID"] = request_id
                    
                    return response
                
                except Exception as e:
                    # Calculate duration even on error
                    duration = time.time() - start_time
                    
                    # Record error metrics
                    metrics_collector.record_http_request(
                        method=method,
                        endpoint=endpoint,
                        status_code=500,
                        duration=duration
                    )
                    
                    metrics_collector.record_error(
                        component="api",
                        error_type=type(e).__name__
                    )
                    
                    # Log error
                    logger.error(
                        "request_failed",
                        error_type=type(e).__name__,
                        error_message=str(e),
                        duration_ms=round(duration * 1000, 2)
                    )
                    
                    # Re-raise exception
                    raise
    
    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path for metrics
        
        Converts paths with IDs to templates:
        /api/conversation/123 -> /api/conversation/{id}
        
        Args:
            path: Request path
        
        Returns:
            Normalized endpoint path
        """
        # Split path into segments
        segments = path.split('/')
        
        # Replace UUIDs and numeric IDs with placeholders
        normalized = []
        for segment in segments:
            if not segment:
                continue
            
            # Check if segment is UUID
            if self._is_uuid(segment):
                normalized.append('{id}')
            # Check if segment is numeric
            elif segment.isdigit():
                normalized.append('{id}')
            else:
                normalized.append(segment)
        
        return '/' + '/'.join(normalized) if normalized else path
    
    def _is_uuid(self, value: str) -> bool:
        """Check if string is a UUID"""
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware for metrics only
    
    Use this if you don't need full monitoring with logging and tracing.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with metrics collection"""
        method = request.method
        endpoint = request.url.path
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            duration = time.time() - start_time
            
            metrics_collector.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
        
        except Exception as e:
            duration = time.time() - start_time
            
            metrics_collector.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=500,
                duration=duration
            )
            
            raise


def setup_monitoring(
    app: FastAPI,
    enable_metrics: bool = True,
    enable_logging: bool = True,
    enable_tracing: bool = True,
    service_name: str = "ai-agent-system"
) -> None:
    """
    Setup monitoring for FastAPI application
    
    Args:
        app: FastAPI application
        enable_metrics: Enable Prometheus metrics
        enable_logging: Enable structured logging
        enable_tracing: Enable distributed tracing
        service_name: Service name for monitoring
    """
    # Add monitoring middleware
    if enable_metrics or enable_logging or enable_tracing:
        app.add_middleware(
            MonitoringMiddleware,
            service_name=service_name
        )
    
    # Add metrics endpoint
    if enable_metrics:
        from fastapi import Response as FastAPIResponse
        
        @app.get("/metrics", tags=["monitoring"])
        async def metrics_endpoint():
            """Prometheus metrics endpoint"""
            return FastAPIResponse(
                content=metrics_collector.get_metrics(),
                media_type=metrics_collector.get_content_type()
            )


# Context propagation helpers
def get_request_id(request: Request) -> str:
    """
    Get request ID from request state
    
    Args:
        request: FastAPI request
    
    Returns:
        Request ID or "unknown"
    """
    return getattr(request.state, 'request_id', 'unknown')


def get_session_id(request: Request) -> str:
    """
    Get session ID from request
    
    Args:
        request: FastAPI request
    
    Returns:
        Session ID from header/cookie or "unknown"
    """
    # Try to get from header
    session_id = request.headers.get('X-Session-ID')
    
    # Try to get from cookie
    if not session_id:
        session_id = request.cookies.get('session_id')
    
    return session_id or 'unknown'


# Example usage
def example_setup():
    """
    Example of setting up monitoring in FastAPI application
    """
    from fastapi import FastAPI
    
    # Create app
    app = FastAPI(title="AI Agent System")
    
    # Setup monitoring
    setup_monitoring(
        app,
        enable_metrics=True,
        enable_logging=True,
        enable_tracing=True,
        service_name="ai-agent-system"
    )
    
    # Add routes
    @app.get("/")
    async def root():
        return {"message": "Hello World"}
    
    @app.post("/api/query")
    async def query(request: Request):
        # Request ID is automatically available
        request_id = get_request_id(request)
        
        # Your handler code here
        return {"request_id": request_id}
    
    return app
