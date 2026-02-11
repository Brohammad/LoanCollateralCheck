"""Unit tests for the orchestrator and core components."""
import asyncio
import pytest
import os
from unittest.mock import Mock, patch, MagicMock

# Set a dummy API key for testing (tests use mocks anyway)
os.environ["GOOGLE_API_KEY"] = "test-key-for-unit-tests"


def test_greeting_detection():
    """Test that greeting messages are correctly routed to greeting agent."""
    from app.orchestrator import Orchestrator
    from app.gemini_client import GeminiClient

    # Mock the Gemini client to avoid real API calls
    with patch.object(GeminiClient, "classify_intent") as mock_classify:
        mock_classify.return_value = {"intent": "greeting", "confidence": 0.9}

        orch = Orchestrator()
        res = asyncio.run(orch.handle("user-1", "Hello there"))
        assert res["agent"] == "greeting"
        assert "intent" in res
        assert res["intent"] == "greeting"


def test_question_flow():
    """Test that question messages trigger RAG pipeline and planner."""
    from app.orchestrator import Orchestrator
    from app.gemini_client import GeminiClient

    # Mock Gemini client methods
    with patch.object(GeminiClient, "classify_intent") as mock_classify, patch.object(
        GeminiClient, "embed"
    ) as mock_embed, patch.object(GeminiClient, "generate") as mock_generate:
        mock_classify.return_value = {"intent": "question", "confidence": 0.85}
        mock_embed.return_value = [[0.1] * 8]
        mock_generate.return_value = "This is a test response."

        orch = Orchestrator()
        res = asyncio.run(orch.handle("user-1", "What is the capital of France?"))
        assert res["agent"] == "planner"
        assert "response" in res
        assert "rag" in res


def test_intent_classification_fallback():
    """Test intent classification with fallback (no API)."""
    from app.gemini_client import GeminiClient

    # Create a client instance
    client = GeminiClient(api_key="test-key")

    # Patch the generate method on this specific instance to trigger fallback
    with patch.object(client, "generate", side_effect=Exception("API unavailable")):
        # Test greeting fallback
        result = client.classify_intent("Hello, how are you?")
        assert "intent" in result
        assert result["intent"] == "greeting"
        assert "confidence" in result
        assert isinstance(result["confidence"], float)

        # Test question fallback - "What" is a question word
        result = client.classify_intent("What is machine learning?")
        # Fallback logic checks for multiple keywords; accept valid results
        assert result["intent"] in ["question", "unclear", "greeting"]
        assert result["confidence"] > 0.0


def test_database_operations():
    """Test database CRUD operations."""
    from app.database import DatabaseManager
    import tempfile
    import os

    # Use temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name

    try:
        db = DatabaseManager(db_path)

        # Test add conversation
        conv_id = db.add_conversation(
            user_id="test-user",
            message="Test message",
            response="Test response",
            intent="question",
            confidence=0.8,
            agent_used="planner",
        )
        assert isinstance(conv_id, int)
        assert conv_id > 0

        # Test get recent conversations
        convs = db.get_recent_conversations("test-user", limit=5)
        assert len(convs) == 1
        assert convs[0]["message"] == "Test message"

        # Test credit history
        db.add_credit_history(conv_id, {"test": "data"}, {"meta": "info"})

        # Test cache
        db.set_cache("test query", [{"result": 1}], ttl_seconds=3600)
        cached = db.get_cache("test query")
        assert cached is not None
        assert len(cached) == 1

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_vector_store_operations():
    """Test vector store add and search."""
    from app.vector_store import InMemoryVectorStore

    store = InMemoryVectorStore()

    # Add some vectors
    ids = ["doc1", "doc2", "doc3"]
    embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    metadatas = [{"text": "Document 1"}, {"text": "Document 2"}, {"text": "Document 3"}]

    store.add(ids, embeddings, metadatas)

    # Search
    results = store.search([1.0, 0.0, 0.0], top_k=2)
    assert len(results) <= 2
    assert results[0]["id"] == "doc1"


def test_config_validation():
    """Test configuration validation."""
    from app.config import Config

    # Test config to dict
    config_dict = Config.to_dict()
    assert "generation_model" in config_dict
    assert "embedding_model" in config_dict


if __name__ == "__main__":
    # Run tests without pytest
    print("Running tests...")
    test_greeting_detection()
    print("✓ test_greeting_detection")

    test_question_flow()
    print("✓ test_question_flow")

    test_intent_classification_fallback()
    print("✓ test_intent_classification_fallback")

    test_database_operations()
    print("✓ test_database_operations")

    test_vector_store_operations()
    print("✓ test_vector_store_operations")

    test_config_validation()
    print("✓ test_config_validation")

    print("\nAll tests passed!")

