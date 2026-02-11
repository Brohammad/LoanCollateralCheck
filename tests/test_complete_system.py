"""
Comprehensive test suite for the AI Agent system
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path

# Set test environment
os.environ["GEMINI_API_KEY"] = "test_key_12345"
os.environ["SQLITE_DB_PATH"] = ":memory:"


@pytest.fixture
def test_db_path():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if Path(db_path).exists():
        Path(db_path).unlink()


@pytest.fixture
def db_manager(test_db_path):
    """Create a database manager for testing."""
    from database.db_manager import DatabaseManager
    
    # Initialize database
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    db = DatabaseManager(test_db_path)
    db.initialize_database(str(schema_path))
    
    yield db
    
    db.close()


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client for testing."""
    from unittest.mock import AsyncMock, MagicMock
    from app.gemini_enhanced import GeminiClient, GeminiResponse, TokenUsage
    
    client = MagicMock(spec=GeminiClient)
    
    # Mock generate_async
    async def mock_generate(**kwargs):
        return GeminiResponse(
            text="This is a test response.",
            token_usage=TokenUsage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15
            ),
            model_name="test-model",
            latency_ms=100,
            from_cache=False
        )
    
    client.generate_async = mock_generate
    
    # Mock classify_intent
    async def mock_classify(**kwargs):
        return "question", 0.95
    
    client.classify_intent = mock_classify
    
    return client


class TestDatabaseManager:
    """Tests for database manager."""
    
    def test_create_session(self, db_manager):
        """Test session creation."""
        success = db_manager.create_session(
            session_id="test_session_1",
            user_id="test_user_1"
        )
        assert success
        
        # Verify session exists
        session = db_manager.get_session("test_session_1")
        assert session is not None
        assert session["user_id"] == "test_user_1"
    
    def test_add_conversation(self, db_manager):
        """Test adding conversation."""
        # Create session first
        db_manager.create_session("test_session_1", "test_user_1")
        
        # Add conversation
        conv_id = db_manager.add_conversation(
            session_id="test_session_1",
            user_message="What is collateral?",
            agent_response="Collateral is an asset used to secure a loan.",
            intent="question",
            confidence=0.95,
            response_time_ms=500,
            token_count=50
        )
        
        assert conv_id > 0
        
        # Verify conversation
        conversations = db_manager.get_recent_conversations("test_session_1", limit=1)
        assert len(conversations) == 1
        assert conversations[0]["user_message"] == "What is collateral?"
    
    def test_conversation_context(self, db_manager):
        """Test retrieving conversation context."""
        # Setup
        db_manager.create_session("test_session_1", "test_user_1")
        
        # Add multiple conversations
        for i in range(5):
            db_manager.add_conversation(
                session_id="test_session_1",
                user_message=f"Question {i}",
                agent_response=f"Answer {i}",
                intent="question"
            )
        
        # Get context
        context = db_manager.get_conversation_context("test_session_1", max_tokens=1000)
        
        assert "Question" in context
        assert "Answer" in context
    
    def test_cache_search_results(self, db_manager):
        """Test search caching."""
        # Cache results
        db_manager.cache_search_results(
            query="test query",
            search_type="vector",
            results=[{"text": "result 1"}, {"text": "result 2"}],
            ttl_seconds=3600
        )
        
        # Retrieve cached results
        cached = db_manager.get_cached_search("test query", "vector")
        
        assert cached is not None
        assert len(cached) == 2
        assert cached[0]["text"] == "result 1"
    
    def test_response_cache(self, db_manager):
        """Test response caching."""
        # Cache response
        db_manager.cache_response(
            input_text="What is collateral?",
            model_name="gemini-2.0-flash-exp",
            response_text="Collateral is an asset...",
            token_count=50,
            ttl_seconds=7200
        )
        
        # Retrieve cached response
        cached = db_manager.get_cached_response(
            input_text="What is collateral?",
            model_name="gemini-2.0-flash-exp"
        )
        
        assert cached is not None
        response_text, token_count = cached
        assert "Collateral" in response_text
        assert token_count == 50
    
    def test_context_storage(self, db_manager):
        """Test context storage and retrieval."""
        # Create session
        db_manager.create_session("test_session_1", "test_user_1")
        
        # Store context
        db_manager.store_context(
            session_id="test_session_1",
            context_type="user_preference",
            context_key="preferred_language",
            context_value="English",
            relevance_score=1.0,
            ttl_days=30
        )
        
        # Retrieve context
        contexts = db_manager.get_context(
            session_id="test_session_1",
            context_type="user_preference"
        )
        
        assert len(contexts) == 1
        assert contexts[0]["context_value"] == "English"
    
    def test_critique_history(self, db_manager):
        """Test critique iteration logging."""
        # Setup
        db_manager.create_session("test_session_1", "test_user_1")
        conv_id = db_manager.add_conversation(
            session_id="test_session_1",
            user_message="Test",
            agent_response="Test response"
        )
        
        # Add critique iteration
        db_manager.add_critique_iteration(
            conversation_id=conv_id,
            iteration=1,
            planner_response="First attempt",
            critique_score=0.75,
            accuracy_score=0.8,
            completeness_score=0.7,
            clarity_score=0.75,
            critique_feedback="Good, but needs more detail"
        )
        
        # Retrieve critique history
        history = db_manager.get_critique_history(conv_id)
        
        assert len(history) == 1
        assert history[0]["iteration"] == 1
        assert history[0]["critique_score"] == 0.75
    
    def test_database_stats(self, db_manager):
        """Test database statistics."""
        # Create some data
        db_manager.create_session("test_session_1", "test_user_1")
        db_manager.add_conversation(
            session_id="test_session_1",
            user_message="Test",
            agent_response="Test"
        )
        
        # Get stats
        stats = db_manager.get_database_stats()
        
        assert "user_sessions" in stats
        assert "conversation_history" in stats
        assert stats["user_sessions"] >= 1
        assert stats["conversation_history"] >= 1


