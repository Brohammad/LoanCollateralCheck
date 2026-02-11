"""
Test Monitoring System

Quick test to verify monitoring components are working correctly.
"""

import pytest
import asyncio
from pathlib import Path

# Test health check system
def test_health_checker_import():
    """Test that health checker can be imported"""
    from monitoring.health import HealthChecker, HealthStatus
    assert HealthChecker is not None
    assert HealthStatus is not None


def test_metrics_import():
    """Test that metrics can be imported"""
    from monitoring.metrics import metrics_collector, metrics_registry
    assert metrics_collector is not None
    assert metrics_registry is not None


def test_logging_import():
    """Test that logging can be imported"""
    from monitoring.logging import get_logger, setup_logging
    assert get_logger is not None
    assert setup_logging is not None


def test_tracing_import():
    """Test that tracing can be imported"""
    from monitoring.tracing import setup_tracing, trace_async
    assert setup_tracing is not None
    assert trace_async is not None


def test_middleware_import():
    """Test that middleware can be imported"""
    from monitoring.middleware import MonitoringMiddleware, setup_monitoring
    assert MonitoringMiddleware is not None
    assert setup_monitoring is not None


@pytest.mark.asyncio
async def test_health_checker_basic():
    """Test basic health checker functionality"""
    from monitoring.health import HealthChecker
    
    # Create temporary test database
    import tempfile
    import sqlite3
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        # Create a test database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()
        
        # Create health checker
        checker = HealthChecker(
            db_path=str(db_path),
            chromadb_path=str(Path(tmpdir) / "chromadb")
        )
        
        # Check database health
        db_health = await checker.check_database()
        assert db_health.name == "database"
        assert db_health.status in ["healthy", "degraded", "unhealthy"]
        assert db_health.response_time_ms >= 0


def test_metrics_collector():
    """Test metrics collector functionality"""
    from monitoring.metrics import MetricsCollector
    
    collector = MetricsCollector()
    
    # Test recording metrics
    collector.record_http_request(
        method="GET",
        endpoint="/test",
        status_code=200,
        duration=0.5
    )
    
    collector.record_intent_classification(
        intent="question",
        confidence=0.95
    )
    
    collector.record_gemini_api_call(
        operation="generate",
        status="success",
        duration=2.5,
        input_tokens=1500,
        output_tokens=500
    )
    
    # Get metrics output
    metrics_output = collector.get_metrics()
    assert metrics_output is not None
    assert isinstance(metrics_output, bytes)


def test_structured_logging():
    """Test structured logging functionality"""
    from monitoring.logging import get_logger, setup_logging, mask_pii
    
    # Setup logging
    setup_logging(log_level="INFO", json_logs=False)
    
    # Get logger
    logger = get_logger(__name__, request_id="test-123")
    
    # Log some messages (should not raise errors)
    logger.info("test_event", key="value")
    logger.warning("test_warning", count=42)
    logger.error("test_error", error="test error")
    
    # Test PII masking
    assert "***" in mask_pii("user@example.com")
    assert "***" in mask_pii("555-123-4567")
    assert "***" in mask_pii("123-45-6789")


def test_tracing_setup():
    """Test tracing setup"""
    from monitoring.tracing import setup_tracing, get_tracer, trace_span
    
    # Setup tracing (console only for test)
    setup_tracing(
        service_name="test-service",
        export_to_console=False,
        export_to_jaeger=False
    )
    
    # Get tracer
    tracer = get_tracer()
    assert tracer is not None
    
    # Test span creation
    with trace_span("test_operation", {"key": "value"}):
        pass  # Should not raise errors


@pytest.mark.asyncio
async def test_trace_decorator():
    """Test trace decorator"""
    from monitoring.tracing import setup_tracing, trace_async
    
    # Setup tracing
    setup_tracing(
        service_name="test-service",
        export_to_console=False,
        export_to_jaeger=False
    )
    
    # Decorated function
    @trace_async()
    async def test_function():
        return "success"
    
    result = await test_function()
    assert result == "success"


def test_monitoring_middleware_creation():
    """Test monitoring middleware can be created"""
    from monitoring.middleware import MonitoringMiddleware
    from fastapi import FastAPI
    
    app = FastAPI()
    
    # Should not raise errors
    middleware = MonitoringMiddleware(app, service_name="test")
    assert middleware is not None


@pytest.mark.asyncio
async def test_full_health_check():
    """Test full health check system"""
    from monitoring.health import HealthChecker
    import tempfile
    import sqlite3
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        # Create test database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()
        
        # Create health checker
        checker = HealthChecker(
            db_path=str(db_path),
            chromadb_path=str(Path(tmpdir) / "chromadb")
        )
        
        # Perform full health check
        health = await checker.check_health(detailed=False)
        
        assert health is not None
        assert health.status in ["healthy", "degraded", "unhealthy"]
        assert health.timestamp is not None
        assert health.overall_response_time_ms >= 0
        assert len(health.components) > 0


def test_pii_masking():
    """Test PII masking functionality"""
    from monitoring.logging import mask_pii
    
    # Test email masking
    email = "john.doe@example.com"
    masked = mask_pii(email)
    assert "***" in masked
    assert "@" in masked
    
    # Test phone masking
    phone = "555-123-4567"
    masked = mask_pii(phone)
    assert "***" in masked
    
    # Test SSN masking
    ssn = "123-45-6789"
    masked = mask_pii(ssn)
    assert "***" in masked
    
    # Test credit card masking
    cc = "4111-1111-1111-1111"
    masked = mask_pii(cc)
    assert "****" in masked
    assert "4111" in masked  # First 4 digits preserved
    assert "1111" in masked  # Last 4 digits preserved
    
    # Test IP masking
    ip = "192.168.1.100"
    masked = mask_pii(ip)
    assert "*" in masked
    
    # Test non-PII text unchanged
    normal_text = "Hello world 123"
    assert mask_pii(normal_text) == normal_text


if __name__ == "__main__":
    print("Running monitoring tests...")
    print("\nTest 1: Imports")
    test_health_checker_import()
    test_metrics_import()
    test_logging_import()
    test_tracing_import()
    test_middleware_import()
    print("✓ All imports successful")
    
    print("\nTest 2: Metrics")
    test_metrics_collector()
    print("✓ Metrics collector works")
    
    print("\nTest 3: Logging")
    test_structured_logging()
    print("✓ Structured logging works")
    
    print("\nTest 4: Tracing")
    test_tracing_setup()
    print("✓ Tracing setup works")
    
    print("\nTest 5: PII Masking")
    test_pii_masking()
    print("✓ PII masking works")
    
    print("\nTest 6: Health Checks")
    asyncio.run(test_health_checker_basic())
    print("✓ Health checker works")
    
    asyncio.run(test_full_health_check())
    print("✓ Full health check works")
    
    print("\nTest 7: Trace Decorator")
    asyncio.run(test_trace_decorator())
    print("✓ Trace decorator works")
    
    print("\n✅ All monitoring tests passed!")
    print("\nMonitoring system is ready to use.")
    print("See docs/monitoring_guide.md for integration instructions.")
