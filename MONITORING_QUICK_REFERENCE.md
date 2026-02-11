# Quick Reference: Monitoring & Observability

## 🚀 5-Minute Quick Start

### 1. Install (1 minute)
```bash
pip install prometheus-client structlog opentelemetry-api opentelemetry-sdk psutil httpx fastapi
```

### 2. Setup (2 minutes)
```python
from fastapi import FastAPI
from monitoring import setup_logging, setup_tracing
from monitoring.middleware import setup_monitoring
from monitoring.health import init_health_checker, health_router

app = FastAPI()

# One-line setup
setup_logging(log_level="INFO", json_logs=True)
setup_tracing(service_name="ai-agent-system")
setup_monitoring(app)
init_health_checker(
    db_path="./database/loan_collateral.db",
    chromadb_path="./data/chromadb"
)
app.include_router(health_router)
```

### 3. Use (2 minutes)
```python
from monitoring.logging import get_logger
from monitoring.metrics import metrics_collector
from monitoring.tracing import trace_async

logger = get_logger(__name__)

@trace_async()
async def my_function():
    logger.info("processing", key="value")
    metrics_collector.record_http_request("GET", "/api", 200, 0.5)
    return "done"
```

---

## 📍 Endpoints

```bash
# Health (fast, for load balancers)
curl http://localhost:8000/health

# Detailed Health (component diagnostics)
curl http://localhost:8000/health/detailed

# Prometheus Metrics
curl http://localhost:8000/metrics

# Liveness (Kubernetes)
curl http://localhost:8000/health/live

# Readiness (Kubernetes)
curl http://localhost:8000/health/ready
```

---

## 📝 Common Usage Patterns

### Logging
```python
from monitoring.logging import get_logger

logger = get_logger(__name__, request_id="123")

# Info log
logger.info("user_action", action="login", user_id="456")

# Error log
logger.error("operation_failed", error=str(e), component="api")

# With context
from monitoring.logging import LogContext
with LogContext(logger, session_id="abc"):
    logger.info("processing")  # Includes session_id
```

### Metrics
```python
from monitoring.metrics import metrics_collector

# HTTP request
metrics_collector.record_http_request("GET", "/api/query", 200, 1.5)

# Intent classification
metrics_collector.record_intent_classification("question", 0.95)

# Gemini API call
metrics_collector.record_gemini_api_call(
    operation="generate",
    status="success",
    duration=2.5,
    input_tokens=1500,
    output_tokens=500
)

# Cache operation
metrics_collector.record_cache_operation("get", "L1", hit=True)

# Error
metrics_collector.record_error("api", "timeout")
```

### Tracing
```python
from monitoring.tracing import trace_async, trace_span, add_span_attributes

# Decorator (automatic)
@trace_async()
async def my_function():
    return "done"

# Context manager (manual)
with trace_span("operation_name", {"key": "value"}):
    # Do work
    add_span_attributes(result_count=5)

# Pre-configured decorators
from monitoring.tracing import trace_intent_classifier, trace_planner

@trace_intent_classifier
async def classify_intent(query):
    return "question"
```

---

## ⚙️ Configuration

### Environment Variables
```bash
# Logging
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_JSON=true               # true for production, false for dev
LOG_FILE=/var/log/app.log   # Optional log file path

# Tracing
TRACING_ENABLED=true
JAEGER_HOST=localhost
JAEGER_PORT=6831

# Health Checks
DB_PATH=./database/loan_collateral.db
CHROMADB_PATH=./data/chromadb
GEMINI_API_KEY=your_key_here
```

### Development vs Production
```python
# Development
setup_logging(log_level="DEBUG", json_logs=False)  # Pretty console
setup_tracing(export_to_console=True, export_to_jaeger=False)

# Production
setup_logging(log_level="INFO", json_logs=True, log_file="/var/log/app.log")
setup_tracing(export_to_jaeger=True, jaeger_host="jaeger-agent")
```

---

## 🔍 Troubleshooting

### Issue: ModuleNotFoundError
```bash
# Solution: Install dependencies
pip install prometheus-client structlog opentelemetry-api opentelemetry-sdk psutil
```

### Issue: Health check fails
```bash
# Solution: Check component availability
curl http://localhost:8000/health/detailed
# Review "components" section for specific failures
```

### Issue: Metrics not in Prometheus
```bash
# Solution: Verify endpoint and Prometheus config
curl http://localhost:8000/metrics  # Should return metrics

# Check prometheus.yml
scrape_configs:
  - job_name: 'app'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Issue: No traces in Jaeger
```bash
# Solution: Verify Jaeger is running
docker run -d -p 16686:16686 -p 6831:6831/udp jaegertracing/all-in-one

