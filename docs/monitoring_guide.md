# Monitoring & Observability Guide

## Overview

This guide explains how to set up and use the comprehensive monitoring and observability features for the AI Agent System.

## Features

### 1. Health Checks
- **Basic health check** (`/health`): Fast check for load balancers
- **Detailed health check** (`/health/detailed`): Component-level diagnostics
- **Liveness probe** (`/health/live`): Kubernetes liveness check
- **Readiness probe** (`/health/ready`): Kubernetes readiness check

### 2. Prometheus Metrics
Comprehensive metrics collection including:
- HTTP request metrics (rate, latency, errors)
- AI agent metrics (intent classification, RAG retrieval, planner-critique)
- Gemini API metrics (calls, tokens, latency)
- Database metrics (connections, query performance)
- Cache metrics (hit rates, size)
- System metrics (CPU, memory, disk)

### 3. Structured Logging
- JSON output for production
- Pretty console output for development
- Automatic PII masking
- Request context propagation
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

### 4. Distributed Tracing
- OpenTelemetry integration
- Request lifecycle tracking
- Component-level spans
- Automatic instrumentation
- Jaeger export support

## Quick Start

### 1. Installation

```bash
# Install monitoring dependencies
pip install -r requirements.txt
```

### 2. Basic Setup

```python
from fastapi import FastAPI
from monitoring import setup_logging, setup_tracing
from monitoring.middleware import setup_monitoring
from monitoring.health import init_health_checker, health_router

# Create FastAPI app
app = FastAPI()

# Setup logging
setup_logging(
    log_level="INFO",
    json_logs=True,  # Use JSON in production
    log_file="./logs/app.log"
)

# Setup tracing
setup_tracing(
    service_name="ai-agent-system",
    jaeger_host="localhost",
    jaeger_port=6831,
    export_to_console=False,
    export_to_jaeger=True
)

# Setup monitoring middleware
setup_monitoring(
    app,
    enable_metrics=True,
    enable_logging=True,
    enable_tracing=True
)

# Initialize health checker
init_health_checker(
    db_path="./database/loan_collateral.db",
    chromadb_path="./data/chromadb",
    gemini_api_key="your-api-key"
)

# Add health check routes
app.include_router(health_router)
```

### 3. Using Structured Logging

```python
from monitoring.logging import get_logger

# Get logger with context
logger = get_logger(__name__, request_id="123", session_id="abc")

# Log with structured data
logger.info(
    "user_query_processed",
    query="What is collateral?",
    intent="question",
    duration_ms=1234,
    tokens_used=3500
)

# Log errors
try:
    result = await process_query(query)
except Exception as e:
    logger.error(
        "query_processing_failed",
        error=str(e),
        error_type=type(e).__name__
    )
    raise
```

### 4. Using Metrics

```python
from monitoring.metrics import metrics_collector

# Record intent classification
metrics_collector.record_intent_classification(
    intent="question",
    confidence=0.95
)

# Record Gemini API call
metrics_collector.record_gemini_api_call(
    operation="generate",
    status="success",
    duration=2.5,
    input_tokens=1500,
    output_tokens=500
)

# Record cache operation
metrics_collector.record_cache_operation(
    operation="get",
    cache_level="L1",
    hit=True
)
```

### 5. Using Tracing

```python
from monitoring.tracing import trace_async, trace_span, add_span_attributes

# Decorate async functions
@trace_async(span_name="process_query")
async def process_query(query: str):
    # Automatic tracing
    
    # Add custom attributes
    add_span_attributes(
        query_length=len(query),
        user_id="123"
    )
    
    # Create child spans
    with trace_span("classify_intent"):
        intent = await classify_intent(query)
    
    with trace_span("retrieve_context"):
        context = await retrieve_context(query)
    
    return result
```

## Endpoints

### Health Checks

#### GET /health
Basic health check for load balancers.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-11T10:30:45.123Z",
  "response_time_ms": 45.23
}
```

#### GET /health/detailed
Detailed health check with component status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-11T10:30:45.123Z",
  "response_time_ms": 145.67,
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database is accessible and healthy",
      "response_time_ms": 42.15,
      "details": {
        "path": "./database/loan_collateral.db",
        "integrity": "ok",
        "size_mb": 12.45
      }
    },
    "vector_db": {
      "status": "healthy",
      "message": "Vector DB is accessible",
      "response_time_ms": 38.92,
      "details": {
        "collections_count": 2
      }
    }
  }
}
```

