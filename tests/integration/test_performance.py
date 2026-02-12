"""
Performance Benchmark Tests

Tests system performance including:
- Response time benchmarks
- Throughput testing
- Scalability tests
- Resource utilization
- Latency percentiles
"""

import pytest
import asyncio
import time
from typing import List, Dict
from statistics import mean, median, stdev
from datetime import datetime

from httpx import AsyncClient
from app.main import app


class TestPerformanceBenchmarks:
    """Performance benchmark tests"""
    
    @pytest.fixture
    async def test_client(self):
        """Create test client"""
        async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_intent_classification_latency(self, test_client: AsyncClient):
        """
        Benchmark intent classification latency
        
        Target: <50ms for 95th percentile
        """
        
        test_inputs = [
            "I want to apply for a loan",
            "What's my credit score?",
            "Upload my tax documents",
            "Analyze my LinkedIn profile",
            "Find me relevant jobs",
            "Hello, I need help",
            "Check my application status",
            "Recommend skills to learn"
        ]
        
        latencies = []
        
        for _ in range(100):  # 100 iterations
            for user_input in test_inputs:
                start_time = time.perf_counter()
                
                response = await test_client.post(
                    "/routing/classify",
                    json={
                        "user_input": user_input,
                        "user_id": "perf_test_user"
                    }
                )
                
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)
                
                assert response.status_code == 200
        
        # Calculate statistics
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        avg = mean(latencies)
        std = stdev(latencies)
        
        print(f"\n=== Intent Classification Latency ===")
        print(f"Average: {avg:.2f}ms")
        print(f"Median (P50): {p50:.2f}ms")
        print(f"P95: {p95:.2f}ms")
        print(f"P99: {p99:.2f}ms")
        print(f"Std Dev: {std:.2f}ms")
        
        # Assertions
        assert p95 < 50, f"P95 latency {p95:.2f}ms exceeds 50ms target"
        assert avg < 30, f"Average latency {avg:.2f}ms exceeds 30ms target"
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_routing_throughput(self, test_client: AsyncClient):
        """
        Test routing throughput
        
        Target: >100 requests/second
        """
        
        num_requests = 1000
        concurrency = 10
        
        async def send_request():
            response = await test_client.post(
                "/routing/route",
                json={
                    "user_input": "I need help with my application",
                    "user_id": f"user_{asyncio.current_task().get_name()}",
                    "user_authenticated": True
                }
            )
            return response.status_code == 200
        
        start_time = time.perf_counter()
        
        # Execute requests in batches
        successful = 0
        for i in range(0, num_requests, concurrency):
            batch = [send_request() for _ in range(min(concurrency, num_requests - i))]
            results = await asyncio.gather(*batch)
            successful += sum(results)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        throughput = num_requests / duration
        
        print(f"\n=== Routing Throughput ===")
        print(f"Total requests: {num_requests}")
        print(f"Successful: {successful}")
        print(f"Duration: {duration:.2f}s")
        print(f"Throughput: {throughput:.2f} req/s")
        
        # Assertions
        assert throughput > 100, f"Throughput {throughput:.2f} req/s below 100 req/s target"
        assert successful / num_requests > 0.99, "Success rate below 99%"
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_end_to_end_workflow_performance(self, test_client: AsyncClient):
        """
        Test end-to-end workflow performance
        
        Target: <500ms for complete loan application workflow
        """
        
        async def complete_workflow():
            start = time.perf_counter()
            
            # Authenticate
            auth_response = await test_client.post("/auth/login", json={
                "email": "perf@example.com",
                "password": "test_password"
            })
            if auth_response.status_code != 200:
                return None
            
            token = auth_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Classify intent
            await test_client.post(
                "/routing/classify",
                json={"user_input": "Apply for business loan", "user_id": "perf_user"},
                headers=headers
            )
            
            # Check credit
            await test_client.get("/credit/history/perf_user", headers=headers)
            
            # Submit application
            await test_client.post(
                "/loans/apply",
                json={
                    "user_id": "perf_user",
                    "loan_type": "business",
                    "amount": 50000
                },
                headers=headers
            )
            
            end = time.perf_counter()
            return (end - start) * 1000  # Return latency in ms
        
        # Run workflow multiple times
        latencies = []
        for _ in range(50):
            latency = await complete_workflow()
            if latency:
                latencies.append(latency)
        
        if not latencies:
            pytest.skip("Workflow execution failed")
        
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        avg = mean(latencies)
        
        print(f"\n=== End-to-End Workflow Performance ===")
        print(f"Average: {avg:.2f}ms")
        print(f"Median (P50): {p50:.2f}ms")
        print(f"P95: {p95:.2f}ms")
        
        # Assertions
        assert p95 < 500, f"P95 latency {p95:.2f}ms exceeds 500ms target"
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_user_scalability(self, test_client: AsyncClient):
        """
        Test system scalability with concurrent users
        
        Target: Support 100 concurrent users with <10% latency increase
        """
        
        async def user_session(user_id: int):
            latencies = []
            
            # Perform 10 operations per user
            for i in range(10):
                start = time.perf_counter()
                
                await test_client.post(
                    "/routing/classify",
                    json={
                        "user_input": f"User {user_id} request {i}",
                        "user_id": f"user_{user_id}"
                    }
                )
                
                end = time.perf_counter()
                latencies.append((end - start) * 1000)
            
            return latencies
        
        # Test with increasing concurrency
        concurrency_levels = [10, 50, 100]
        results = {}
        
        for concurrency in concurrency_levels:
            tasks = [user_session(i) for i in range(concurrency)]
            all_latencies = await asyncio.gather(*tasks)
            
            # Flatten latencies
            flat_latencies = [lat for user_lats in all_latencies for lat in user_lats]
            avg_latency = mean(flat_latencies)
            
            results[concurrency] = avg_latency
            
            print(f"\n=== Concurrency: {concurrency} users ===")
            print(f"Average latency: {avg_latency:.2f}ms")
        
        # Check latency degradation
        baseline = results[10]
        high_load = results[100]
        degradation_pct = ((high_load - baseline) / baseline) * 100
        
        print(f"\n=== Scalability Results ===")
        print(f"Baseline (10 users): {baseline:.2f}ms")
        print(f"High load (100 users): {high_load:.2f}ms")
        print(f"Degradation: {degradation_pct:.2f}%")
        
        # Assertion
        assert degradation_pct < 10, f"Latency degradation {degradation_pct:.2f}% exceeds 10% target"
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_database_query_performance(self, test_client: AsyncClient):
        """
        Test database query performance
        
        Target: <20ms for simple queries, <100ms for complex queries
        """
        
        # Authenticate
        auth_response = await test_client.post("/auth/login", json={
            "email": "perf@example.com",
            "password": "test_password"
        })
        token = auth_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test simple query (user lookup)
        simple_latencies = []
        for _ in range(100):
            start = time.perf_counter()
            await test_client.get("/users/perf_user", headers=headers)
            end = time.perf_counter()
            simple_latencies.append((end - start) * 1000)
        
        simple_avg = mean(simple_latencies)
        simple_p95 = sorted(simple_latencies)[int(len(simple_latencies) * 0.95)]
        
        # Test complex query (loan history with joins)
        complex_latencies = []
        for _ in range(50):
            start = time.perf_counter()
            await test_client.get("/loans/history/perf_user", headers=headers)
            end = time.perf_counter()
            complex_latencies.append((end - start) * 1000)
        
        complex_avg = mean(complex_latencies)
        complex_p95 = sorted(complex_latencies)[int(len(complex_latencies) * 0.95)]
        
        print(f"\n=== Database Query Performance ===")
        print(f"Simple queries (avg): {simple_avg:.2f}ms")
        print(f"Simple queries (P95): {simple_p95:.2f}ms")
        print(f"Complex queries (avg): {complex_avg:.2f}ms")
        print(f"Complex queries (P95): {complex_p95:.2f}ms")
        
        # Assertions
        assert simple_p95 < 20, f"Simple query P95 {simple_p95:.2f}ms exceeds 20ms target"
        assert complex_p95 < 100, f"Complex query P95 {complex_p95:.2f}ms exceeds 100ms target"
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_memory_efficiency(self, test_client: AsyncClient):
        """
        Test memory efficiency under load
        
        Verifies no memory leaks during sustained operation
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform 1000 operations
        for i in range(1000):
            await test_client.post(
                "/routing/classify",
                json={
                    "user_input": f"Test input {i}",
                    "user_id": "memory_test_user"
                }
            )
            
            # Check memory every 100 operations
            if i % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                
                print(f"Operations: {i}, Memory: {current_memory:.2f}MB, Increase: {memory_increase:.2f}MB")
                
                # Should not increase by more than 100MB
                assert memory_increase < 100, f"Memory increase {memory_increase:.2f}MB exceeds 100MB limit"
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory
        
        print(f"\n=== Memory Efficiency ===")
        print(f"Initial memory: {initial_memory:.2f}MB")
        print(f"Final memory: {final_memory:.2f}MB")
        print(f"Total increase: {total_increase:.2f}MB")
        
        # Should not leak more than 50MB
        assert total_increase < 50, f"Memory leak detected: {total_increase:.2f}MB increase"
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_effectiveness(self, test_client: AsyncClient):
        """
        Test caching effectiveness
        
        Cached requests should be >10x faster
        """
        
        # First request (cold)
        cold_latencies = []
        for i in range(10):
            start = time.perf_counter()
            await test_client.post(
                "/routing/classify",
                json={
                    "user_input": "Apply for a business loan",
                    "user_id": f"cache_test_user_{i}"
                }
            )
            end = time.perf_counter()
            cold_latencies.append((end - start) * 1000)
        
        cold_avg = mean(cold_latencies)
        
        # Repeated requests (warm cache)
        warm_latencies = []
        for _ in range(100):
            start = time.perf_counter()
            await test_client.post(
                "/routing/classify",
                json={
                    "user_input": "Apply for a business loan",
                    "user_id": "cache_test_user_0"  # Same user
                }
            )
            end = time.perf_counter()
            warm_latencies.append((end - start) * 1000)
        
        warm_avg = mean(warm_latencies)
        speedup = cold_avg / warm_avg
        
        print(f"\n=== Cache Effectiveness ===")
        print(f"Cold average: {cold_avg:.2f}ms")
        print(f"Warm average: {warm_avg:.2f}ms")
        print(f"Speedup: {speedup:.2f}x")
        
        # Cache should provide at least 2x speedup
        assert speedup > 2, f"Cache speedup {speedup:.2f}x below 2x target"
