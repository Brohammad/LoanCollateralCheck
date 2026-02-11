"""
Cost tracker for monitoring LLM API usage and costs
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import sqlite3
from pathlib import Path

from cost_analysis.models import (
    TokenUsage,
    CostRecord,
    ModelType,
    RequestType,
    UsageSummary,
)
from cost_analysis.pricing import calculate_cost


class CostTracker:
    """
    Tracks token usage and costs for LLM API calls.
    
    Stores usage data in SQLite database for analysis and reporting.
    """
    
    def __init__(self, db_path: str = "data/cost_tracking.db"):
        """
        Initialize cost tracker.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Token usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                request_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                request_type TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                user_id TEXT,
                session_id TEXT,
                conversation_id TEXT,
                agent_name TEXT,
                metadata TEXT
            )
        """)
        
        # Cost records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_records (
                request_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                input_cost REAL NOT NULL,
                output_cost REAL NOT NULL,
                total_cost REAL NOT NULL,
                input_price_per_1k REAL NOT NULL,
                output_price_per_1k REAL NOT NULL,
                user_id TEXT,
                FOREIGN KEY (request_id) REFERENCES token_usage(request_id)
            )
        """)
        
        # Indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON token_usage(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id 
            ON token_usage(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model 
            ON token_usage(model)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cost_timestamp 
            ON cost_records(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def track_usage(
        self,
        model: ModelType,
        request_type: RequestType,
        input_tokens: int,
        output_tokens: int,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CostRecord:
        """
        Track token usage and calculate cost.
        
        Args:
            model: LLM model used
            request_type: Type of request
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            user_id: User identifier (optional)
            session_id: Session identifier (optional)
            conversation_id: Conversation identifier (optional)
            agent_name: Agent that made the request (optional)
            metadata: Additional metadata (optional)
        
        Returns:
            CostRecord with usage and cost information
        """
        # Create usage record
        usage = TokenUsage(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            model=model,
            request_type=request_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            user_id=user_id,
            session_id=session_id,
            conversation_id=conversation_id,
            agent_name=agent_name,
            metadata=metadata or {},
        )
        
        # Calculate cost
        cost_data = calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        
        # Create cost record
        cost_record = CostRecord(
            usage=usage,
            input_cost=cost_data["input_cost"],
            output_cost=cost_data["output_cost"],
            total_cost=cost_data["total_cost"],
            input_price_per_1k=cost_data["input_price_per_1k"],
            output_price_per_1k=cost_data["output_price_per_1k"],
        )
        
        # Save to database
        self._save_record(cost_record)
        
        return cost_record
    
    def _save_record(self, record: CostRecord):
        """Save cost record to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save usage
        import json
        cursor.execute("""
            INSERT INTO token_usage (
                request_id, timestamp, model, request_type,
                input_tokens, output_tokens, total_tokens,
                user_id, session_id, conversation_id, agent_name, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.usage.request_id,
            record.usage.timestamp.isoformat(),
            record.usage.model.value,
            record.usage.request_type.value,
            record.usage.input_tokens,
            record.usage.output_tokens,
            record.usage.total_tokens,
            record.usage.user_id,
            record.usage.session_id,
            record.usage.conversation_id,
            record.usage.agent_name,
            json.dumps(record.usage.metadata),
        ))
        
        # Save cost
        cursor.execute("""
            INSERT INTO cost_records (
                request_id, timestamp, model,
                input_cost, output_cost, total_cost,
                input_price_per_1k, output_price_per_1k, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.usage.request_id,
            record.usage.timestamp.isoformat(),
            record.usage.model.value,
            record.input_cost,
            record.output_cost,
            record.total_cost,
            record.input_price_per_1k,
            record.output_price_per_1k,
            record.usage.user_id,
        ))
        
        conn.commit()
        conn.close()
    
    def get_usage_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        model: Optional[ModelType] = None,
    ) -> UsageSummary:
        """
        Get usage summary for a time period.
        
        Args:
            start_time: Start of time period (default: 24 hours ago)
            end_time: End of time period (default: now)
            user_id: Filter by user (optional)
            model: Filter by model (optional)
        
        Returns:
            UsageSummary with aggregated statistics
        """
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(days=1)
        if end_time is None:
            end_time = datetime.utcnow()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT 
                u.model,
                u.request_type,
                u.user_id,
                COUNT(*) as request_count,
                SUM(u.input_tokens) as total_input,
                SUM(u.output_tokens) as total_output,
                SUM(u.total_tokens) as total_tokens,
                SUM(c.total_cost) as total_cost
            FROM token_usage u
            JOIN cost_records c ON u.request_id = c.request_id
            WHERE u.timestamp >= ? AND u.timestamp <= ?
        """
        params = [start_time.isoformat(), end_time.isoformat()]
        
        if user_id:
            query += " AND u.user_id = ?"
            params.append(user_id)
        
        if model:
            query += " AND u.model = ?"
            params.append(model.value)
        
        query += " GROUP BY u.model, u.request_type, u.user_id"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Aggregate results
        summary = UsageSummary(
            start_time=start_time,
            end_time=end_time,
        )
        
        for row in rows:
            model_str, request_type_str, uid, count, inp, out, total, cost = row
            
            summary.total_requests += count
            summary.input_tokens += inp
            summary.output_tokens += out
            summary.total_tokens += total
            summary.total_cost += cost
            
            # By request type
            req_type = RequestType(request_type_str)
            summary.requests_by_type[req_type] = summary.requests_by_type.get(req_type, 0) + count
            
            # By model
            model_enum = ModelType(model_str)
            summary.requests_by_model[model_enum] = summary.requests_by_model.get(model_enum, 0) + count
            summary.tokens_by_model[model_enum] = summary.tokens_by_model.get(model_enum, 0) + total
            summary.cost_by_model[model_enum] = summary.cost_by_model.get(model_enum, 0) + cost
            
            # By user
            if uid:
                summary.cost_by_user[uid] = summary.cost_by_user.get(uid, 0) + cost
        
        # Calculate averages
        if summary.total_requests > 0:
            summary.avg_tokens_per_request = summary.total_tokens / summary.total_requests
            summary.avg_cost_per_request = summary.total_cost / summary.total_requests
        
        conn.close()
        return summary
    
    def get_recent_requests(
        self,
        limit: int = 100,
        user_id: Optional[str] = None,
    ) -> List[CostRecord]:
        """
        Get recent cost records.
        
        Args:
            limit: Maximum number of records to return
            user_id: Filter by user (optional)
        
        Returns:
            List of recent CostRecord objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                u.request_id, u.timestamp, u.model, u.request_type,
                u.input_tokens, u.output_tokens, u.total_tokens,
                u.user_id, u.session_id, u.conversation_id, u.agent_name,
                c.input_cost, c.output_cost, c.total_cost,
                c.input_price_per_1k, c.output_price_per_1k
            FROM token_usage u
            JOIN cost_records c ON u.request_id = c.request_id
            WHERE 1=1
        """
        params = []
        
        if user_id:
            query += " AND u.user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY u.timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            usage = TokenUsage(
                request_id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                model=ModelType(row[2]),
                request_type=RequestType(row[3]),
                input_tokens=row[4],
                output_tokens=row[5],
                total_tokens=row[6],
                user_id=row[7],
                session_id=row[8],
                conversation_id=row[9],
                agent_name=row[10],
            )
            
            record = CostRecord(
                usage=usage,
                input_cost=row[11],
                output_cost=row[12],
                total_cost=row[13],
                input_price_per_1k=row[14],
                output_price_per_1k=row[15],
            )
            records.append(record)
        
        conn.close()
        return records
    
    def get_total_cost(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
    ) -> float:
        """
        Get total cost for a time period.
        
        Args:
            start_time: Start of time period (default: beginning of time)
            end_time: End of time period (default: now)
            user_id: Filter by user (optional)
        
        Returns:
            Total cost in USD
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT SUM(c.total_cost)
            FROM cost_records c
            JOIN token_usage u ON c.request_id = u.request_id
            WHERE 1=1
        """
        params = []
        
        if start_time:
            query += " AND c.timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND c.timestamp <= ?"
            params.append(end_time.isoformat())
        
        if user_id:
            query += " AND u.user_id = ?"
            params.append(user_id)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result[0] is not None else 0.0
    
    def cleanup_old_records(self, days: int = 90):
        """
        Delete records older than specified days.
        
        Args:
            days: Number of days to retain
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM cost_records
            WHERE timestamp < ?
        """, (cutoff_date.isoformat(),))
        
        cursor.execute("""
            DELETE FROM token_usage
            WHERE timestamp < ?
        """, (cutoff_date.isoformat(),))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
