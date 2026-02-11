"""
Prometheus Metrics Collection System

Provides comprehensive metrics collection for monitoring system performance,
API usage, errors, and business metrics.
"""

import time
from functools import wraps
from typing import Callable, Optional, Dict, Any

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)


# Create metrics registry
metrics_registry = CollectorRegistry()


# HTTP Request Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=metrics_registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=metrics_registry
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint'],
    registry=metrics_registry
)


# AI Agent Metrics
intent_classification_total = Counter(
    'intent_classification_total',
    'Total intent classifications',
    ['intent', 'confidence_bucket'],
    registry=metrics_registry
)

rag_retrieval_duration_seconds = Histogram(
    'rag_retrieval_duration_seconds',
    'RAG retrieval duration in seconds',
    ['search_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
    registry=metrics_registry
)

planner_critique_iterations = Histogram(
    'planner_critique_iterations',
    'Number of planner-critique iterations',
    buckets=[1, 2, 3],
    registry=metrics_registry
)

critique_acceptance_rate = Gauge(
    'critique_acceptance_rate',
    'Percentage of responses accepted on first iteration',
    registry=metrics_registry
)

gemini_api_calls_total = Counter(
    'gemini_api_calls_total',
    'Total Gemini API calls',
    ['operation', 'status'],
    registry=metrics_registry
)

gemini_api_tokens_used = Counter(
    'gemini_api_tokens_used',
    'Total tokens used by Gemini API',
    ['type'],  # input or output
    registry=metrics_registry
)

gemini_api_duration_seconds = Histogram(
    'gemini_api_duration_seconds',
    'Gemini API call duration in seconds',
    ['operation'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 15.0],
    registry=metrics_registry
)


# Database Metrics
database_connections_active = Gauge(
    'database_connections_active',
    'Number of active database connections',
    registry=metrics_registry
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
    registry=metrics_registry
)


# Cache Metrics
cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate percentage',
    ['cache_level'],  # L1 or L2
    registry=metrics_registry
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Cache size in bytes',
    ['cache_level'],
    registry=metrics_registry
)

cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'cache_level', 'result'],  # operation: get/set, result: hit/miss
    registry=metrics_registry
)


# Vector DB Metrics
vector_db_query_duration_seconds = Histogram(
    'vector_db_query_duration_seconds',
    'Vector database query duration in seconds',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0],
    registry=metrics_registry
)

vector_db_documents_count = Gauge(
    'vector_db_documents_count',
    'Number of documents in vector database',
    ['collection'],
    registry=metrics_registry
)


# Error Metrics
errors_total = Counter(
    'errors_total',
    'Total errors',
    ['component', 'error_type'],
    registry=metrics_registry
)

api_errors_total = Counter(
    'api_errors_total',
    'Total API errors',
    ['api', 'status_code'],
    registry=metrics_registry
)

circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half-open, 2=open)',
    ['service'],
    registry=metrics_registry
)


# System Metrics
system_memory_usage_bytes = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes',
    registry=metrics_registry
)

system_cpu_usage_percent = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=metrics_registry
)