class TestGeminiClient:
    """Tests for Gemini client."""
    
    @pytest.mark.asyncio
    async def test_token_counting(self):
        """Test token counting."""
        from app.gemini_enhanced import GeminiClient
        
        text = "This is a test sentence with several words."
        tokens = GeminiClient.count_tokens(text)
        
        assert tokens > 0
        assert tokens < len(text)  # Tokens should be less than characters
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, db_manager):
        """Test cache key generation."""
        from app.gemini_enhanced import GeminiClient
        
        client = GeminiClient(
            api_key="test_key",
            enable_cache=True,
            db_manager=db_manager
        )
        
        key1 = client._get_cache_key("test prompt", {"temperature": 0.7})
        key2 = client._get_cache_key("test prompt", {"temperature": 0.7})
        key3 = client._get_cache_key("different prompt", {"temperature": 0.7})
        
        assert key1 == key2  # Same input = same key
        assert key1 != key3  # Different input = different key


class TestPlannerCritique:
    """Tests for planner-critique orchestrator."""
    
    @pytest.mark.asyncio
    async def test_planner_critique_loop(self, mock_gemini_client):
        """Test complete planner-critique loop."""
        from app.planner_critique import PlannerCritiqueOrchestrator
        from unittest.mock import AsyncMock
        
        # Mock critique to return low score first, then high score
        scores = [0.7, 0.9]
        score_index = [0]
        
        async def mock_critique(**kwargs):
            score = scores[min(score_index[0], len(scores) - 1)]
            score_index[0] += 1
            return {
                "overall_score": score,
                "accuracy": score,
                "completeness": score,
                "clarity": score,
                "feedback": "Needs improvement" if score < 0.85 else "Good",
                "strengths": "Clear",
                "weaknesses": "Too brief" if score < 0.85 else "None",
                "approved": score >= 0.85,
                "tokens": 50
            }
        
        orchestrator = PlannerCritiqueOrchestrator(
            gemini_client=mock_gemini_client,
            max_iterations=2,
            acceptance_threshold=0.85
        )
        
        # Mock the critique step
        orchestrator._critique_step = mock_critique
        
        # Run loop
        result = await orchestrator.run(
            query="What is collateral?",
            context="Collateral is an asset used to secure a loan."
        )
        
        assert result.total_iterations <= 2
        assert result.final_response is not None
        assert len(result.iterations) > 0
    
    @pytest.mark.asyncio
    async def test_max_iterations_limit(self, mock_gemini_client):
        """Test that max iterations are enforced."""
        from app.planner_critique import PlannerCritiqueOrchestrator
        
        # Mock critique to always return low score
        async def mock_critique_low(**kwargs):
            return {
                "overall_score": 0.5,
                "accuracy": 0.5,
                "completeness": 0.5,
                "clarity": 0.5,
                "feedback": "Needs improvement",
                "strengths": "",
                "weaknesses": "Everything",
                "approved": False,
                "tokens": 50
            }
        
        orchestrator = PlannerCritiqueOrchestrator(
            gemini_client=mock_gemini_client,
            max_iterations=2,
            acceptance_threshold=0.85
        )
        
        orchestrator._critique_step = mock_critique_low
        
        result = await orchestrator.run(
            query="Test query",
            context="Test context"
        )
        
        assert result.total_iterations == 2  # Should stop at max
        assert result.approved is False  # Never approved