# Check configuration
setup_tracing(
    service_name="ai-agent-system",
    jaeger_host="localhost",  # or "jaeger-agent" in Docker
    jaeger_port=6831
)
```

---

## 📊 Key Metrics

### HTTP Performance
```
http_requests_total                   # Request count
http_request_duration_seconds         # Latency (histogram)
http_requests_in_progress             # Active requests
```

### AI Agent Performance
```
intent_classification_total           # Intent classifications
rag_retrieval_duration_seconds        # RAG search time
planner_critique_iterations           # Critique iterations
critique_acceptance_rate              # First-try acceptance
gemini_api_calls_total                # API calls
gemini_api_tokens_used                # Token usage
```

### System Health
```
database_connections_active           # DB connections
cache_hit_rate                        # Cache efficiency
errors_total                          # Error count
circuit_breaker_state                 # Circuit breaker status
```

---

## 🚨 Alert Examples

### High Latency
```yaml
- alert: HighP99Latency
  expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 15
  for: 5m
```

### High Error Rate
```yaml
- alert: HighErrorRate
  expr: (sum(rate(http_requests_total{status_code=~"5.."}[10m])) / sum(rate(http_requests_total[10m]))) * 100 > 5
  for: 10m
```

### Low Cache Hit Rate
```yaml
- alert: LowCacheHitRate
  expr: cache_hit_rate < 50
  for: 1h
```

See `monitoring/alerts.yml` for all 15+ alert rules.

---

## 📚 Files Reference

```
monitoring/
├── __init__.py          # Module exports
├── health.py            # Health checks (650 lines)
├── metrics.py           # Metrics (550 lines)
├── logging.py           # Logging (450 lines)
├── tracing.py           # Tracing (400 lines)
├── middleware.py        # Middleware (350 lines)
└── alerts.yml           # Alerts (250 lines)

docs/
└── monitoring_guide.md  # Full guide (900 lines)

tests/
└── test_monitoring.py   # Tests (300 lines)
```

---

## 🎯 Best Practices

### Logging
✅ Use structured logging with context  
✅ Log business events, not just errors  
✅ Use appropriate log levels  
❌ Don't log PII (automatic masking enabled)  

### Metrics
✅ Record metrics for important operations  
✅ Use histograms for durations  
✅ Use counters for events  
✅ Use gauges for point-in-time values  

### Tracing
✅ Create spans for logical operations  
✅ Add meaningful attributes  
✅ Keep span names consistent  
❌ Don't trace too granularly (performance)  

### Health Checks
✅ Implement component-specific checks  
✅ Set appropriate timeouts  
✅ Return degraded for non-critical issues  
✅ Include diagnostic information  

---

## 💡 Pro Tips

1. **Start Simple:** Use basic health checks first, add detailed later
2. **Monitor Early:** Enable monitoring from day 1, not after problems
3. **Alert Wisely:** Too many alerts = alert fatigue
4. **Cache Aggressively:** High cache hit rate = lower costs
5. **Track Tokens:** Token usage directly affects costs
6. **Use Request IDs:** Makes debugging 10x easier
7. **Review Metrics Weekly:** Spot trends before they become problems
8. **Test Alerts:** Don't wait for production to test alert rules

---

## 🔗 Quick Links

- **Full Documentation:** `docs/monitoring_guide.md`
- **Implementation Status:** `IMPLEMENTATION_STATUS.md`
- **Complete Summary:** `MONITORING_COMPLETE.md`
- **System Design:** `SYSTEM_DESIGN.md`
- **Tests:** `tests/test_monitoring.py`

---

## ⏱️ Performance Impact

| Component | Overhead | Impact |
|-----------|----------|--------|
| Metrics   | < 1ms    | Negligible |
| Logging   | < 5ms    | Minimal |
| Tracing   | < 10ms   | Low |
| Health    | < 100ms  | None (separate endpoint) |
| **Total** | **< 2%** | **Acceptable** |

---

## ✅ Checklist

After integration, verify:

- [ ] Health endpoint returns 200: `curl /health`
- [ ] Detailed health shows all components: `curl /health/detailed`
- [ ] Metrics endpoint returns data: `curl /metrics`
- [ ] Logs appear in console/file
- [ ] Request IDs in response headers
- [ ] PII is masked in logs
- [ ] Prometheus scraping works
- [ ] Grafana shows metrics
- [ ] Jaeger shows traces (if enabled)
- [ ] Alerts configured in AlertManager

---

**Need help?** See `docs/monitoring_guide.md` for complete documentation.

**Ready for production!** 🎉
