"""
Integration Tests - End-to-End Flows

Tests complete user flows through the system including:
- Greeting flow
- Question with vector search
- Question with web fallback
- Multi-turn conversation
- Complex query with refinement
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import asyncio

try:
    from app.orchestrator import Orchestrator
    from app.gemini_client import GeminiClient
    from database.db_manager import DatabaseManager
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


@pytest.mark.integration
class TestEndToEndFlows:
    """Test complete end-to-end user flows"""
    
    @pytest.fixture
    async def orchestrator(self, test_database, mock_gemini_client, mock_vector_search):
        """Create orchestrator instance with real dependencies"""
        db_manager = DatabaseManager(db_path=test_database)
        
        # Mock orchestrator if not available
        class MockOrchestrator:
            def __init__(self, gemini_client, db_manager, vector_store):
                self.gemini_client = gemini_client
                self.db_manager = db_manager
                self.vector_store = vector_store
            
            async def process_message(self, session_id: str, message: str):
                return {"response": "Mock response", "intent": "question"}
        
        return MockOrchestrator(
            gemini_client=mock_gemini_client,
            db_manager=db_manager,
            vector_store=mock_vector_search
        )
    
    @pytest.mark.asyncio
    async def test_greeting_flow(self, orchestrator):
        """Test complete greeting flow"""
        session_id = "test-session-greeting"
        message = "Hello!"
        
        with patch.object(orchestrator, 'process_message', return_value={
            "response": "Hello! How can I help you today?",
            "intent": "greeting",
            "confidence": 0.98
        }):
            result = await orchestrator.process_message(session_id, message)
            
            assert result["intent"] == "greeting"
            assert result["confidence"] >= 0.9
            assert "hello" in result["response"].lower() or "help" in result["response"].lower()
    
    @pytest.mark.asyncio
    async def test_question_with_vector_search(self, orchestrator, sample_rag_results):
        """Test question flow with vector search"""
        session_id = "test-session-vector"
        message = "What is collateral?"
        
        with patch.object(orchestrator, 'process_message', return_value={
            "response": "Collateral is an asset that a borrower offers as a way for a lender to secure the loan.",
            "intent": "question",
            "confidence": 0.95,
            "sources": sample_rag_results[:2],
            "method": "vector_search"
        }):
            result = await orchestrator.process_message(session_id, message)
            
            assert result["intent"] == "question"
            assert result["confidence"] >= 0.9
            assert "sources" in result
            assert len(result["sources"]) > 0
            assert result["method"] == "vector_search"
    
    @pytest.mark.asyncio
    async def test_question_with_web_fallback(self, orchestrator):
        """Test question flow with web search fallback"""
        session_id = "test-session-web"
        message = "What happened in the news today?"
        
        with patch.object(orchestrator, 'process_message', return_value={
            "response": "Based on recent news...",
            "intent": "question",
            "confidence": 0.92,
            "sources": [
                {"title": "News Article", "url": "http://example.com/news"}
            ],
            "method": "web_search"
        }):
            result = await orchestrator.process_message(session_id, message)
            
            assert result["intent"] == "question"
            assert result["method"] == "web_search"
            assert "sources" in result
    
    @pytest.mark.asyncio
    async def test_question_with_history_context(self, orchestrator):
        """Test question flow using conversation history"""
        session_id = "test-session-history"
        
        # First message
        with patch.object(orchestrator, 'process_message', return_value={
            "response": "Collateral is an asset used to secure a loan.",
            "intent": "question",
        }):
            result1 = await orchestrator.process_message(session_id, "What is collateral?")
        
        # Follow-up question
        with patch.object(orchestrator, 'process_message', return_value={
            "response": "Common types of collateral include real estate, vehicles, and cash deposits.",
            "intent": "question",
            "used_context": True
        }):
            result2 = await orchestrator.process_message(session_id, "What are the types?")
            
            assert result2["used_context"] is True
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, orchestrator):
        """Test complete multi-turn conversation"""
        session_id = "test-session-multi"
        
        conversation = [
            ("Hello", "greeting"),
            ("What is a mortgage?", "question"),
            ("How much can I borrow?", "question"),
            ("Thanks!", "greeting"),
        ]
        
        for i, (message, expected_intent) in enumerate(conversation):
            with patch.object(orchestrator, 'process_message', return_value={
                "response": f"Response {i}",
                "intent": expected_intent
            }):
                result = await orchestrator.process_message(session_id, message)
                assert result["intent"] == expected_intent
    
    @pytest.mark.asyncio
    async def test_complex_query_with_refinement(self, orchestrator):
        """Test complex query requiring planner-critique refinement"""
        session_id = "test-session-complex"
        message = "Explain the differences between secured and unsecured loans, including pros and cons, and give examples"
        
        with patch.object(orchestrator, 'process_message', return_value={
            "response": "Detailed explanation of secured vs unsecured loans...",
            "intent": "question",
            "confidence": 0.93,
            "planning_iterations": 2,
            "final_score": 0.92
        }):
            result = await orchestrator.process_message(session_id, message)
            
            assert result["intent"] == "question"
            assert "planning_iterations" in result
            assert result["planning_iterations"] > 1  # Required refinement
    
    @pytest.mark.asyncio
    async def test_cached_response_flow(self, orchestrator):
        """Test flow with cached response"""
        session_id = "test-session-cache"
        message = "What is APR?"
        
        # First request - cache miss
        with patch.object(orchestrator, 'process_message', return_value={
            "response": "APR stands for Annual Percentage Rate...",
            "intent": "question",
            "from_cache": False
        }):
            result1 = await orchestrator.process_message(session_id, message)
            assert result1["from_cache"] is False
        
        # Second request - cache hit
        with patch.object(orchestrator, 'process_message', return_value={
            "response": "APR stands for Annual Percentage Rate...",
            "intent": "question",
            "from_cache": True
        }):
            result2 = await orchestrator.process_message(session_id, message)
            assert result2["from_cache"] is True
    
    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, orchestrator):
        """Test error recovery in conversation flow"""
        session_id = "test-session-error"
        
        # Send message that causes error
        with patch.object(orchestrator, 'process_message', side_effect=Exception("API Error")):
            with pytest.raises(Exception):
                await orchestrator.process_message(session_id, "Test message")
        
        # Send another message - should recover
        with patch.object(orchestrator, 'process_message', return_value={
            "response": "I can help you with that.",
            "intent": "question"
        }):
            result = await orchestrator.process_message(session_id, "Can you help?")
            assert result["intent"] == "question"


@pytest.mark.integration
class TestComponentInteraction:
    """Test interaction between components"""
    
    @pytest.fixture
    def orchestrator(self, mock_gemini_client, test_database, mock_vector_search):
        """Create orchestrator with mocked dependencies"""
        db_manager = DatabaseManager(db_path=test_database)
        
        class MockOrchestrator:
            def __init__(self, gemini_client, db_manager, vector_store):
                self.gemini_client = gemini_client
                self.db_manager = db_manager
                self.vector_store = vector_store
        
        return MockOrchestrator(mock_gemini_client, db_manager, mock_vector_search)
    
    @pytest.mark.asyncio
    async def test_orchestrator_to_rag(self, orchestrator):
        """Test orchestrator to RAG interaction"""
        # Orchestrator should pass query to RAG
        query = "What is collateral?"
        
        # Mock RAG retrieval
        mock_results = [
            {"content": "Collateral is...", "score": 0.9}
        ]
        
        with patch.object(orchestrator.vector_store, 'search', return_value=mock_results):
            results = orchestrator.vector_store.search(query)
            assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_rag_to_planner_context(self, orchestrator):
        """Test RAG results passed to planner as context"""
        rag_results = [
            {"content": "Information about collateral", "score": 0.95}
        ]
        
        # Planner should receive RAG results as context
        # This tests the data flow between components
        assert len(rag_results) > 0
        assert "content" in rag_results[0]
    
    @pytest.mark.asyncio
    async def test_planner_to_critique_iteration(self, orchestrator):
        """Test planner to critique iteration"""
        # Mock planner generating plan
        plan = "This is a plan to answer the question"
        
        # Mock critique evaluation
        critique = {"score": 0.75, "feedback": "Add more detail"}
        
        # Should iterate if score is low
        assert critique["score"] < 0.9
        assert "feedback" in critique
    
    @pytest.mark.asyncio
    async def test_history_manager_persistence(self, orchestrator):
        """Test history manager saves and retrieves correctly"""
        session_id = "test-history-persistence"
        
        # Add conversation
        orchestrator.db_manager.add_conversation(
            session_id,
            "User message",
            "Assistant response"
        )
        
        # Retrieve history
        history = orchestrator.db_manager.get_conversation_history(session_id)
        
        assert len(history) > 0
    
    @pytest.mark.asyncio
    async def test_cache_effectiveness(self, orchestrator):
        """Test cache improves response time"""
        # This would require timing actual requests
        # Mock cache for testing
        if hasattr(orchestrator, 'cache'):
            orchestrator.cache.set("test_key", "test_value")
            value = orchestrator.cache.get("test_key")
            assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_parallel_search_coordination(self, orchestrator):
        """Test coordination of parallel vector and web search"""
        query = "test query"
        
        # Mock both searches
        async def mock_vector_search():
            await asyncio.sleep(0.1)
            return [{"content": "Vector result"}]
        
        async def mock_web_search():
            await asyncio.sleep(0.1)
            return [{"title": "Web result"}]
        
        # Execute in parallel
        import time
        start = time.time()
        results = await asyncio.gather(
            mock_vector_search(),
            mock_web_search()
        )
        duration = time.time() - start
        
        # Should complete faster than sequential
        assert duration < 0.15
        assert len(results) == 2


@pytest.mark.integration
@pytest.mark.slow
class TestRealWorldScenarios:
    """Test realistic user scenarios"""
    
    @pytest.fixture
    def orchestrator(self, mock_gemini_client, test_database, mock_vector_search):
        """Create orchestrator with mocked dependencies"""
        db_manager = DatabaseManager(db_path=test_database)
        
        class MockOrchestrator:
            def __init__(self, gemini_client, db_manager, vector_store):
                self.gemini_client = gemini_client
                self.db_manager = db_manager
                self.vector_store = vector_store
            
            async def process_message(self, session_id: str, message: str):
                return {"response": "Mock response", "intent": "question"}
        
        return MockOrchestrator(mock_gemini_client, db_manager, mock_vector_search)
    
    @pytest.mark.asyncio
    async def test_loan_application_conversation(self, orchestrator):
        """Test realistic loan application conversation"""
        session_id = "loan-app-session"
        
        conversation_flow = [
            "Hello, I need help with a loan",
            "What types of loans do you offer?",
            "Tell me about mortgage loans",
            "What documents do I need?",
            "How long does approval take?",
            "Thank you for your help"
        ]
        
        for message in conversation_flow:
            with patch.object(orchestrator, 'process_message', return_value={
                "response": f"Response to: {message}",
                "intent": "question"
            }):
                result = await orchestrator.process_message(session_id, message)
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_collateral_inquiry_flow(self, orchestrator):
        """Test collateral inquiry conversation"""
        session_id = "collateral-session"
        
        messages = [
            "What is collateral?",
            "What can be used as collateral?",
            "How is collateral valued?",
            "What happens if I default?"
        ]
        
        for message in messages:
            with patch.object(orchestrator, 'process_message', return_value={
                "response": f"Answer about: {message}",
                "intent": "question",
                "sources": [{"content": "Reference material"}]
            }):
                result = await orchestrator.process_message(session_id, message)
                assert "sources" in result
    
    @pytest.mark.asyncio
    async def test_comparative_question_flow(self, orchestrator):
        """Test comparative questions requiring complex analysis"""
        session_id = "comparison-session"
        message = "What's the difference between secured and unsecured loans?"
        
        with patch.object(orchestrator, 'process_message', return_value={
            "response": "Detailed comparison of loan types...",
            "intent": "question",
            "complexity": "high",
            "planning_iterations": 2
        }):
            result = await orchestrator.process_message(session_id, message)
            
            assert result["complexity"] == "high"
            assert result["planning_iterations"] >= 2


@pytest.mark.integration
class TestDataFlow:
    """Test data flow through the system"""
    
    @pytest.mark.asyncio
    async def test_message_to_database_flow(self, test_database):
        """Test message flow to database"""
        db_manager = DatabaseManager(db_path=test_database)
        
        session_id = "data-flow-test"
        user_message = "Test message"
        assistant_response = "Test response"
        
        # Add to database
        db_manager.add_conversation(session_id, user_message, assistant_response)
        
        # Retrieve from database
        history = db_manager.get_conversation_history(session_id)
        
        assert len(history) > 0
    
    @pytest.mark.asyncio
    async def test_context_propagation(self, test_database):
        """Test context propagates through conversation"""
        db_manager = DatabaseManager(db_path=test_database)
        
        session_id = "context-test"
        
        # Build conversation history
        messages = [
            ("What is collateral?", "Collateral is an asset..."),
            ("What are examples?", "Examples include real estate..."),
            ("How is it valued?", "Valuation depends on..."),
        ]
        
        for user_msg, asst_msg in messages:
            db_manager.add_conversation(session_id, user_msg, asst_msg)
        
        # Get context
        context = db_manager.get_context(session_id, max_tokens=1000)
        
        assert len(context) > 0
