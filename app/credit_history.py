"""Simple SQLite-based credit history (conversation context) manager.

This manager stores conversation turns (user->assistant) per user_id and allows retrieval of recent context.
"""
import sqlite3
from typing import List, Tuple
import os
import json

DB_PATH = os.environ.get("SQLITE_PATH", "./data/credit_history.db")

class CreditHistoryManager:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DB_PATH
        self._ensure_db()

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path) or "", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                meta TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
        conn.close()

    def add_turn(self, user_id: str, role: str, text: str, meta: dict | None = None) -> None:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO history (user_id, role, text, meta) VALUES (?, ?, ?, ?)",
            (user_id, role, text, json.dumps(meta or {})),
        )
        conn.commit()
        conn.close()

    def get_recent(self, user_id: str, limit: int = 10) -> List[Tuple[str, str, str]]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT role, text, meta FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        rows = cur.fetchall()
        conn.close()
        # return in chronological order (oldest first)
        return list(reversed(rows))


# Simple CLI-style test function
if __name__ == "__main__":
    mgr = CreditHistoryManager()
    mgr.add_turn("user-1", "user", "Hi", {"note": "greeting"})
    mgr.add_turn("user-1", "assistant", "Hello — how can I help?", {})
    print(mgr.get_recent("user-1"))
