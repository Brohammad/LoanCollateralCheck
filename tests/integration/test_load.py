"""
Load Testing Suite

Comprehensive load tests including:
- Sustained load testing
- Spike testing
- Stress testing
- Soak testing (endurance)
- Volume testing
"""

import pytest
import asyncio
import time
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from statistics import mean

from httpx import AsyncClient
from app.main import app


class TestLoadScenarios:
    """Load testing scenarios"""
    
    @pytest.fixture
    async def test_client(self):
        """Create test client"""
        async with AsyncClient(app=app, base_url="http://test", timeout=60.0) as client:
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_sustained_load(self, test_client: AsyncClient):
        """
        Sustained load test
        
        Simulate 50 concurrent users for 5 minutes
        Target: Maintain <100ms average latency, >99% success rate
        """
        
        duration_seconds = 300  # 5 minutes
        concurrent_users = 50
        requests_per_user_per_minute = 10
        
        results = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "latencies": [],
            "errors": []
        }
        
        async def user_load(user_id: int, duration: int):
            """Simulate user activity"""
            start_time = time.time()
            requests_made = 0
            
            while time.time() - start_time < duration:
                try:
                    request_start = time.perf_counter()
                    
                    response = await test_client.post(
                        "/routing/route",
                        json={
                            "user_input": f"I need help with my application",
                            "user_id": f"load_user_{user_id}",
                            "user_authenticated": True
                        }
                    )
                    
                    request_end = time.perf_counter()
                    latency_ms = (request_end - request_start) * 1000
                    
                    results["total_requests"] += 1
                    results["latencies"].append(latency_ms)
                    
                    if response.status_code == 200:
                        results["successful_requests"] += 1
                    else:
                        results["failed_requests"] += 1
                        results["errors"].append(f"Status {response.status_code}")
                    
                    requests_made += 1
                    
                    # Wait to maintain request rate
                    await asyncio.sleep(60 / requests_per_user_per_minute)
                
                except Exception as e:
                    results["failed_requests"] += 1
                    results["errors"].append(str(e))
        
        # Start user simulations
        start_time = time.time()
        tasks = [user_load(i, duration_seconds) for i in range(concurrent_users)]
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Calculate results
        actual_duration = end_time - start_time
        avg_latency = mean(results["latencies"]) if results["latencies"] else 0
        success_rate = (results["successful_requests"] / results["total_requests"]) * 100 if results["total_requests"] > 0 else 0
        throughput = results["total_requests"] / actual_duration
        
        print(f"\n=== Sustained Load Test Results ===")
        print(f"Duration: {actual_duration:.2f}s")
        print(f"Concurrent users: {concurrent_users}")
        print(f"Total requests: {results['total_requests']}")
        print(f"Successful: {results['successful_requests']}")
        print(f"Failed: {results['failed_requests']}")
        print(f"Average latency: {avg_latency:.2f}ms")
        print(f"Success rate: {success_rate:.2f}%")
        print(f"Throughput: {throughput:.2f} req/s")
        
        # Assertions
        assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms exceeds 100ms target"
        assert success_rate > 99, f"Success rate {success_rate:.2f}% below 99% target"
    
    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_spike_load(self, test_client: AsyncClient):
        """
        Spike load test
        
        Sudden increase from 10 to 100 users
        Target: Handle spike with <20% latency increase
        """
        
        async def measure_latency(num_users: int, num_requests: int):
            """Measure average latency for given load"""
            
            async def send_request():
                start = time.perf_counter()
                response = await test_client.post(
                    "/routing/classify",
                    json={
                        "user_input": "I need help",
                        "user_id": f"spike_user_{asyncio.current_task().get_name()}"
                    }
                )
                end = time.perf_counter()
                return (end - start) * 1000, response.status_code == 200
            
            latencies = []
            successes = 0
            
            for _ in range(0, num_requests, num_users):
                batch_size = min(num_users, num_requests - len(latencies))
                batch = [send_request() for _ in range(batch_size)]
                results = await asyncio.gather(*batch)
                
                for latency, success in results:
                    latencies.append(latency)
                    if success:
                        successes += 1
            
            return mean(latencies), (successes / num_requests) * 100
        
        # Baseline load (10 users)
        print("\n=== Baseline Load (10 users) ===")
        baseline_latency, baseline_success = await measure_latency(10, 100)
        print(f"Average latency: {baseline_latency:.2f}ms")
        print(f"Success rate: {baseline_success:.2f}%")
        
        # Spike load (100 users)
        print("\n=== Spike Load (100 users) ===")
        spike_latency, spike_success = await measure_latency(100, 1000)
        print(f"Average latency: {spike_latency:.2f}ms")
        print(f"Success rate: {spike_success:.2f}%")
        
        # Calculate degradation
        latency_increase_pct = ((spike_latency - baseline_latency) / baseline_latency) * 100
        
        print(f"\n=== Spike Impact ===")
        print(f"Latency increase: {latency_increase_pct:.2f}%")
        
        # Assertions
        assert latency_increase_pct < 20, f"Latency increase {latency_increase_pct:.2f}% exceeds 20% target"
        assert spike_success > 95, f"Spike success rate {spike_success:.2f}% below 95% target"
    
    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_stress_test(self, test_client: AsyncClient):
        """
        Stress test to find breaking point
        
        Gradually increase load until failure
        Target: Identify maximum capacity
        """
        
        async def test_load_level(concurrent_users: int, requests: int):
            """Test specific load level"""
            
            async def send_request():
                try:
                    start = time.perf_counter()
                    response = await test_client.post(
                        "/routing/classify",
                        json={
                            "user_input": "Stress test",
                            "user_id": "stress_user"
                        }
                    )
                    end = time.perf_counter()
                    return (end - start) * 1000, response.status_code == 200, None
                except Exception as e:
                    return None, False, str(e)
            
            latencies = []
            successes = 0
            errors = []
            
            for _ in range(0, requests, concurrent_users):
                batch_size = min(concurrent_users, requests - len(latencies))
                batch = [send_request() for _ in range(batch_size)]
                results = await asyncio.gather(*batch)
                
                for latency, success, error in results:
                    if latency:
                        latencies.append(latency)
                    if success:
                        successes += 1
                    if error:
                        errors.append(error)
            
            success_rate = (successes / requests) * 100
            avg_latency = mean(latencies) if latencies else float('inf')
            
            return avg_latency, success_rate, len(errors)
        
        # Test increasing load levels
        load_levels = [10, 25, 50, 100, 200, 500]
        results = []
        
        print(f"\n=== Stress Test Results ===")
        
        for level in load_levels:
            avg_latency, success_rate, error_count = await test_load_level(level, 100)
            results.append({
                "level": level,
                "latency": avg_latency,
                "success_rate": success_rate,
                "errors": error_count
            })
            
            print(f"Load level {level}: Latency={avg_latency:.2f}ms, Success={success_rate:.2f}%, Errors={error_count}")
            
            # Stop if performance degrades significantly
            if success_rate < 90 or avg_latency > 500:
                print(f"Breaking point reached at {level} concurrent users")
                break
        
        # Find maximum sustainable load
        sustainable_loads = [r for r in results if r["success_rate"] > 95 and r["latency"] < 200]
        max_sustainable = max(sustainable_loads, key=lambda x: x["level"]) if sustainable_loads else results[0]
        
        print(f"\n=== Maximum Sustainable Load ===")
        print(f"Concurrent users: {max_sustainable['level']}")
        print(f"Latency: {max_sustainable['latency']:.2f}ms")
        print(f"Success rate: {max_sustainable['success_rate']:.2f}%")
        
        # Should handle at least 50 concurrent users
        assert max_sustainable["level"] >= 50, f"System capacity {max_sustainable['level']} below minimum 50"
    
    @pytest.mark.asyncio
    @pytest.mark.load
    @pytest.mark.slow
    async def test_soak_test(self, test_client: AsyncClient):
        """
        Soak test (endurance test)
        
        Moderate load for extended period (1 hour simulated as 10 minutes)
        Target: No memory leaks, stable performance
        """
        
        duration_seconds = 600  # 10 minutes (simulating 1 hour)
        concurrent_users = 20
        
        results = {
            "intervals": [],
            "total_requests": 0,
            "total_successes": 0
        }
        
        async def user_activity():
            """Simulate continuous user activity"""
            while True:
                try:
                    start = time.perf_counter()
                    response = await test_client.post(
                        "/routing/classify",
                        json={
                            "user_input": "Soak test request",
                            "user_id": f"soak_user_{asyncio.current_task().get_name()}"
                        }
                    )
                    end = time.perf_counter()
                    
                    results["total_requests"] += 1
                    if response.status_code == 200:
                        results["total_successes"] += 1
                    
                    await asyncio.sleep(1)  # 1 request per second per user
                
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    pass
        
        # Start user tasks
        tasks = [asyncio.create_task(user_activity()) for _ in range(concurrent_users)]
        
        # Monitor performance over time
        start_time = time.time()
        interval_duration = 60  # Check every minute
        
        print(f"\n=== Soak Test (Duration: {duration_seconds}s) ===")
        
        while time.time() - start_time < duration_seconds:
            await asyncio.sleep(interval_duration)
            
            elapsed = time.time() - start_time
            requests_in_interval = results["total_requests"]
            successes_in_interval = results["total_successes"]
            success_rate = (successes_in_interval / requests_in_interval * 100) if requests_in_interval > 0 else 0
            
            interval_result = {
                "elapsed": elapsed,
                "requests": requests_in_interval,
                "success_rate": success_rate
            }
            results["intervals"].append(interval_result)
            
            print(f"Elapsed: {elapsed:.0f}s, Requests: {requests_in_interval}, Success: {success_rate:.2f}%")
        
        # Stop user tasks
        for task in tasks:
            task.cancel()
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze stability
        success_rates = [interval["success_rate"] for interval in results["intervals"]]
        avg_success_rate = mean(success_rates)
        success_rate_variance = max(success_rates) - min(success_rates)
        
        print(f"\n=== Soak Test Results ===")
        print(f"Total requests: {results['total_requests']}")
        print(f"Average success rate: {avg_success_rate:.2f}%")
        print(f"Success rate variance: {success_rate_variance:.2f}%")
        
        # Assertions
        assert avg_success_rate > 99, f"Average success rate {avg_success_rate:.2f}% below 99%"
        assert success_rate_variance < 5, f"Success rate variance {success_rate_variance:.2f}% exceeds 5%"
    
    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_volume_test(self, test_client: AsyncClient):
        """
        Volume test
        
        Process large volumes of data
        Target: Handle 10,000 intents without degradation
        """
        
        num_intents = 10000
        batch_size = 100
        
        results = {
            "processed": 0,
            "failed": 0,
            "batch_latencies": []
        }
        
        print(f"\n=== Volume Test (Processing {num_intents} intents) ===")
        
        for batch_num in range(0, num_intents, batch_size):
            batch_start = time.perf_counter()
            
            # Process batch
            batch_tasks = []
            for i in range(batch_size):
                task = test_client.post(
                    "/routing/classify",
                    json={
                        "user_input": f"Volume test intent {batch_num + i}",
                        "user_id": "volume_test_user"
                    }
                )
                batch_tasks.append(task)
            
            responses = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            batch_end = time.perf_counter()
            batch_latency = (batch_end - batch_start) * 1000
            results["batch_latencies"].append(batch_latency)
            
            # Count results
            for response in responses:
                if isinstance(response, Exception):
                    results["failed"] += 1
                elif response.status_code == 200:
                    results["processed"] += 1
                else:
                    results["failed"] += 1
            
            # Progress update every 1000
            if (batch_num + batch_size) % 1000 == 0:
                print(f"Processed: {batch_num + batch_size}/{num_intents}")
        
        # Calculate statistics
        avg_batch_latency = mean(results["batch_latencies"])
        success_rate = (results["processed"] / num_intents) * 100
        
        print(f"\n=== Volume Test Results ===")
        print(f"Total intents: {num_intents}")
        print(f"Processed: {results['processed']}")
        print(f"Failed: {results['failed']}")
        print(f"Success rate: {success_rate:.2f}%")
        print(f"Average batch latency: {avg_batch_latency:.2f}ms")
        
        # Assertions
        assert success_rate > 99, f"Success rate {success_rate:.2f}% below 99%"
        assert avg_batch_latency < 1000, f"Batch latency {avg_batch_latency:.2f}ms exceeds 1000ms"