class MetricsCollector:
    """
    Comprehensive metrics collector with helper methods
    """
    
    def __init__(self):
        """Initialize metrics collector"""
        self.registry = metrics_registry
        self._cache_stats: Dict[str, Dict[str, int]] = {
            'L1': {'hits': 0, 'misses': 0},
            'L2': {'hits': 0, 'misses': 0}
        }
    
    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float
    ) -> None:
        """
        Record HTTP request metrics
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Request endpoint
            status_code: Response status code
            duration: Request duration in seconds
        """
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def track_http_in_progress(
        self,
        method: str,
        endpoint: str
    ):
        """
        Context manager to track requests in progress
        
        Usage:
            with collector.track_http_in_progress('GET', '/api/query'):
                # Handle request
                pass
        """
        class _InProgressTracker:
            def __enter__(self_):
                http_requests_in_progress.labels(
                    method=method,
                    endpoint=endpoint
                ).inc()
                self_.start_time = time.time()
                return self_
            
            def __exit__(self_, exc_type, exc_val, exc_tb):
                http_requests_in_progress.labels(
                    method=method,
                    endpoint=endpoint
                ).dec()
        
        return _InProgressTracker()
    
    def record_intent_classification(
        self,
        intent: str,
        confidence: float
    ) -> None:
        """
        Record intent classification
        
        Args:
            intent: Classified intent
            confidence: Confidence score (0-1)
        """
        # Bucket confidence scores
        if confidence >= 0.9:
            bucket = "high"
        elif confidence >= 0.7:
            bucket = "medium"
        else:
            bucket = "low"
        
        intent_classification_total.labels(
            intent=intent,
            confidence_bucket=bucket
        ).inc()
    
    def record_rag_retrieval(
        self,
        search_type: str,
        duration: float
    ) -> None:
        """
        Record RAG retrieval metrics
        
        Args:
            search_type: Type of search (vector, web, etc.)
            duration: Search duration in seconds
        """
        rag_retrieval_duration_seconds.labels(
            search_type=search_type
        ).observe(duration)
    
    def record_planner_critique(
        self,
        iterations: int,
        accepted_first_try: bool
    ) -> None:
        """
        Record planner-critique metrics
        
        Args:
            iterations: Number of iterations taken
            accepted_first_try: Whether response was accepted on first try
        """
        planner_critique_iterations.observe(iterations)
        
        # Update acceptance rate (this is simplified - in production use rolling average)
        if accepted_first_try:
            critique_acceptance_rate.set(
                critique_acceptance_rate._value.get() * 0.95 + 0.05
                if hasattr(critique_acceptance_rate._value, 'get')
                else 1.0
            )
    
    def record_gemini_api_call(
        self,
        operation: str,
        status: str,
        duration: float,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> None:
        """
        Record Gemini API call metrics
        
        Args:
            operation: Type of operation (generate, classify, etc.)
            status: Call status (success, error, timeout)
            duration: Call duration in seconds
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        gemini_api_calls_total.labels(
            operation=operation,
            status=status
        ).inc()
        
        gemini_api_duration_seconds.labels(
            operation=operation
        ).observe(duration)
        
        if input_tokens > 0:
            gemini_api_tokens_used.labels(type='input').inc(input_tokens)
        
        if output_tokens > 0:
            gemini_api_tokens_used.labels(type='output').inc(output_tokens)
    
    def record_database_query(
        self,
        query_type: str,
        duration: float
    ) -> None:
        """
        Record database query metrics
        
        Args:
            query_type: Type of query (select, insert, update, etc.)
            duration: Query duration in seconds
        """
        database_query_duration_seconds.labels(
            query_type=query_type
        ).observe(duration)
    
    def update_database_connections(self, count: int) -> None:
        """Update active database connections count"""
        database_connections_active.set(count)
    
    def record_cache_operation(
        self,
        operation: str,
        cache_level: str,
        hit: bool
    ) -> None:
        """
        Record cache operation
        
        Args:
            operation: Operation type (get, set)
            cache_level: Cache level (L1, L2)
            hit: Whether operation was a cache hit
        """
        result = 'hit' if hit else 'miss'
        
        cache_operations_total.labels(
            operation=operation,
            cache_level=cache_level,
            result=result
        ).inc()
        
        # Update cache hit rate
        if operation == 'get':
            stats = self._cache_stats[cache_level]
            if hit:
                stats['hits'] += 1
            else:
                stats['misses'] += 1
            
            total = stats['hits'] + stats['misses']
            hit_rate = (stats['hits'] / total * 100) if total > 0 else 0
            cache_hit_rate.labels(cache_level=cache_level).set(hit_rate)
    
    def update_cache_size(self, cache_level: str, size_bytes: int) -> None:
        """Update cache size metric"""
        cache_size_bytes.labels(cache_level=cache_level).set(size_bytes)
    
    def record_vector_db_query(self, duration: float) -> None:
        """Record vector database query duration"""
        vector_db_query_duration_seconds.observe(duration)
    
    def update_vector_db_count(self, collection: str, count: int) -> None:
        """Update vector database document count"""
        vector_db_documents_count.labels(collection=collection).set(count)
    
    def record_error(
        self,
        component: str,
        error_type: str
    ) -> None:
        """
        Record error occurrence
        
        Args:
            component: Component where error occurred
            error_type: Type of error
        """
        errors_total.labels(
            component=component,
            error_type=error_type
        ).inc()
    
    def record_api_error(
        self,
        api: str,
        status_code: int
    ) -> None:
        """
        Record API error
        
        Args:
            api: API name (gemini, serp, etc.)
            status_code: HTTP status code
        """
        api_errors_total.labels(
            api=api,
            status_code=status_code
        ).inc()
    
    def update_circuit_breaker_state(
        self,
        service: str,
        state: str
    ) -> None:
        """
        Update circuit breaker state
        
        Args:
            service: Service name
            state: State (closed, half-open, open)
        """
        state_map = {'closed': 0, 'half-open': 1, 'open': 2}
        circuit_breaker_state.labels(service=service).set(
            state_map.get(state.lower(), 0)
        )
    
    def update_system_metrics(
        self,
        memory_bytes: Optional[int] = None,
        cpu_percent: Optional[float] = None
    ) -> None:
        """
        Update system resource metrics
        
        Args:
            memory_bytes: Memory usage in bytes
            cpu_percent: CPU usage percentage
        """
        if memory_bytes is not None:
            system_memory_usage_bytes.set(memory_bytes)
        
        if cpu_percent is not None:
            system_cpu_usage_percent.set(cpu_percent)
    
    def get_metrics(self) -> bytes:
        """
        Generate Prometheus metrics output
        
        Returns:
            Metrics in Prometheus text format
        """
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """Get content type for metrics endpoint"""
        return CONTENT_TYPE_LATEST


# Decorator for automatic metrics collection
def track_duration(metric_name: str, **labels):
    """
    Decorator to track function execution duration
    
    Usage:
        @track_duration('my_function_duration', component='api')
        def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    # Record to appropriate metric based on metric_name
                    # This is a simplified version
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    # Record to appropriate metric
            return sync_wrapper
    return decorator


# Global metrics collector instance
metrics_collector = MetricsCollector()