### Metrics

#### GET /metrics
Prometheus metrics endpoint.

**Response:** Prometheus text format
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/query",status_code="200"} 1234.0

# HELP http_request_duration_seconds HTTP request duration in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/api/query",le="0.1"} 850.0
...
```

## Prometheus Configuration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# Load alert rules
rule_files:
  - "monitoring/alerts.yml"

scrape_configs:
  - job_name: 'ai-agent-system'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

## Grafana Dashboard

Import the dashboard from `monitoring/grafana_dashboard.json` (to be created).

Key panels:
- Request rate and latency (P50, P95, P99)
- Error rates by component
- Cache hit rates
- Token usage over time
- Critique iterations distribution
- System resources (CPU, memory, disk)

## Alerting

Alerts are defined in `monitoring/alerts.yml`.

Key alerts:
- **HighP99Latency**: P99 latency > 15s for 5 minutes
- **HighErrorRate**: Error rate > 5% for 10 minutes
- **LowCacheHitRate**: Cache hit rate < 50% for 1 hour
- **LowDiskSpace**: Disk usage > 90%
- **HighMemoryUsage**: Memory usage > 90%

## Development vs Production

### Development
```python
# Pretty console logging
setup_logging(log_level="DEBUG", json_logs=False)

# Console tracing
setup_tracing(export_to_console=True, export_to_jaeger=False)
```

### Production
```python
# JSON logging
setup_logging(log_level="INFO", json_logs=True, log_file="/var/log/app.log")

# Jaeger tracing
setup_tracing(
    export_to_console=False,
    export_to_jaeger=True,
    jaeger_host="jaeger-agent",
    jaeger_port=6831
)
```

## Environment Variables

```bash
# Logging
LOG_LEVEL=INFO
LOG_JSON=true
LOG_FILE=/var/log/ai-agent/app.log

# Tracing
TRACING_ENABLED=true
JAEGER_HOST=localhost
JAEGER_PORT=6831

# Metrics
METRICS_ENABLED=true
```

## Best Practices

### 1. Logging
- Use structured logging with context
- Never log raw PII (automatic masking enabled)
- Log business events, not just errors
- Use appropriate log levels

### 2. Metrics
- Record metrics for all important operations
- Use histograms for duration metrics
- Use counters for events
- Use gauges for point-in-time values

### 3. Tracing
- Create spans for logical operations
- Add meaningful attributes
- Keep span names consistent
- Don't trace too granularly (performance impact)

### 4. Health Checks
- Implement component-specific checks
- Set appropriate timeouts
- Return degraded status for non-critical issues
- Include diagnostic information

## Troubleshooting

### Issue: Metrics not appearing
**Solution:** 
- Check that prometheus-client is installed
- Verify `/metrics` endpoint is accessible
- Check Prometheus scrape configuration

### Issue: Traces not in Jaeger
**Solution:**
- Verify Jaeger agent is running
- Check JAEGER_HOST and JAEGER_PORT
- Verify opentelemetry dependencies installed

### Issue: Health check fails
**Solution:**
- Check component availability (database, vector DB)
- Review health check logs
- Verify file paths and permissions

### Issue: PII in logs
**Solution:**
- PII masking is automatic but may need pattern updates
- Check PII_PATTERNS in monitoring/logging.py
- Add custom patterns if needed

## Performance Impact

Monitoring overhead:
- Metrics collection: < 1ms per operation
- Logging: < 5ms per log entry
- Tracing: < 10ms per request (with sampling)

Overall impact: < 2% of total request time

## Next Steps

1. **Setup Prometheus**: Install and configure Prometheus to scrape metrics
2. **Setup Grafana**: Import dashboard and connect to Prometheus
3. **Setup Jaeger**: Install Jaeger for distributed tracing
4. **Configure Alerts**: Customize alert rules for your environment
5. **Test Monitoring**: Generate test traffic and verify metrics/logs/traces

## Support

For issues or questions:
- Review logs in `/var/log/ai-agent/`
- Check health endpoint: `/health/detailed`
- Review metrics: `/metrics`
- Check Grafana dashboards

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Structlog Documentation](https://www.structlog.org/)
