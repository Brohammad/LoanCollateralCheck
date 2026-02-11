"""
Database Manager with Connection Pooling
Handles all database operations with proper error handling and connection management.
"""

import sqlite3
import hashlib
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from queue import Queue
from threading import Lock

logger = logging.getLogger(__name__)


class ConnectionPool:
    """SQLite connection pool for thread-safe database access."""
    
    def __init__(self, database_path: str, pool_size: int = 5):
        self.database_path = database_path
        self.pool_size = pool_size
        self.pool: Queue = Queue(maxsize=pool_size)
        self.lock = Lock()
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool with connections."""
        for _ in range(self.pool_size):
            conn = self._create_connection()
            self.pool.put(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimized settings."""
        conn = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
            timeout=30.0
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
        conn.execute("PRAGMA temp_store = MEMORY")
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool (context manager)."""
        conn = self.pool.get()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            self.pool.put(conn)
    
    def close_all(self):
        """Close all connections in the pool."""
        while not self.pool.empty():
            conn = self.pool.get()
            conn.close()


class DatabaseManager:
    """Main database manager class."""
    
    def __init__(self, database_path: str, pool_size: int = 5):
        self.database_path = database_path
        self.pool = ConnectionPool(database_path, pool_size)
        logger.info(f"Database manager initialized: {database_path}")
    
    def initialize_database(self, schema_path: str):
        """Initialize database with schema from SQL file."""
        schema_file = Path(schema_path)
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        with self.pool.get_connection() as conn:
            conn.executescript(schema_sql)
        
        logger.info("Database initialized successfully")
    
    # Session Management
    def create_session(self, session_id: str, user_id: str, metadata: Optional[Dict] = None) -> bool:
        """Create a new user session."""
        try:
            with self.pool.get_connection() as conn:
                conn.execute(
                    """INSERT INTO user_sessions (session_id, user_id, session_metadata)
                       VALUES (?, ?, ?)""",
                    (session_id, user_id, json.dumps(metadata) if metadata else None)
                )
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Session already exists: {session_id}")
            return False
    
    def update_session_activity(self, session_id: str):
        """Update last activity timestamp for a session."""
        with self.pool.get_connection() as conn:
            conn.execute(
                "UPDATE user_sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = ?",
                (session_id,)
            )
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session information."""
        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM user_sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # Conversation History
    def add_conversation(
        self,
        session_id: str,
        user_message: str,
        agent_response: str,
        intent: Optional[str] = None,
        confidence: Optional[float] = None,
        response_time_ms: Optional[int] = None,
        token_count: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """Add a conversation to history."""
        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO conversation_history 
                   (session_id, user_message, agent_response, intent, confidence, 
                    response_time_ms, token_count, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, user_message, agent_response, intent, confidence,
                 response_time_ms, token_count, json.dumps(metadata) if metadata else None)
            )
            return cursor.lastrowid
    
    def get_recent_conversations(
        self,
        session_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """Get recent conversations for a session."""
        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM conversation_history 
                   WHERE session_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (session_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_conversation_context(
        self,
        session_id: str,
        max_tokens: int = 2000
    ) -> str:
        """Get conversation context within token limit."""
        conversations = self.get_recent_conversations(session_id, limit=10)
        context_parts = []
        total_tokens = 0
        
        for conv in reversed(conversations):  # Oldest first
            # Rough token estimation: 1 token ≈ 4 characters
            conv_tokens = (len(conv['user_message']) + len(conv['agent_response'])) // 4
            
            if total_tokens + conv_tokens > max_tokens:
                break
            
            context_parts.append(
                f"User: {conv['user_message']}\nAgent: {conv['agent_response']}"
            )
            total_tokens += conv_tokens
        
        return "\n\n".join(context_parts)
    
    # Credit History (Context Storage)
    def store_context(
        self,
        session_id: str,
        context_type: str,
        context_key: str,
        context_value: str,
        relevance_score: float = 1.0,
        ttl_days: Optional[int] = 30,
        metadata: Optional[Dict] = None
    ):
        """Store context information with optional TTL."""
        expires_at = None
        if ttl_days:
            expires_at = (datetime.now() + timedelta(days=ttl_days)).isoformat()
        
        with self.pool.get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO credit_history 
                   (session_id, context_type, context_key, context_value, 
                    relevance_score, expires_at, metadata, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (session_id, context_type, context_key, context_value,
                 relevance_score, expires_at, json.dumps(metadata) if metadata else None)
            )
    
    def get_context(
        self,
        session_id: str,
        context_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Retrieve context information."""
        query = """
            SELECT * FROM credit_history 
            WHERE session_id = ? 
            AND (expires_at IS NULL OR expires_at > datetime('now'))
        """
        params = [session_id]
        
        if context_type:
            query += " AND context_type = ?"
            params.append(context_type)
        
        query += " ORDER BY relevance_score DESC, updated_at DESC LIMIT ?"
        params.append(limit)
        
        with self.pool.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def prune_old_context(self, days: int = 30) -> int:
        """Remove expired context data."""
        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                """DELETE FROM credit_history 
                   WHERE expires_at IS NOT NULL 
                   AND expires_at < datetime('now')"""
            )
            return cursor.rowcount
    
    # Search Cache
    @staticmethod
    def _hash_query(query: str, search_type: str) -> str:
        """Generate hash for cache key."""
        content = f"{search_type}:{query}".lower().strip()
        return hashlib.sha256(content.encode()).hexdigest()
    
    def cache_search_results(
        self,
        query: str,
        search_type: str,
        results: List[Dict],
        ttl_seconds: int = 3600
    ):
        """Cache search results."""
        query_hash = self._hash_query(query, search_type)
        expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()
        
        with self.pool.get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO search_cache 
                   (query_hash, query_text, search_type, results, result_count, 
                    expires_at, ttl_seconds)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (query_hash, query, search_type, json.dumps(results),
                 len(results), expires_at, ttl_seconds)
            )
    
    def get_cached_search(
        self,
        query: str,
        search_type: str
    ) -> Optional[List[Dict]]:
        """Retrieve cached search results."""
        query_hash = self._hash_query(query, search_type)
        
        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                """SELECT results FROM search_cache 
                   WHERE query_hash = ? 
                   AND expires_at > datetime('now')""",
                (query_hash,)
            )
            row = cursor.fetchone()
            
            if row:
                # Update access tracking
                conn.execute(
                    """UPDATE search_cache 
                       SET accessed_at = CURRENT_TIMESTAMP, 
                           access_count = access_count + 1
                       WHERE query_hash = ?""",
                    (query_hash,)
                )
                return json.loads(row['results'])
        
        return None
    
    def clear_expired_cache(self) -> int:
        """Remove expired cache entries."""
        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM search_cache WHERE expires_at < datetime('now')"
            )
            return cursor.rowcount
    
    # Response Cache
    def cache_response(
        self,
        input_text: str,
        model_name: str,
        response_text: str,
        token_count: int,
        ttl_seconds: int = 7200
    ):
        """Cache API response."""
        input_hash = hashlib.sha256(f"{model_name}:{input_text}".encode()).hexdigest()
        expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()
        
        with self.pool.get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO response_cache 
                   (input_hash, input_text, model_name, response_text, 
                    token_count, expires_at, ttl_seconds)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (input_hash, input_text, model_name, response_text,
                 token_count, expires_at, ttl_seconds)
            )
    
    def get_cached_response(
        self,
        input_text: str,
        model_name: str
    ) -> Optional[Tuple[str, int]]:
        """Retrieve cached response."""
        input_hash = hashlib.sha256(f"{model_name}:{input_text}".encode()).hexdigest()
        
        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                """SELECT response_text, token_count FROM response_cache 
                   WHERE input_hash = ? 
                   AND expires_at > datetime('now')""",
                (input_hash,)
            )
            row = cursor.fetchone()
            
            if row:
                # Update access tracking
                conn.execute(
                    """UPDATE response_cache 
                       SET accessed_at = CURRENT_TIMESTAMP, 
                           access_count = access_count + 1
                       WHERE input_hash = ?""",
                    (input_hash,)
                )
                return row['response_text'], row['token_count']
        
        return None
    
    # Critique History
    def add_critique_iteration(
        self,
        conversation_id: int,
        iteration: int,
        planner_response: str,
        critique_score: float,
        accuracy_score: float,
        completeness_score: float,
        clarity_score: float,
        critique_feedback: str
    ):
        """Add critique iteration to history."""
        with self.pool.get_connection() as conn:
            conn.execute(
                """INSERT INTO critique_history 
                   (conversation_id, iteration, planner_response, critique_score,
                    accuracy_score, completeness_score, clarity_score, critique_feedback)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (conversation_id, iteration, planner_response, critique_score,
                 accuracy_score, completeness_score, clarity_score, critique_feedback)
            )
    
    def get_critique_history(self, conversation_id: int) -> List[Dict]:
        """Get all critique iterations for a conversation."""
        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM critique_history 
                   WHERE conversation_id = ? 
                   ORDER BY iteration""",
                (conversation_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    # API Call Logging
    def log_api_call(
        self,
        api_name: str,
        endpoint: Optional[str] = None,
        request_method: Optional[str] = None,
        request_params: Optional[Dict] = None,
        response_status: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        token_count: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Log API call for monitoring."""
        with self.pool.get_connection() as conn:
            conn.execute(
                """INSERT INTO api_call_logs 
                   (api_name, endpoint, request_method, request_params, 
                    response_status, response_time_ms, token_count, error_message)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (api_name, endpoint, request_method,
                 json.dumps(request_params) if request_params else None,
                 response_status, response_time_ms, token_count, error_message)
            )
    
    # Performance Metrics
    def record_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Record performance metric."""
        with self.pool.get_connection() as conn:
            conn.execute(
                """INSERT INTO performance_metrics 
                   (metric_name, metric_value, metric_unit, session_id, metadata)
                   VALUES (?, ?, ?, ?, ?)""",
                (metric_name, metric_value, metric_unit, session_id,
                 json.dumps(metadata) if metadata else None)
            )
    
    def get_metrics_summary(
        self,
        metric_name: str,
        hours: int = 24
    ) -> Dict[str, float]:
        """Get summary statistics for a metric."""
        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                """SELECT 
                   COUNT(*) as count,
                   AVG(metric_value) as avg,
                   MIN(metric_value) as min,
                   MAX(metric_value) as max,
                   SUM(metric_value) as total
                   FROM performance_metrics 
                   WHERE metric_name = ? 
                   AND created_at >= datetime('now', ? || ' hours')""",
                (metric_name, f"-{hours}")
            )
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    # Maintenance
    def vacuum_database(self):
        """Optimize database (run periodically)."""
        with self.pool.get_connection() as conn:
            conn.execute("VACUUM")
        logger.info("Database vacuumed successfully")
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        stats = {}
        tables = [
            'user_sessions', 'conversation_history', 'credit_history',
            'search_cache', 'response_cache', 'critique_history',
            'api_call_logs', 'performance_metrics'
        ]
        
        with self.pool.get_connection() as conn:
            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = cursor.fetchone()['count']
        
        return stats
    
    def close(self):
        """Close all connections."""
        self.pool.close_all()
        logger.info("Database manager closed")
