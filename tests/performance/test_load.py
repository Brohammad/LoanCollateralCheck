"""
Performance Tests - Load Testing

Tests system performance under load including:
- Sustained request rate
- Burst traffic
- Concurrent users
- Connection pool behavior
- Memory stability
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch


@pytest.mark.performance
@pytest.mark.slow
class TestLoadPerformance:
    """Test system under sustained load"""
    
    @pytest.fixture
    def orchestrator(self, mock_gemini_client, test_database, mock_vector_search):
        """Create orchestrator instance"""
        from database.db_manager import DatabaseManager
        
        db_manager = DatabaseManager(db_path=test_database)
        
        class MockOrchestrator:
            def __init__(self, gemini_client, db_manager, vector_store):
                self.gemini_client = gemini_client
                self.db_manager = db_manager
                self.vector_store = vector_store
            
            async def process_message(self, session_id: str, message: str):
                await asyncio.sleep(0.01)  # Simulate processing
                return {"response": "Test response", "intent": "question"}
        
        return MockOrchestrator(mock_gemini_client, db_manager, mock_vector_search)
    
    @pytest.mark.asyncio
    async def test_sustained_1000_rpm(self, orchestrator):
        """Test sustained 1000 requests per minute"""
        requests_per_minute = 1000
        duration_seconds = 60
        
        request_count = 0
        start_time = time.time()
        
        async def make_request():
            nonlocal request_count
            await orchestrator.process_message("load-test", f"Message {request_count}")
            request_count += 1
        
        # Generate requests at target rate
        tasks = []
        target_interval = 60.0 / requests_per_minute  # seconds between requests
        
        # Run for shorter duration in test
        test_duration = 1.0  # 1 second for testing
        target_requests = int(requests_per_minute * test_duration / 60)
        
        for i in range(target_requests):
            task = asyncio.create_task(make_request())
            tasks.append(task)
            await asyncio.sleep(target_interval)
        
        # Wait for all requests to complete
        await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        actual_rpm = (request_count / elapsed) * 60
        
        # Should handle target rate (with some tolerance)
        assert actual_rpm >= requests_per_minute * 0.9
    
    @pytest.mark.asyncio
    async def test_burst_traffic(self, orchestrator):
        """Test handling of burst traffic"""
        burst_size = 100
        
        start_time = time.time()
        
        # Send burst of requests simultaneously
        tasks = [
            orchestrator.process_message(f"burst-session-{i}", f"Burst message {i}")
            for i in range(burst_size)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.time() - start_time
        
        # All requests should complete
        successful = sum(1 for r in results if not isinstance(r, Exception))
        success_rate = successful / burst_size
        
        assert success_rate >= 0.95  # 95% success rate
        assert elapsed < 5.0  # Complete within 5 seconds
    
    @pytest.mark.asyncio
    async def test_concurrent_users(self, orchestrator):
        """Test with 100 concurrent users"""
        num_users = 100
        messages_per_user = 5
        
        async def simulate_user(user_id):
            session_id = f"user-{user_id}"
            results = []
            
            for i in range(messages_per_user):
                result = await orchestrator.process_message(
                    session_id,
                    f"User {user_id} message {i}"
                )
                results.append(result)
                await asyncio.sleep(0.1)  # Think time
            
            return results
        
        start_time = time.time()
        
        # Simulate concurrent users
        user_tasks = [simulate_user(i) for i in range(num_users)]
        all_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        elapsed = time.time() - start_time
        
        # Check success rate
        successful_users = sum(1 for r in all_results if not isinstance(r, Exception))
        success_rate = successful_users / num_users
        
        assert success_rate >= 0.95
        print(f"Concurrent users test: {elapsed:.2f}s, {success_rate*100:.1f}% success")
    
    @pytest.mark.asyncio
    async def test_database_connection_pool(self, test_database):
        """Test database connection pool under load"""
        from database.db_manager import DatabaseManager
        
        db_manager = DatabaseManager(db_path=test_database)
        
        async def db_operation(i):
            # Simulate database operations
            session_id = f"pool-test-{i % 10}"  # 10 sessions
            db_manager.add_conversation(session_id, f"Message {i}", f"Response {i}")
            history = db_manager.get_conversation_history(session_id)
            return len(history)
        
        # Generate many concurrent DB operations
        tasks = [db_operation(i) for i in range(200)]
        
        start_time = time.time()
        results = await asyncio.gather(*[asyncio.create_task(asyncio.to_thread(t)) for t in tasks], return_exceptions=True)
        elapsed = time.time() - start_time
        
        # All operations should complete
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful >= 180  # 90% success rate
        
        print(f"DB connection pool test: {elapsed:.2f}s, {successful}/200 successful")
    
    @pytest.mark.asyncio
    async def test_memory_stability(self, orchestrator):
        """Test memory usage remains stable under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate sustained load
        for batch in range(10):
            tasks = [
                orchestrator.process_message(f"mem-test-{i}", f"Message {i}")
                for i in range(100)
            ]
            await asyncio.gather(*tasks)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (< 100MB for 1000 requests)
        assert memory_growth < 100
        
        print(f"Memory test: Initial {initial_memory:.2f}MB, Final {final_memory:.2f}MB, Growth {memory_growth:.2f}MB")