class TestConfiguration:
    """Tests for configuration management."""
    
    def test_config_loading(self):
        """Test configuration loading."""
        from config.config_loader import Config
        
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("GEMINI_API_KEY=test_key\n")
            f.write("MAX_CRITIQUE_ITERATIONS=3\n")
            f.write("ENABLE_CRITIQUE=true\n")
            env_path = f.name
        
        try:
            config = Config(env_path)
            
            assert config.gemini_api_key == "test_key"
            assert config.max_critique_iterations == 3
            assert config.enable_critique is True
        finally:
            Path(env_path).unlink()
    
    def test_config_validation(self):
        """Test configuration validation."""
        from config.config_loader import Config
        
        # Create invalid config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("GEMINI_API_KEY=your_gemini_api_key_here\n")
            env_path = f.name
        
        try:
            config = Config(env_path)
            
            with pytest.raises(ValueError):
                config.validate()
        finally:
            Path(env_path).unlink()


class TestIntegration:
    """Integration tests."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_flow(self, db_manager, mock_gemini_client):
        """Test complete end-to-end flow."""
        from app.planner_critique import PlannerCritiqueOrchestrator
        
        # Create session
        db_manager.create_session("integration_test", "test_user")
        
        # Mock critique
        async def mock_critique(**kwargs):
            return {
                "overall_score": 0.9,
                "accuracy": 0.9,
                "completeness": 0.9,
                "clarity": 0.9,
                "feedback": "Excellent",
                "strengths": "Clear and accurate",
                "weaknesses": "None",
                "approved": True,
                "tokens": 50
            }
        
        # Create orchestrator
        orchestrator = PlannerCritiqueOrchestrator(
            gemini_client=mock_gemini_client,
            max_iterations=2,
            acceptance_threshold=0.85,
            db_manager=db_manager
        )
        
        orchestrator._critique_step = mock_critique
        
        # Add conversation first
        conv_id = db_manager.add_conversation(
            session_id="integration_test",
            user_message="What is collateral?",
            agent_response="Placeholder"
        )
        
        # Run planner-critique
        result = await orchestrator.run(
            query="What is collateral?",
            context="Collateral is an asset used to secure a loan.",
            conversation_id=conv_id
        )
        
        # Verify results
        assert result.approved
        assert result.final_response is not None
        
        # Verify database logging
        critique_history = db_manager.get_critique_history(conv_id)
        assert len(critique_history) > 0


class TestPerformance:
    """Performance tests."""
    
    def test_database_query_performance(self, db_manager):
        """Test database query performance."""
        import time
        
        # Create session and add conversations
        db_manager.create_session("perf_test", "test_user")
        
        for i in range(100):
            db_manager.add_conversation(
                session_id="perf_test",
                user_message=f"Question {i}",
                agent_response=f"Answer {i}"
            )
        
        # Measure query time
        start = time.time()
        conversations = db_manager.get_recent_conversations("perf_test", limit=10)
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        assert elapsed < 200  # Should be < 200ms
        assert len(conversations) == 10
    
    def test_cache_performance(self, db_manager):
        """Test cache hit performance."""
        import time
        
        # Cache some results
        db_manager.cache_search_results(
            query="test query",
            search_type="vector",
            results=[{"text": f"result {i}"} for i in range(10)],
            ttl_seconds=3600
        )
        
        # Measure cache retrieval time
        start = time.time()
        cached = db_manager.get_cached_search("test query", "vector")
        elapsed = (time.time() - start) * 1000
        
        assert elapsed < 50  # Should be very fast
        assert cached is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
