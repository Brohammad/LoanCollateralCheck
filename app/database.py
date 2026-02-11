"""Enhanced SQLite database manager with comprehensive schema.

Implements:
- Conversation history (user messages + assistant responses)
- Credit history (context snapshots per conversation)
- Search results cache (query hash -> results with expiry)
"""
import sqlite3
import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DB_PATH = os.environ.get("SQLITE_PATH", "./data/credit_history.db")


class DatabaseManager:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DB_PATH
        self._ensure_db()

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Conversation history table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                intent TEXT,
                confidence REAL,
                agent_used TEXT,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Credit history table (context snapshots)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS credit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                context_snapshot TEXT NOT NULL,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
            """
        )

        # Search results cache table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                results TEXT NOT NULL,
                expiry DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Create indexes for performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_credit_history_conv ON credit_history(conversation_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cache_expiry ON search_cache(expiry);")

        conn.commit()
        conn.close()

    def add_conversation(
        self,
        user_id: str,
        message: str,
        response: str,
        intent: str | None = None,
        confidence: float | None = None,
        agent_used: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> int:
        """Add a conversation turn and return the conversation ID."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO conversations (user_id, message, response, intent, confidence, agent_used, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, message, response, intent, confidence, agent_used, json.dumps(metadata or {})),
        )
        conv_id = cur.lastrowid
        conn.commit()
        conn.close()
        return conv_id

    def add_credit_history(
        self, conversation_id: int, context_snapshot: Dict[str, Any], metadata: Dict[str, Any] | None = None
    ) -> None:
        """Add a credit history snapshot for a conversation."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO credit_history (conversation_id, context_snapshot, metadata) VALUES (?, ?, ?)",
            (conversation_id, json.dumps(context_snapshot), json.dumps(metadata or {})),
        )
        conn.commit()
        conn.close()

    def get_recent_conversations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversations for a user."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, message, response, intent, confidence, agent_used, metadata, timestamp
            FROM conversations
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in reversed(rows)]

    def get_cache(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results if not expired."""
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT results, expiry FROM search_cache WHERE query_hash = ?",
            (query_hash,),
        )
        row = cur.fetchone()
        conn.close()

        if row:
            results_json, expiry_str = row
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.now() < expiry:
                return json.loads(results_json)
            else:
                # Clean up expired entry
                self._delete_cache(query_hash)
        return None

    def set_cache(self, query: str, results: List[Dict[str, Any]], ttl_seconds: int = 3600) -> None:
        """Cache search results with expiry."""
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        expiry = datetime.now() + timedelta(seconds=ttl_seconds)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO search_cache (query_hash, query, results, expiry)
            VALUES (?, ?, ?, ?)
            """,
            (query_hash, query, json.dumps(results), expiry.isoformat()),
        )
        conn.commit()
        conn.close()

    def _delete_cache(self, query_hash: str) -> None:
        """Delete a cached entry."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM search_cache WHERE query_hash = ?", (query_hash,))
        conn.commit()
        conn.close()

    def cleanup_expired_cache(self) -> int:
        """Remove all expired cache entries. Returns number of deleted rows."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM search_cache WHERE expiry < ?", (datetime.now().isoformat(),))
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        return deleted
