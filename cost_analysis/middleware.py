"""
Middleware for automatic cost tracking
"""

import time
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
import structlog

from cost_analysis.tracker import CostTracker
from cost_analysis.models import ModelType, RequestType

logger = structlog.get_logger(__name__)


class CostTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track costs for LLM API calls.
    
    Intercepts requests and tracks token usage and costs.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        tracker: Optional[CostTracker] = None,
        enabled: bool = True,
    ):
        """
        Initialize cost tracking middleware.
        
        Args:
            app: FastAPI application
            tracker: CostTracker instance (creates new if None)
            enabled: Whether cost tracking is enabled
        """
        super().__init__(app)
        self.tracker = tracker or CostTracker()
        self.enabled = enabled
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Process request and track costs.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
        
        Returns:
            Response
        """
        if not self.enabled:
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Check if response has cost tracking data
        # (This would be set by the LLM client)
        if hasattr(response, "cost_data"):
            try:
                cost_data = response.cost_data
                
                # Track usage
                cost_record = self.tracker.track_usage(
                    model=cost_data.get("model", ModelType.GEMINI_2_FLASH),
                    request_type=cost_data.get("request_type", RequestType.GENERATION),
                    input_tokens=cost_data.get("input_tokens", 0),
                    output_tokens=cost_data.get("output_tokens", 0),
                    user_id=cost_data.get("user_id"),
                    session_id=cost_data.get("session_id"),
                    conversation_id=cost_data.get("conversation_id"),
                    agent_name=cost_data.get("agent_name"),
                    metadata={
                        "processing_time": processing_time,
                        "endpoint": str(request.url.path),
                        "method": request.method,
                    },
                )
                
                # Add cost headers to response
                response.headers["X-Cost-Tokens"] = str(cost_record.usage.total_tokens)
                response.headers["X-Cost-USD"] = f"{cost_record.total_cost:.6f}"
                
                logger.info(
                    "cost_tracked",
                    request_id=cost_record.usage.request_id,
                    model=cost_record.usage.model.value,
                    tokens=cost_record.usage.total_tokens,
                    cost=cost_record.total_cost,
                    processing_time=processing_time,
                )
            
            except Exception as e:
                logger.error(
                    "cost_tracking_error",
                    error=str(e),
                    exc_info=True,
                )
        
        return response


def cost_tracking_middleware(
    tracker: Optional[CostTracker] = None,
    enabled: bool = True,
) -> Callable:
    """
    Factory function to create cost tracking middleware.
    
    Args:
        tracker: CostTracker instance
        enabled: Whether cost tracking is enabled
    
    Returns:
        Middleware class
    """
    def middleware(app: ASGIApp) -> CostTrackingMiddleware:
        return CostTrackingMiddleware(app, tracker=tracker, enabled=enabled)
    
    return middleware


# Context manager for tracking costs in code
class CostTrackingContext:
    """
    Context manager for tracking costs of specific operations.
    
    Usage:
        tracker = CostTracker()
        with CostTrackingContext(tracker, model=ModelType.GEMINI_2_FLASH) as ctx:
            # Make LLM API call
            result = llm.generate(prompt)
            
            # Track usage
            ctx.track(
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
    """
    
    def __init__(
        self,
        tracker: CostTracker,
        model: ModelType,
        request_type: RequestType = RequestType.GENERATION,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ):
        """
        Initialize cost tracking context.
        
        Args:
            tracker: CostTracker instance
            model: Model being used
            request_type: Type of request
            user_id: User identifier
            session_id: Session identifier
            conversation_id: Conversation identifier
            agent_name: Agent name
        """
        self.tracker = tracker
        self.model = model
        self.request_type = request_type
        self.user_id = user_id
        self.session_id = session_id
        self.conversation_id = conversation_id
        self.agent_name = agent_name
        self.cost_record = None
        self.start_time = None
    
    def __enter__(self):
        """Enter context"""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context"""
        if self.cost_record:
            processing_time = time.time() - self.start_time
            logger.info(
                "cost_tracked_context",
                request_id=self.cost_record.usage.request_id,
                model=self.cost_record.usage.model.value,
                tokens=self.cost_record.usage.total_tokens,
                cost=self.cost_record.total_cost,
                processing_time=processing_time,
            )
        return False  # Don't suppress exceptions
    
    def track(
        self,
        input_tokens: int,
        output_tokens: int,
        metadata: Optional[dict] = None,
    ):
        """
        Track token usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            metadata: Additional metadata
        """
        self.cost_record = self.tracker.track_usage(
            model=self.model,
            request_type=self.request_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            user_id=self.user_id,
            session_id=self.session_id,
            conversation_id=self.conversation_id,
            agent_name=self.agent_name,
            metadata=metadata,
        )
        return self.cost_record


# Decorator for tracking costs
def track_cost(
    tracker: CostTracker,
    model: ModelType,
    request_type: RequestType = RequestType.GENERATION,
):
    """
    Decorator to automatically track costs of a function.
    
    The decorated function should return a dict with 'input_tokens' and 'output_tokens'.
    
    Usage:
        tracker = CostTracker()
        
        @track_cost(tracker, ModelType.GEMINI_2_FLASH)
        async def generate_response(prompt: str):
            result = await llm.generate(prompt)
            return {
                "response": result.text,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            }
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            if isinstance(result, dict) and "input_tokens" in result and "output_tokens" in result:
                tracker.track_usage(
                    model=model,
                    request_type=request_type,
                    input_tokens=result["input_tokens"],
                    output_tokens=result["output_tokens"],
                    metadata={
                        "function": func.__name__,
                    },
                )
            
            return result
        
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            if isinstance(result, dict) and "input_tokens" in result and "output_tokens" in result:
                tracker.track_usage(
                    model=model,
                    request_type=request_type,
                    input_tokens=result["input_tokens"],
                    output_tokens=result["output_tokens"],
                    metadata={
                        "function": func.__name__,
                    },
                )
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
