"""
Pytest Configuration and Shared Fixtures

Provides shared fixtures, test configuration, and utilities for all tests.
"""

import asyncio
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Generator, Dict, Any
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_database(temp_dir):
    """Create a temporary test database."""
    db_path = temp_dir / "test.db"
    
    # Create database with schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE user_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_message TEXT,
            agent_response TEXT,
            intent TEXT,
            confidence REAL,
            tokens_used INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES user_sessions(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE response_cache (
            id TEXT PRIMARY KEY,
            input_text TEXT,
            model_name TEXT,
            response_text TEXT,
            tokens_used INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME
        )
    """)
    
    cursor.execute("""
        CREATE TABLE search_cache (
            id TEXT PRIMARY KEY,
            query TEXT,
            search_type TEXT,
            results_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME
        )
    """)
    
    conn.commit()
    conn.close()
    
    yield str(db_path)
    
    # Cleanup handled by temp_dir fixture


@pytest.fixture
def test_vector_db(temp_dir):
    """Create a temporary ChromaDB instance."""
    chroma_path = temp_dir / "chromadb"
    chroma_path.mkdir()
    
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(chroma_path))
        
        # Create a test collection
        collection = client.create_collection(
            name="test_collection",
            metadata={"description": "Test collection"}
        )
        
        # Add some test documents
        collection.add(
            documents=[
                "Loan collateral is an asset pledged to secure a loan.",
                "Types of collateral include real estate, vehicles, and equipment.",
                "Credit history affects loan approval rates significantly."
            ],
            ids=["doc1", "doc2", "doc3"],
            metadatas=[
                {"source": "test", "topic": "collateral"},
                {"source": "test", "topic": "collateral_types"},
                {"source": "test", "topic": "credit"}
            ]
        )
        
        yield str(chroma_path), client, collection
    except ImportError:
        # ChromaDB not installed, return mock
        yield str(chroma_path), None, None


@pytest.fixture
def sample_conversations() -> list[Dict[str, Any]]:
    """Sample conversation data for testing."""
    return [
        {
            "session_id": "session-001",
            "user_message": "What is loan collateral?",
            "agent_response": "Loan collateral is an asset pledged to secure a loan...",
            "intent": "question",
            "confidence": 0.95,
            "tokens_used": 1500
        },
        {
            "session_id": "session-001",
            "user_message": "What types of collateral are accepted?",
            "agent_response": "Common types include real estate, vehicles, equipment...",
            "intent": "question",
            "confidence": 0.92,
            "tokens_used": 1800
        },
        {
            "session_id": "session-002",
            "user_message": "Hello",
            "agent_response": "Hello! How can I help you today?",
            "intent": "greeting",
            "confidence": 0.98,
            "tokens_used": 500
        }
    ]


@pytest.fixture
def sample_rag_results() -> Dict[str, Any]:
    """Sample RAG retrieval results for testing."""
    return {
        "vector_results": [
            {
                "content": "Loan collateral is an asset pledged to secure a loan.",
                "metadata": {"source": "document1.pdf", "page": 1},
                "score": 0.92
            },
            {
                "content": "Types of collateral include real estate and vehicles.",
                "metadata": {"source": "document2.pdf", "page": 3},
                "score": 0.88
            }
        ],
        "web_results": [
            {
                "title": "Understanding Loan Collateral",
                "url": "https://example.com/collateral",
                "snippet": "Collateral is an asset that backs a loan..."
            }
        ],
        "merged_context": "Loan collateral is an asset pledged to secure a loan. Types of collateral include real estate and vehicles.",
        "token_count": 450
    }


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini API client for testing."""
    mock = AsyncMock()
    
    # Mock generate_async
    mock.generate_async.return_value = "This is a test response from Gemini."
    
    # Mock classify_intent
    mock.classify_intent.return_value = ("question", 0.95)
    
    # Mock generate_with_json
    mock.generate_with_json.return_value = {
        "overall_score": 0.87,
        "accuracy_score": 0.90,
        "completeness_score": 0.85,
        "clarity_score": 0.85,
        "approved": True,
        "feedback": "Response is accurate and complete."
    }
    
    # Mock count_tokens
    mock.count_tokens.return_value = 1500
    
    return mock


@pytest.fixture
def mock_database_manager(test_database):
    """Mock database manager with test database."""
    from database.db_manager import DatabaseManager
    
    manager = DatabaseManager(db_path=test_database)
    yield manager
    manager.close()


@pytest.fixture
def mock_cache():
    """Mock cache for testing."""
    cache = {}
    
    class MockCache:
        def get(self, key: str):
            return cache.get(key)
        
        def set(self, key: str, value: Any, ttl: int = 3600):
            cache[key] = value
        
        def delete(self, key: str):
            if key in cache:
                del cache[key]
        
        def clear(self):
            cache.clear()
        
        def exists(self, key: str) -> bool:
            return key in cache
    
    return MockCache()


@pytest.fixture
def mock_vector_search():
    """Mock vector search results."""
    async def search(query: str, top_k: int = 5):
        return [
            {
                "content": "Loan collateral is an asset pledged to secure a loan.",
                "metadata": {"source": "test"},
                "score": 0.92
            },
            {
                "content": "Types of collateral include real estate and vehicles.",
                "metadata": {"source": "test"},
                "score": 0.88
            }
        ]
    
    return search


@pytest.fixture
def mock_web_search():
    """Mock web search results."""
    async def search(query: str):
        return [
            {
                "title": "Understanding Loan Collateral",
                "url": "https://example.com/collateral",
                "snippet": "Collateral is an asset that backs a loan..."
            }
        ]
    
    return search


@pytest.fixture
def sample_user_query():
    """Sample user query for testing."""
    return {
        "message": "What is loan collateral?",
        "session_id": "test-session-123",
        "metadata": {
            "user_id": "user-456",
            "timestamp": "2026-02-11T10:30:45Z"
        }
    }


@pytest.fixture
def mock_serp_api():
    """Mock SERP API responses."""
    mock = AsyncMock()
    mock.search.return_value = {
        "organic_results": [
            {
                "title": "Understanding Loan Collateral",
                "link": "https://example.com/collateral",
                "snippet": "Collateral is an asset that backs a loan..."
            }
        ]
    }
    return mock


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics between tests."""
    from prometheus_client import REGISTRY
    
    # Clear collectors
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass
    
    yield
    
    # Cleanup after test
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass


@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        "database": {
            "path": "./test.db",
            "pool_size": 3
        },
        "gemini": {
            "api_key": "test-api-key",
            "model": "gemini-2.0-flash-exp",
            "temperature": 0.7,
            "max_tokens": 2048
        },
        "cache": {
            "ttl": 3600,
            "max_size": 1000
        },
        "rag": {
            "top_k": 5,
            "max_tokens": 4000
        },
        "critique": {
            "max_iterations": 2,
            "acceptance_threshold": 0.85
        }
    }


# Test data generators
def generate_test_conversation(
    session_id: str = "test-session",
    count: int = 5
) -> list[Dict[str, Any]]:
    """Generate test conversation data."""
    conversations = []
    for i in range(count):
        conversations.append({
            "session_id": session_id,
            "user_message": f"Test question {i+1}",
            "agent_response": f"Test response {i+1}",
            "intent": "question",
            "confidence": 0.85 + (i * 0.02),
            "tokens_used": 1000 + (i * 100)
        })
    return conversations


def generate_test_documents(count: int = 10) -> list[Dict[str, Any]]:
    """Generate test documents for vector DB."""
    documents = []
    for i in range(count):
        documents.append({
            "id": f"doc-{i+1}",
            "content": f"Test document content {i+1}",
            "metadata": {
                "source": f"test-source-{i+1}",
                "topic": "test",
                "page": i + 1
            }
        })
    return documents


# Pytest hooks
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test items."""
    # Add markers automatically based on test location
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)


# Environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment."""
    # Set test environment variables
    os.environ["ENV"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["TESTING"] = "true"
    
    yield
    
    # Cleanup
    if "ENV" in os.environ:
        del os.environ["ENV"]
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
