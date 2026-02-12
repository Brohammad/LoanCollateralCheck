"""
Chaos Engineering Tests

Tests system resilience under failure conditions:
- Service failures
- Network latency
- Database failures
- Cache failures
- Partial outages
- Cascading failures
"""

import pytest
import asyncio
import time
from typing import Dict, Any
from unittest.mock import patch, Mock

from httpx import AsyncClient
from app.main import app


class TestChaosScenarios:
    """Chaos engineering test scenarios"""
    
    @pytest.fixture
    async def test_client(self):
        """Create test client"""
        async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_database_failure_resilience(self, test_client: AsyncClient):
        """
        Test system resilience when database is unavailable
        
        Expected: Graceful degradation, cached data used, appropriate errors
        """
        
        # First establish baseline
        baseline_response = await test_client.post(
            "/routing/classify",
            json={
                "user_input": "I need help",
                "user_id": "chaos_user"
            }
        )
        assert baseline_response.status_code == 200
        
        # Simulate database failure
        with patch('app.database.db_manager.DBManager.get_connection') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            # System should handle gracefully
            chaos_response = await test_client.post(
                "/routing/classify",
                json={
                    "user_input": "I need help",
                    "user_id": "chaos_user"
                }
            )
            
            # Should either:
            # 1. Return cached result (200)
            # 2. Return service unavailable (503) with proper error
            assert chaos_response.status_code in [200, 503]
            
            if chaos_response.status_code == 503:
                error_data = chaos_response.json()
                assert "error" in error_data or "detail" in error_data
                assert "database" in str(error_data).lower() or "unavailable" in str(error_data).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_external_service_timeout(self, test_client: AsyncClient):
        """
        Test system behavior when external services timeout
        
        Expected: Timeouts handled, fallback mechanisms used
        """
        
        with patch('app.linkedin.linkedin_service.LinkedInService.parse_profile') as mock_linkedin:
            # Simulate slow external service
            async def slow_service(*args, **kwargs):
                await asyncio.sleep(10)  # Longer than timeout
                return {}
            
            mock_linkedin.side_effect = slow_service
            
            start = time.perf_counter()
            
            response = await test_client.post(
                "/linkedin/parse-profile",
                json={
                    "user_id": "chaos_user",
                    "profile_url": "https://linkedin.com/in/test"
                }
            )
            
            end = time.perf_counter()
            duration = end - start
            
            # Should timeout quickly (not wait 10 seconds)
            assert duration < 5, f"Request took {duration:.2f}s, timeout not enforced"
            
            # Should return timeout error
            assert response.status_code in [408, 504]  # Request Timeout or Gateway Timeout
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_cache_failure_resilience(self, test_client: AsyncClient):
        """
        Test system when cache (Redis) is unavailable
        
        Expected: Continue operation without cache, slight latency increase acceptable
        """
        
        with patch('app.cache.redis_client.RedisClient.get') as mock_redis_get, \
             patch('app.cache.redis_client.RedisClient.set') as mock_redis_set:
            
            # Simulate Redis failure
            mock_redis_get.side_effect = Exception("Redis connection failed")
            mock_redis_set.side_effect = Exception("Redis connection failed")
            
            # System should still work (without cache)
            response = await test_client.post(
                "/routing/classify",
                json={
                    "user_input": "Apply for loan",
                    "user_id": "chaos_user"
                }
            )
            
            # Should succeed despite cache failure
            assert response.status_code == 200
            intent_data = response.json()
            assert intent_data["intent_type"] == "LOAN_APPLICATION"
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_partial_service_outage(self, test_client: AsyncClient):
        """
        Test system during partial outage (some services down)
        
        Expected: Available services continue working
        """
        
        # Credit service down
        with patch('app.credit.credit_service.CreditService.check_credit') as mock_credit:
            mock_credit.side_effect = Exception("Credit service unavailable")
            
            # LinkedIn service should still work
            linkedin_response = await test_client.post(
                "/linkedin/parse-profile",
                json={
                    "user_id": "chaos_user",
                    "profile_url": "https://linkedin.com/in/test"
                }
            )
            
            # LinkedIn should work independently
            assert linkedin_response.status_code in [200, 404]  # Success or not found (acceptable)
            
            # Credit check should fail gracefully
            credit_response = await test_client.get("/credit/history/chaos_user")
            assert credit_response.status_code in [503, 500]
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_network_latency_injection(self, test_client: AsyncClient):
        """
        Test system behavior under high network latency
        
        Expected: Timeouts prevent cascade, circuit breaker activates
        """
        
        async def add_latency(*args, **kwargs):
            await asyncio.sleep(2)  # Add 2 second latency
            return {"result": "delayed"}
        
        with patch('httpx.AsyncClient.post', side_effect=add_latency):
            start = time.perf_counter()
            
            # Make multiple requests
            tasks = []
            for i in range(10):
                task = test_client.post(
                    "/routing/classify",
                    json={"user_input": f"Request {i}", "user_id": "chaos_user"}
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end = time.perf_counter()
            
            # Circuit breaker should kick in
            # Not all requests should take full 2 seconds
            avg_duration = (end - start) / len(tasks)
            assert avg_duration < 2, f"Circuit breaker not working, avg duration: {avg_duration:.2f}s"
            
            # Some requests may fail fast
            failures = sum(1 for r in results if isinstance(r, Exception) or (hasattr(r, 'status_code') and r.status_code >= 500))
            assert failures > 0, "Circuit breaker should cause some fast failures"
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_cascading_failure_prevention(self, test_client: AsyncClient):
        """
        Test prevention of cascading failures
        
        Expected: Failure in one component doesn't bring down entire system
        """
        
        # Simulate auth service failure
        with patch('app.security.auth_service.AuthService.verify_token') as mock_auth:
            mock_auth.side_effect = Exception("Auth service down")
            
            # Public endpoints should still work
            public_response = await test_client.get("/health")
            assert public_response.status_code == 200
            
            # Protected endpoints should fail gracefully
            protected_response = await test_client.get(
                "/loans/history/chaos_user",
                headers={"Authorization": "Bearer fake_token"}
            )
            assert protected_response.status_code in [401, 503]
            
            # System health endpoint should report degraded state
            health_data = public_response.json()
            # May show degraded but not down
            assert "status" in health_data
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_resource_exhaustion(self, test_client: AsyncClient):
        """
        Test behavior when resources are exhausted
        
        Expected: Rate limiting, graceful rejection, no crashes
        """
        
        # Flood with requests
        num_requests = 1000
        concurrency = 100
        
        async def send_request():
            try:
                response = await test_client.post(
                    "/routing/classify",
                    json={"user_input": "Flood test", "user_id": "chaos_user"}
                )
                return response.status_code
            except Exception as e:
                return 500
        
        # Send flood
        results = []
        for i in range(0, num_requests, concurrency):
            batch = [send_request() for _ in range(min(concurrency, num_requests - i))]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)
        
        # Count status codes
        status_counts = {}
        for status in results:
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\n=== Resource Exhaustion Results ===")
        for status, count in sorted(status_counts.items()):
            print(f"Status {status}: {count} requests")
        
        # Should have rate limiting (429) or successful (200)
        # Should NOT crash (500 should be minimal)
        crash_rate = status_counts.get(500, 0) / num_requests
        assert crash_rate < 0.1, f"Crash rate {crash_rate:.2%} too high"
        
        # Rate limiting should be in effect
        rate_limited = status_counts.get(429, 0)
        assert rate_limited > 0, "Rate limiting not active during flood"
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_data_corruption_handling(self, test_client: AsyncClient):
        """
        Test handling of corrupted data
        
        Expected: Validation catches corruption, appropriate errors returned
        """
        
        # Send malformed requests
        malformed_requests = [
            {"user_input": "", "user_id": "chaos_user"},  # Empty input
            {"user_input": "A" * 10000, "user_id": "chaos_user"},  # Oversized input
            {"user_input": None, "user_id": "chaos_user"},  # Null input
            {"user_input": "Test", "user_id": ""},  # Empty user ID
            {"user_input": "Test"},  # Missing user ID
            {},  # Empty payload
        ]
        
        for malformed_req in malformed_requests:
            response = await test_client.post(
                "/routing/classify",
                json=malformed_req
            )
            
            # Should reject with validation error (422) or bad request (400)
            # Should NOT crash (500)
            assert response.status_code in [400, 422], \
                f"Malformed request not properly rejected: {malformed_req}"
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_dependency_failure_isolation(self, test_client: AsyncClient):
        """
        Test that dependency failures are isolated
        
        Expected: Independent services continue working
        """
        
        # Test matrix: Each service failure should not affect others
        service_tests = []
        
        # Test 1: Gemini AI failure shouldn't stop routing
        with patch('app.gemini_client.GeminiClient.generate') as mock_gemini:
            mock_gemini.side_effect = Exception("Gemini API error")
            
            response = await test_client.post(
                "/routing/classify",
                json={"user_input": "Test", "user_id": "chaos_user"}
            )
            # Should work with pattern-based classification (no Gemini needed)
            service_tests.append(("Gemini failure -> Routing works", response.status_code == 200))
        
        # Test 2: Cost tracking failure shouldn't stop operations
        with patch('app.cost_analysis.usage_tracker.UsageTracker.track') as mock_cost:
            mock_cost.side_effect = Exception("Cost tracking error")
            
            response = await test_client.post(
                "/routing/classify",
                json={"user_input": "Test", "user_id": "chaos_user"}
            )
            # Classification should still work
            service_tests.append(("Cost tracking failure -> Routing works", response.status_code == 200))
        
        # Test 3: Monitoring failure shouldn't stop operations
        with patch('app.monitoring.metrics.counter.inc') as mock_metrics:
            mock_metrics.side_effect = Exception("Metrics error")
            
            response = await test_client.post(
                "/routing/classify",
                json={"user_input": "Test", "user_id": "chaos_user"}
            )
            # Should continue despite monitoring failure
            service_tests.append(("Monitoring failure -> Routing works", response.status_code == 200))
        
        # Print results
        print(f"\n=== Dependency Isolation Results ===")
        for test_name, passed in service_tests:
            status = "✓" if passed else "✗"
            print(f"{status} {test_name}")
        
        # All isolation tests should pass
        assert all(passed for _, passed in service_tests), "Some dependencies not properly isolated"
    
    @pytest.mark.asyncio
    @pytest.mark.chaos
    async def test_recovery_after_failure(self, test_client: AsyncClient):
        """
        Test system recovery after temporary failure
        
        Expected: System recovers automatically when service returns
        """
        
        failure_active = True
        
        def conditional_failure(*args, **kwargs):
            if failure_active:
                raise Exception("Service temporarily down")
            return Mock(status_code=200, json=lambda: {"result": "success"})
        
        with patch('httpx.AsyncClient.get', side_effect=conditional_failure):
            # During failure
            response1 = await test_client.get("/external/test")
            assert response1.status_code >= 500, "Failure not detected"
            
            # Service recovers
            failure_active = False
            
            # After recovery
            response2 = await test_client.get("/external/test")
            # May still fail due to circuit breaker cooldown, but should recover soon
            
            # Wait for circuit breaker reset
            await asyncio.sleep(2)
            
            response3 = await test_client.get("/external/test")
            # Should work now
            assert response3.status_code in [200, 404], "System didn't recover"
        
        print("\n=== Recovery Test ===")
        print(f"During failure: {response1.status_code}")
        print(f"Immediate recovery: {response2.status_code}")
        print(f"After cooldown: {response3.status_code}")