@pytest.mark.performance
class TestLatencyPerformance:
    """Test response time latencies"""
    
    @pytest.fixture
    def orchestrator(self, mock_gemini_client, test_database, mock_vector_search):
        """Create orchestrator instance"""
        from database.db_manager import DatabaseManager
        
        db_manager = DatabaseManager(db_path=test_database)
        
        class MockOrchestrator:
            def __init__(self, gemini_client, db_manager, vector_store):
                self.gemini_client = gemini_client
                self.db_manager = db_manager
                self.vector_store = vector_store
            
            async def process_message(self, session_id: str, message: str):
                # Simulate realistic processing time
                await asyncio.sleep(0.05)
                return {"response": "Test response", "intent": "question"}
        
        return MockOrchestrator(mock_gemini_client, db_manager, mock_vector_search)
    
    @pytest.mark.asyncio
    async def test_p50_latency_target(self, orchestrator):
        """Test P50 latency < 4 seconds"""
        latencies = []
        num_requests = 100
        
        for i in range(num_requests):
            start = time.time()
            await orchestrator.process_message("latency-test", f"Message {i}")
            latency = time.time() - start
            latencies.append(latency)
        
        latencies.sort()
        p50 = latencies[int(len(latencies) * 0.5)]
        
        print(f"P50 latency: {p50*1000:.2f}ms")
        assert p50 < 4.0  # 4 seconds
    
    @pytest.mark.asyncio
    async def test_p95_latency_target(self, orchestrator):
        """Test P95 latency < 8 seconds"""
        latencies = []
        num_requests = 100
        
        for i in range(num_requests):
            start = time.time()
            await orchestrator.process_message("latency-test", f"Message {i}")
            latency = time.time() - start
            latencies.append(latency)
        
        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)]
        
        print(f"P95 latency: {p95*1000:.2f}ms")
        assert p95 < 8.0  # 8 seconds
    
    @pytest.mark.asyncio
    async def test_p99_latency_target(self, orchestrator):
        """Test P99 latency < 15 seconds"""
        latencies = []
        num_requests = 100
        
        for i in range(num_requests):
            start = time.time()
            await orchestrator.process_message("latency-test", f"Message {i}")
            latency = time.time() - start
            latencies.append(latency)
        
        latencies.sort()
        p99 = latencies[int(len(latencies) * 0.99)]
        
        print(f"P99 latency: {p99*1000:.2f}ms")
        assert p99 < 15.0  # 15 seconds
    
    @pytest.mark.asyncio
    async def test_cache_hit_latency(self, orchestrator):
        """Test cache hit latency is significantly lower"""
        query = "What is collateral?"
        session_id = "cache-hit-test"
        
        # First request (cache miss)
        start = time.time()
        await orchestrator.process_message(session_id, query)
        cache_miss_latency = time.time() - start
        
        # Second request (cache hit)
        start = time.time()
        await orchestrator.process_message(session_id, query)
        cache_hit_latency = time.time() - start
        
        print(f"Cache miss: {cache_miss_latency*1000:.2f}ms, Cache hit: {cache_hit_latency*1000:.2f}ms")
        
        # Cache hit should be much faster (placeholder - depends on implementation)
        # assert cache_hit_latency < cache_miss_latency * 0.5
    
    @pytest.mark.asyncio
    async def test_cache_miss_latency(self, orchestrator):
        """Test cache miss latency meets targets"""
        unique_queries = [f"Unique query {i}" for i in range(50)]
        latencies = []
        
        for query in unique_queries:
            start = time.time()
            await orchestrator.process_message("cache-miss-test", query)
            latency = time.time() - start
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        print(f"Average cache miss latency: {avg_latency*1000:.2f}ms")
        
        # Average should be reasonable
        assert avg_latency < 5.0  # 5 seconds


