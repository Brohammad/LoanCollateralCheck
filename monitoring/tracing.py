"""
Distributed Tracing with OpenTelemetry

Provides distributed tracing capabilities for tracking request flow
across components and external API calls.
"""

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode


# Global tracer instance
_tracer: Optional[trace.Tracer] = None


def setup_tracing(
    service_name: str = "ai-agent-system",
    jaeger_host: str = "localhost",
    jaeger_port: int = 6831,
    export_to_console: bool = False,
    export_to_jaeger: bool = True
) -> None:
    """
    Setup OpenTelemetry tracing
    
    Args:
        service_name: Name of the service
        jaeger_host: Jaeger agent hostname
        jaeger_port: Jaeger agent port
        export_to_console: If True, also export to console
        export_to_jaeger: If True, export to Jaeger
    """
    global _tracer
    
    # Create resource with service name
    resource = Resource.create({"service.name": service_name})
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Add exporters
    if export_to_jaeger:
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name=jaeger_host,
                agent_port=jaeger_port,
            )
            provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
        except Exception as e:
            print(f"Warning: Could not setup Jaeger exporter: {e}")
    
    if export_to_console:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
    
    # Set as global tracer provider
    trace.set_tracer_provider(provider)
    
    # Get tracer
    _tracer = trace.get_tracer(__name__)


def get_tracer() -> trace.Tracer:
    """
    Get the global tracer instance
    
    Returns:
        Tracer instance
    
    Raises:
        RuntimeError: If tracing not setup
    """
    if _tracer is None:
        raise RuntimeError("Tracing not setup. Call setup_tracing() first.")
    return _tracer


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    set_status_on_exception: bool = True
):
    """
    Context manager for creating trace spans
    
    Args:
        name: Span name
        attributes: Span attributes
        set_status_on_exception: Automatically set error status on exception
    
    Usage:
        with trace_span("database_query", {"query_type": "SELECT"}):
            # Perform database operation
            pass
    """
    if _tracer is None:
        # Tracing not setup, yield without creating span
        yield None
        return
    
    with _tracer.start_as_current_span(name) as span:
        # Add attributes
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        
        try:
            yield span
        except Exception as e:
            if set_status_on_exception:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
            raise


def trace_async(
    span_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Decorator for tracing async functions
    
    Args:
        span_name: Custom span name (defaults to function name)
        attributes: Additional span attributes
    
    Usage:
        @trace_async(span_name="custom_operation")
        async def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        name = span_name or func.__name__
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if _tracer is None:
                # Tracing not setup, call function directly
                return await func(*args, **kwargs)
            
            with _tracer.start_as_current_span(name) as span:
                # Add function attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))
                
                # Add argument information (be careful with PII)
                if args:
                    span.set_attribute("args.count", len(args))
                if kwargs:
                    span.set_attribute("kwargs.keys", ",".join(kwargs.keys()))
                
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # Record success
                    span.set_status(Status(StatusCode.OK))
                    span.set_attribute("success", True)
                    
                    return result
                
                except Exception as e:
                    # Record error
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    span.set_attribute("success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    raise
                
                finally:
                    # Record duration
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("duration_ms", round(duration_ms, 2))
        
        return wrapper
    return decorator


def trace_sync(
    span_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Decorator for tracing synchronous functions
    
    Args:
        span_name: Custom span name (defaults to function name)
        attributes: Additional span attributes
    
    Usage:
        @trace_sync(span_name="custom_operation")
        def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        name = span_name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if _tracer is None:
                # Tracing not setup, call function directly
                return func(*args, **kwargs)
            
            with _tracer.start_as_current_span(name) as span:
                # Add function attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Record success
                    span.set_status(Status(StatusCode.OK))
                    span.set_attribute("success", True)
                    
                    return result
                
                except Exception as e:
                    # Record error
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    span.set_attribute("success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    raise
                
                finally:
                    # Record duration
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("duration_ms", round(duration_ms, 2))
        
        return wrapper
    return decorator


def add_span_attributes(**attributes) -> None:
    """
    Add attributes to current span
    
    Args:
        **attributes: Attributes to add
    
    Usage:
        with trace_span("operation"):
            add_span_attributes(user_id="123", query="test")
    """
    span = trace.get_current_span()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, str(value))


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Add an event to current span
    
    Args:
        name: Event name
        attributes: Event attributes
    
    Usage:
        with trace_span("operation"):
            add_span_event("cache_hit", {"cache_key": "abc123"})
    """
    span = trace.get_current_span()
    if span:
        span.add_event(name, attributes or {})


# Pre-configured trace decorators for common operations
def trace_intent_classifier(func: Callable) -> Callable:
    """Decorator for tracing intent classification"""
    return trace_async(
        span_name="intent_classification",
        attributes={"component": "intent_classifier"}
    )(func)


def trace_rag_retriever(func: Callable) -> Callable:
    """Decorator for tracing RAG retrieval"""
    return trace_async(
        span_name="rag_retrieval",
        attributes={"component": "rag_retriever"}
    )(func)


def trace_planner(func: Callable) -> Callable:
    """Decorator for tracing planner"""
    return trace_async(
        span_name="planner_generation",
        attributes={"component": "planner"}
    )(func)


def trace_critique(func: Callable) -> Callable:
    """Decorator for tracing critique"""
    return trace_async(
        span_name="critique_evaluation",
        attributes={"component": "critique"}
    )(func)


def trace_database(func: Callable) -> Callable:
    """Decorator for tracing database operations"""
    return trace_async(
        span_name="database_operation",
        attributes={"component": "database"}
    )(func)


def trace_gemini_api(func: Callable) -> Callable:
    """Decorator for tracing Gemini API calls"""
    return trace_async(
        span_name="gemini_api_call",
        attributes={"component": "gemini_api"}
    )(func)


# Example usage class
class TracingExample:
    """
    Example class showing how to use tracing
    """
    
    @trace_async(span_name="process_query")
    async def process_query(self, query: str):
        """Example traced async method"""
        # Tracing is automatic with decorator
        
        # Add custom attributes
        add_span_attributes(
            query_length=len(query),
            query_type="question"
        )
        
        # Create child span
        with trace_span("classify_intent", {"query": query}):
            intent = await self._classify_intent(query)
            add_span_attributes(intent=intent)
        
        # Add event
        add_span_event("intent_classified", {"intent": intent})
        
        # Create another child span
        with trace_span("retrieve_context"):
            context = await self._retrieve_context(query)
            add_span_attributes(context_size=len(context))
        
        return {"intent": intent, "context": context}
    
    async def _classify_intent(self, query: str) -> str:
        """Helper method (not traced by default)"""
        return "question"
    
    async def _retrieve_context(self, query: str) -> str:
        """Helper method (not traced by default)"""
        return "sample context"
