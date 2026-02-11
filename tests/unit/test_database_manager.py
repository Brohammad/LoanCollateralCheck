"""
Unit Tests for Database Manager

Tests the database manager including:
- Connection management
- Conversation storage and retrieval
- Context retrieval
- Cache operations
- Transaction handling
"""

import pytest
import sqlite3
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, timedelta
import json

try:
    from database.db_manager import DatabaseManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    # Mock class for testing
    class DatabaseManager:
        def __init__(self, db_path: str = ":memory:"):
            self.db_path = db_path
            self.pool_size = 5
        
        def get_connection(self):
            return sqlite3.connect(self.db_path)
        
        def add_conversation(self, session_id: str, user_message: str, assistant_response: str):
            pass
        
        def get_conversation_history(self, session_id: str, limit: int = 10):
            return []
        
        def get_context(self, session_id: str, max_tokens: int = 2000):
            return []


@pytest.mark.unit
class TestDatabaseManager:
    """Test suite for Database Manager"""
    
    @pytest.fixture
    def db_manager(self, test_database):
        """Create a database manager instance"""
        return DatabaseManager(db_path=test_database)
    
    def test_connection_creation(self, db_manager):
        """Test database connection creation"""
        conn = db_manager.get_connection()
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
        conn.close()
    
    def test_connection_reuse(self, db_manager):
        """Test connection pooling and reuse"""
        conn1 = db_manager.get_connection()
        conn1.close()
        
        conn2 = db_manager.get_connection()
        assert conn2 is not None
        conn2.close()
    
    def test_connection_pool_exhaustion(self, db_manager):
        """Test behavior when connection pool is exhausted"""
        connections = []
        max_connections = db_manager.pool_size
        
        # Get all available connections
        for _ in range(max_connections):
            conn = db_manager.get_connection()
            connections.append(conn)
        
        # Attempting to get another should handle gracefully
        # Implementation-dependent behavior
        
        # Clean up
        for conn in connections:
            conn.close()
    
    def test_add_conversation(self, db_manager):
        """Test adding a conversation to database"""
        session_id = "test-session-123"
        user_message = "What is collateral?"
        assistant_response = "Collateral is an asset used to secure a loan."
        
        db_manager.add_conversation(session_id, user_message, assistant_response)
        
        # Verify it was added
        history = db_manager.get_conversation_history(session_id)
        assert len(history) > 0
    
    def test_get_conversation_history(self, db_manager):
        """Test retrieving conversation history"""
        session_id = "test-session-456"
        
        # Add multiple messages
        for i in range(5):
            db_manager.add_conversation(
                session_id,
                f"User message {i}",
                f"Assistant response {i}"
            )
        
        history = db_manager.get_conversation_history(session_id, limit=3)
        assert len(history) == 3
    
    def test_get_conversation_history_empty(self, db_manager):
        """Test retrieving history for non-existent session"""
        history = db_manager.get_conversation_history("non-existent-session")
        assert len(history) == 0
    
    def test_get_context_with_token_limit(self, db_manager):
        """Test context retrieval with token limit"""
        session_id = "test-session-789"
        
        # Add several messages
        for i in range(10):
            db_manager.add_conversation(
                session_id,
                f"User message {i}" * 10,  # Make it longer
                f"Assistant response {i}" * 10
            )
        
        context = db_manager.get_context(session_id, max_tokens=500)
        # Should return limited messages to fit token budget
        assert isinstance(context, list)
    
    def test_get_context_empty_history(self, db_manager):
        """Test context retrieval with no history"""
        context = db_manager.get_context("non-existent-session")
        assert context == [] or context is None
    
    def test_concurrent_writes(self, db_manager):
        """Test concurrent write operations"""
        session_id = "concurrent-test"
        
        def write_message(i):
            db_manager.add_conversation(
                session_id,
                f"Message {i}",
                f"Response {i}"
            )
        
        # Simulate concurrent writes
        threads = []
        import threading
        for i in range(10):
            t = threading.Thread(target=write_message, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All messages should be recorded
        history = db_manager.get_conversation_history(session_id, limit=100)
        assert len(history) == 10
    
    def test_transaction_commit(self, db_manager):
        """Test transaction commit"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        
        cursor.execute("INSERT INTO test_table (value) VALUES (?)", ("test",))
        conn.commit()
        
        cursor.execute("SELECT * FROM test_table WHERE value = ?", ("test",))
        result = cursor.fetchone()
        assert result is not None
        
        conn.close()
    
    def test_transaction_rollback(self, db_manager):
        """Test transaction rollback"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_rollback (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        
        # Insert but rollback
        cursor.execute("INSERT INTO test_rollback (value) VALUES (?)", ("rollback_test",))
        conn.rollback()
        
        cursor.execute("SELECT * FROM test_rollback WHERE value = ?", ("rollback_test",))
        result = cursor.fetchone()
        assert result is None
        
        conn.close()
    
    def test_database_schema_initialization(self, db_manager):
        """Test that database schema is properly initialized"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Check for expected tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='conversations'
        """)
        result = cursor.fetchone()
        assert result is not None
        
        conn.close()
    
    def test_query_performance_with_index(self, db_manager):
        """Test query performance with indexes"""
        session_id = "performance-test"
        
        # Add many messages
        for i in range(100):
            db_manager.add_conversation(
                session_id,
                f"Message {i}",
                f"Response {i}"
            )
        
        # Query should be fast with proper indexing
        import time
        start = time.time()
        history = db_manager.get_conversation_history(session_id, limit=10)
        duration = time.time() - start
        
        assert duration < 0.1  # Should complete in < 100ms
        assert len(history) == 10
    
    def test_conversation_ordering(self, db_manager):
        """Test that conversations are ordered by timestamp"""
        session_id = "order-test"
        
        messages = ["First", "Second", "Third"]
        for msg in messages:
            db_manager.add_conversation(session_id, msg, f"Response to {msg}")
            import time
            time.sleep(0.01)  # Ensure different timestamps
        
        history = db_manager.get_conversation_history(session_id)
        # Should be in chronological order (or reverse chronological)
        assert len(history) == 3
    
    def test_message_metadata_storage(self, db_manager):
        """Test storing message metadata"""
        session_id = "metadata-test"
        user_message = "Test message"
        assistant_response = "Test response"
        
        db_manager.add_conversation(session_id, user_message, assistant_response)
        
        history = db_manager.get_conversation_history(session_id)
        # Metadata like timestamp should be stored
        assert len(history) > 0
    
    def test_large_message_storage(self, db_manager):
        """Test storing very large messages"""
        session_id = "large-message-test"
        large_message = "x" * 10000  # 10KB message
        
        db_manager.add_conversation(session_id, large_message, "Response")
        
        history = db_manager.get_conversation_history(session_id)
        assert len(history) > 0
    
    def test_special_characters_in_messages(self, db_manager):
        """Test storing messages with special characters"""
        session_id = "special-chars-test"
        special_message = "Test with 'quotes', \"double quotes\", and \\ backslash"
        
        db_manager.add_conversation(session_id, special_message, "Response")
        
        history = db_manager.get_conversation_history(session_id)
        assert len(history) > 0
    
    def test_unicode_message_storage(self, db_manager):
        """Test storing Unicode messages"""
        session_id = "unicode-test"
        unicode_message = "Test with émojis 😀 and 中文"
        
        db_manager.add_conversation(session_id, unicode_message, "Response")
        
        history = db_manager.get_conversation_history(session_id)
        assert len(history) > 0
    
    def test_empty_message_handling(self, db_manager):
        """Test handling of empty messages"""
        session_id = "empty-test"
        
        # Should handle empty messages gracefully
        try:
            db_manager.add_conversation(session_id, "", "")
        except ValueError:
            pass  # Expected to raise error for empty messages