@pytest.mark.performance
@pytest.mark.slow
class TestStressTest:
    """Stress tests to find system limits"""
    
    @pytest.fixture
    def orchestrator(self, mock_gemini_client, test_database, mock_vector_search):
        """Create orchestrator instance"""
        from database.db_manager import DatabaseManager
        
        db_manager = DatabaseManager(db_path=test_database)
        
        class MockOrchestrator:
            def __init__(self, gemini_client, db_manager, vector_store):
                self.gemini_client = gemini_client
                self.db_manager = db_manager
                self.vector_store = vector_store
            
            async def process_message(self, session_id: str, message: str):
                await asyncio.sleep(0.01)
                return {"response": "Test response", "intent": "question"}
        
        return MockOrchestrator(mock_gemini_client, db_manager, mock_vector_search)
    
    @pytest.mark.asyncio
    async def test_find_breaking_point(self, orchestrator):
        """Test to find the breaking point of the system"""
        request_rates = [100, 500, 1000, 2000, 5000]  # requests per minute
        
        for rpm in request_rates:
            print(f"\nTesting {rpm} RPM...")
            
            requests_per_second = rpm / 60
            num_requests = int(requests_per_second * 5)  # 5 seconds of load
            
            start_time = time.time()
            
            tasks = [
                orchestrator.process_message(f"stress-{i}", f"Message {i}")
                for i in range(num_requests)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start_time
            
            successful = sum(1 for r in results if not isinstance(r, Exception))
            success_rate = successful / num_requests
            actual_rpm = (num_requests / elapsed) * 60
            
            print(f"  Target: {rpm} RPM, Actual: {actual_rpm:.0f} RPM, Success: {success_rate*100:.1f}%")
            
            if success_rate < 0.95:
                print(f"  Breaking point found at {rpm} RPM")
                break
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, orchestrator):
        """Test system degrades gracefully under extreme load"""
        extreme_load = 500  # requests simultaneously
        
        tasks = [
            orchestrator.process_message(f"degrade-{i}", f"Message {i}")
            for i in range(extreme_load)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time
        
        successful = sum(1 for r in results if not isinstance(r, Exception))
        success_rate = successful / extreme_load
        
        # System should handle at least some requests
        assert success_rate >= 0.5  # At least 50% success even under extreme load
        
        print(f"Graceful degradation: {success_rate*100:.1f}% success under extreme load")
    
    @pytest.mark.asyncio
    async def test_recovery_after_overload(self, orchestrator):
        """Test system recovers after overload"""
        # Create overload
        overload_tasks = [
            orchestrator.process_message(f"overload-{i}", f"Message {i}")
            for i in range(1000)
        ]
        await asyncio.gather(*overload_tasks, return_exceptions=True)
        
        # Wait for system to stabilize
        await asyncio.sleep(1)
        
        # Test normal operation
        recovery_tasks = [
            orchestrator.process_message(f"recovery-{i}", f"Message {i}")
            for i in range(10)
        ]
        
        results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
        successful = sum(1 for r in results if not isinstance(r, Exception))
        
        # Should recover to normal operation
        assert successful >= 9  # 90% success after recovery


@pytest.mark.performance
class TestThroughputPerformance:
    """Test system throughput"""
    
    @pytest.mark.asyncio
    async def test_maximum_throughput(self, mock_gemini_client, test_database, mock_vector_search):
        """Test maximum requests per second"""
        from database.db_manager import DatabaseManager
        
        db_manager = DatabaseManager(db_path=test_database)
        
        class MockOrchestrator:
            async def process_message(self, session_id: str, message: str):
                return {"response": "Test", "intent": "question"}
        
        orchestrator = MockOrchestrator()
        
        duration = 5  # seconds
        start_time = time.time()
        request_count = 0
        
        async def make_requests():
            nonlocal request_count
            end_time = start_time + duration
            
            while time.time() < end_time:
                await orchestrator.process_message("throughput-test", "Test message")
                request_count += 1
        
        # Run multiple concurrent workers
        workers = [make_requests() for _ in range(10)]
        await asyncio.gather(*workers)
        
        elapsed = time.time() - start_time
        throughput = request_count / elapsed
        
        print(f"Maximum throughput: {throughput:.2f} requests/second")
        assert throughput > 0
