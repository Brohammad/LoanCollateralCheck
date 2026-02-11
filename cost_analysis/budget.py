"""
Budget management with alerts and enforcement
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import sqlite3
from pathlib import Path

from cost_analysis.models import (
    Budget,
    BudgetPeriod,
    BudgetAlert,
    AlertLevel,
    ModelType,
)


class BudgetManager:
    """
    Manages budgets and generates alerts when thresholds are exceeded.
    """
    
    def __init__(self, db_path: str = "data/cost_tracking.db"):
        """
        Initialize budget manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema for budgets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Budgets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                period TEXT NOT NULL,
                limit_amount REAL NOT NULL,
                user_id TEXT,
                model TEXT,
                warning_threshold REAL NOT NULL,
                critical_threshold REAL NOT NULL,
                current_usage REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Budget alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget_alerts (
                id TEXT PRIMARY KEY,
                budget_id TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                current_usage REAL NOT NULL,
                budget_limit REAL NOT NULL,
                usage_percentage REAL NOT NULL,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_at TEXT,
                acknowledged_by TEXT,
                FOREIGN KEY (budget_id) REFERENCES budgets(id)
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_budget_period 
            ON budgets(period)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_timestamp 
            ON budget_alerts(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def create_budget(
        self,
        name: str,
        period: BudgetPeriod,
        limit: float,
        user_id: Optional[str] = None,
        model: Optional[ModelType] = None,
        warning_threshold: float = 0.8,
        critical_threshold: float = 0.95,
    ) -> Budget:
        """
        Create a new budget.
        
        Args:
            name: Budget name
            period: Budget period (daily/weekly/monthly/yearly)
            limit: Budget limit in USD
            user_id: Filter by user (optional)
            model: Filter by model (optional)
            warning_threshold: Warning threshold (0-1)
            critical_threshold: Critical threshold (0-1)
        
        Returns:
            Created Budget object
        """
        budget = Budget(
            id=str(uuid.uuid4()),
            name=name,
            period=period,
            limit=limit,
            user_id=user_id,
            model=model,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            current_usage=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO budgets (
                id, name, period, limit_amount, user_id, model,
                warning_threshold, critical_threshold, current_usage,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            budget.id,
            budget.name,
            budget.period.value,
            budget.limit,
            budget.user_id,
            budget.model.value if budget.model else None,
            budget.warning_threshold,
            budget.critical_threshold,
            budget.current_usage,
            budget.created_at.isoformat(),
            budget.updated_at.isoformat(),
        ))
        
        conn.commit()
        conn.close()
        
        return budget
    
    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """Get budget by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM budgets WHERE id = ?
        """, (budget_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return Budget(
            id=row[0],
            name=row[1],
            period=BudgetPeriod(row[2]),
            limit=row[3],
            user_id=row[4],
            model=ModelType(row[5]) if row[5] else None,
            warning_threshold=row[6],
            critical_threshold=row[7],
            current_usage=row[8],
            created_at=datetime.fromisoformat(row[9]),
            updated_at=datetime.fromisoformat(row[10]),
        )
    
    def list_budgets(
        self,
        user_id: Optional[str] = None,
        period: Optional[BudgetPeriod] = None,
    ) -> List[Budget]:
        """
        List all budgets with optional filters.
        
        Args:
            user_id: Filter by user
            period: Filter by period
        
        Returns:
            List of Budget objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM budgets WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if period:
            query += " AND period = ?"
            params.append(period.value)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        budgets = []
        for row in rows:
            budgets.append(Budget(
                id=row[0],
                name=row[1],
                period=BudgetPeriod(row[2]),
                limit=row[3],
                user_id=row[4],
                model=ModelType(row[5]) if row[5] else None,
                warning_threshold=row[6],
                critical_threshold=row[7],
                current_usage=row[8],
                created_at=datetime.fromisoformat(row[9]),
                updated_at=datetime.fromisoformat(row[10]),
            ))
        
        return budgets
    
    def update_budget_usage(
        self,
        budget_id: str,
        cost_tracker,
    ) -> Budget:
        """
        Update budget usage from cost tracker.
        
        Args:
            budget_id: Budget ID
            cost_tracker: CostTracker instance
        
        Returns:
            Updated Budget object
        """
        budget = self.get_budget(budget_id)
        if not budget:
            raise ValueError(f"Budget {budget_id} not found")
        
        # Calculate time period based on budget period
        end_time = datetime.utcnow()
        if budget.period == BudgetPeriod.DAILY:
            start_time = end_time - timedelta(days=1)
        elif budget.period == BudgetPeriod.WEEKLY:
            start_time = end_time - timedelta(weeks=1)
        elif budget.period == BudgetPeriod.MONTHLY:
            start_time = end_time - timedelta(days=30)
        else:  # YEARLY
            start_time = end_time - timedelta(days=365)
        
        # Get total cost from tracker
        current_usage = cost_tracker.get_total_cost(
            start_time=start_time,
            end_time=end_time,
            user_id=budget.user_id,
        )
        
        budget.current_usage = current_usage
        budget.updated_at = datetime.utcnow()
        
        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE budgets 
            SET current_usage = ?, updated_at = ?
            WHERE id = ?
        """, (current_usage, budget.updated_at.isoformat(), budget_id))
        
        conn.commit()
        conn.close()
        
        # Check for alerts
        self._check_budget_alerts(budget)
        
        return budget
    
    def _check_budget_alerts(self, budget: Budget):
        """Check budget and create alerts if needed"""
        alerts = []
        
        if budget.is_exceeded:
            alert = self._create_alert(
                budget=budget,
                level=AlertLevel.CRITICAL,
                message=f"Budget '{budget.name}' exceeded! Usage: ${budget.current_usage:.2f} / ${budget.limit:.2f} ({budget.usage_percentage:.1f}%)",
            )
            alerts.append(alert)
        elif budget.is_critical:
            alert = self._create_alert(
                budget=budget,
                level=AlertLevel.CRITICAL,
                message=f"Budget '{budget.name}' at critical level! Usage: ${budget.current_usage:.2f} / ${budget.limit:.2f} ({budget.usage_percentage:.1f}%)",
            )
            alerts.append(alert)
        elif budget.is_warning:
            alert = self._create_alert(
                budget=budget,
                level=AlertLevel.WARNING,
                message=f"Budget '{budget.name}' at warning level. Usage: ${budget.current_usage:.2f} / ${budget.limit:.2f} ({budget.usage_percentage:.1f}%)",
            )
            alerts.append(alert)
        
        return alerts
    
    def _create_alert(
        self,
        budget: Budget,
        level: AlertLevel,
        message: str,
    ) -> BudgetAlert:
        """Create a budget alert"""
        alert = BudgetAlert(
            id=str(uuid.uuid4()),
            budget_id=budget.id,
            level=level,
            message=message,
            timestamp=datetime.utcnow(),
            current_usage=budget.current_usage,
            budget_limit=budget.limit,
            usage_percentage=budget.usage_percentage,
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO budget_alerts (
                id, budget_id, level, message, timestamp,
                current_usage, budget_limit, usage_percentage,
                acknowledged, acknowledged_at, acknowledged_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.id,
            alert.budget_id,
            alert.level.value,
            alert.message,
            alert.timestamp.isoformat(),
            alert.current_usage,
            alert.budget_limit,
            alert.usage_percentage,
            int(alert.acknowledged),
            alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            alert.acknowledged_by,
        ))
        
        conn.commit()
        conn.close()
        
        return alert
    
    def get_alerts(
        self,
        budget_id: Optional[str] = None,
        level: Optional[AlertLevel] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> List[BudgetAlert]:
        """
        Get budget alerts.
        
        Args:
            budget_id: Filter by budget
            level: Filter by alert level
            acknowledged: Filter by acknowledgement status
            limit: Maximum number of alerts
        
        Returns:
            List of BudgetAlert objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM budget_alerts WHERE 1=1"
        params = []
        
        if budget_id:
            query += " AND budget_id = ?"
            params.append(budget_id)
        
        if level:
            query += " AND level = ?"
            params.append(level.value)
        
        if acknowledged is not None:
            query += " AND acknowledged = ?"
            params.append(int(acknowledged))
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        alerts = []
        for row in rows:
            alerts.append(BudgetAlert(
                id=row[0],
                budget_id=row[1],
                level=AlertLevel(row[2]),
                message=row[3],
                timestamp=datetime.fromisoformat(row[4]),
                current_usage=row[5],
                budget_limit=row[6],
                usage_percentage=row[7],
                acknowledged=bool(row[8]),
                acknowledged_at=datetime.fromisoformat(row[9]) if row[9] else None,
                acknowledged_by=row[10],
            ))
        
        return alerts
    
    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
    ) -> BudgetAlert:
        """
        Acknowledge a budget alert.
        
        Args:
            alert_id: Alert ID
            acknowledged_by: User who acknowledged
        
        Returns:
            Updated BudgetAlert object
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        acknowledged_at = datetime.utcnow()
        
        cursor.execute("""
            UPDATE budget_alerts
            SET acknowledged = 1, acknowledged_at = ?, acknowledged_by = ?
            WHERE id = ?
        """, (acknowledged_at.isoformat(), acknowledged_by, alert_id))
        
        conn.commit()
        
        # Fetch updated alert
        cursor.execute("SELECT * FROM budget_alerts WHERE id = ?", (alert_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise ValueError(f"Alert {alert_id} not found")
        
        return BudgetAlert(
            id=row[0],
            budget_id=row[1],
            level=AlertLevel(row[2]),
            message=row[3],
            timestamp=datetime.fromisoformat(row[4]),
            current_usage=row[5],
            budget_limit=row[6],
            usage_percentage=row[7],
            acknowledged=bool(row[8]),
            acknowledged_at=datetime.fromisoformat(row[9]) if row[9] else None,
            acknowledged_by=row[10],
        )
    
    def delete_budget(self, budget_id: str):
        """Delete a budget and its alerts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete alerts first
        cursor.execute("DELETE FROM budget_alerts WHERE budget_id = ?", (budget_id,))
        
        # Delete budget
        cursor.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
        
        conn.commit()
        conn.close()
    
    def reset_budget(self, budget_id: str) -> Budget:
        """Reset budget usage to zero"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updated_at = datetime.utcnow()
        
        cursor.execute("""
            UPDATE budgets
            SET current_usage = 0, updated_at = ?
            WHERE id = ?
        """, (updated_at.isoformat(), budget_id))
        
        conn.commit()
        conn.close()
        
        return self.get_budget(budget_id)