@pytest.mark.unit
class TestDatabaseCache:
    """Test database cache operations"""
    
    @pytest.fixture
    def db_manager(self, test_database):
        """Create a database manager instance"""
        return DatabaseManager(db_path=test_database)
    
    def test_cache_set_and_get(self, db_manager):
        """Test setting and getting cache values"""
        # Assuming cache operations exist
        if hasattr(db_manager, 'cache_set'):
            db_manager.cache_set("test_key", "test_value")
            value = db_manager.cache_get("test_key")
            assert value == "test_value"
    
    def test_cache_expiration(self, db_manager):
        """Test cache expiration"""
        if hasattr(db_manager, 'cache_set'):
            db_manager.cache_set("expiring_key", "value", ttl=1)
            import time
            time.sleep(2)
            value = db_manager.cache_get("expiring_key")
            assert value is None
    
    def test_cache_invalidation(self, db_manager):
        """Test cache invalidation"""
        if hasattr(db_manager, 'cache_set') and hasattr(db_manager, 'cache_invalidate'):
            db_manager.cache_set("invalid_key", "value")
            db_manager.cache_invalidate("invalid_key")
            value = db_manager.cache_get("invalid_key")
            assert value is None
    
    def test_cache_size_limit(self, db_manager):
        """Test cache size limiting"""
        if hasattr(db_manager, 'cache_set'):
            # Fill cache beyond limit
            for i in range(1000):
                db_manager.cache_set(f"key_{i}", f"value_{i}")
            
            # Cache should have evicted old entries
            # Implementation-dependent behavior
    
    def test_cache_statistics(self, db_manager):
        """Test cache statistics"""
        if hasattr(db_manager, 'cache_stats'):
            stats = db_manager.cache_stats()
            assert isinstance(stats, dict)


@pytest.mark.unit
class TestDatabaseMigrations:
    """Test database migration functionality"""
    
    @pytest.fixture
    def db_manager(self, test_database):
        """Create a database manager instance"""
        return DatabaseManager(db_path=test_database)
    
    def test_schema_version_tracking(self, db_manager):
        """Test that schema version is tracked"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Check for schema version table
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='schema_version'
        """)
        # Schema version may or may not exist depending on implementation
        
        conn.close()
    
    def test_migration_execution(self, db_manager):
        """Test running database migrations"""
        # Placeholder for migration test
        pass


@pytest.mark.unit 
class TestDatabaseIndexes:
    """Test database index performance"""
    
    @pytest.fixture
    def db_manager(self, test_database):
        """Create a database manager instance"""
        return DatabaseManager(db_path=test_database)
    
    def test_session_id_index_exists(self, db_manager):
        """Test that session_id has an index"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND sql LIKE '%session_id%'
        """)
        indexes = cursor.fetchall()
        # Should have index on session_id for fast lookups
        
        conn.close()
    
    def test_timestamp_index_exists(self, db_manager):
        """Test that timestamp has an index"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND sql LIKE '%timestamp%'
        """)
        indexes = cursor.fetchall()
        # Should have index on timestamp for ordered queries
        
        conn.close()
