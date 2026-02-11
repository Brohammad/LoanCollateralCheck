"""
Budget manager for tracking and alerting on cost budgets.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import uuid
from collections import defaultdict

from cost_analysis.models import (
    BudgetAlert,
    BudgetPeriod,
)
from cost_analysis.tracker import CostTracker


class Budget:
    """Represents a cost budget for a specific period."""
    
    def __init__(
        self,
        name: str,
        limit: float,
        period: BudgetPeriod,
        alert_thresholds: List[float] = None,
        user_id: Optional[str] = None,
        feature: Optional[str] = None,
    ):
        """
        Initialize budget.
        
        Args:
            name: Budget name
            limit: Budget limit in currency
            period: Budget period
            alert_thresholds: Alert threshold percentages (e.g., [50, 75, 90])
            user_id: User ID for user-specific budgets
            feature: Feature name for feature-specific budgets
        """
        self.name = name
        self.limit = limit
        self.period = period
        self.alert_thresholds = alert_thresholds or [75.0, 90.0, 100.0]
        self.user_id = user_id
        self.feature = feature
        
        self.current_spend = 0.0
        self.period_start = self._get_period_start()
        self.period_end = self._get_period_end()
        
        self.alerts_sent: List[BudgetAlert] = []
        self.last_reset = datetime.utcnow()
    
    def _get_period_start(self) -> datetime:
        """Get start of current period."""
        now = datetime.utcnow()
        
        if self.period == BudgetPeriod.HOURLY:
            return now.replace(minute=0, second=0, microsecond=0)
        elif self.period == BudgetPeriod.DAILY:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif self.period == BudgetPeriod.WEEKLY:
            # Start of week (Monday)
            days_since_monday = now.weekday()
            return (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif self.period == BudgetPeriod.MONTHLY:
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif self.period == BudgetPeriod.YEARLY:
            return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return now
    
    def _get_period_end(self) -> datetime:
        """Get end of current period."""
        start = self.period_start
        
        if self.period == BudgetPeriod.HOURLY:
            return start + timedelta(hours=1)
        elif self.period == BudgetPeriod.DAILY:
            return start + timedelta(days=1)
        elif self.period == BudgetPeriod.WEEKLY:
            return start + timedelta(weeks=1)
        elif self.period == BudgetPeriod.MONTHLY:
            # Next month
            if start.month == 12:
                return start.replace(year=start.year + 1, month=1)
            else:
                return start.replace(month=start.month + 1)
        elif self.period == BudgetPeriod.YEARLY:
            return start.replace(year=start.year + 1)
        
        return start + timedelta(days=30)
    
    def should_reset(self) -> bool:
        """Check if budget period has ended and should be reset."""
        return datetime.utcnow() >= self.period_end
    
    def reset(self):
        """Reset budget for new period."""
        self.current_spend = 0.0
        self.period_start = self._get_period_start()
        self.period_end = self._get_period_end()
        self.alerts_sent.clear()
        self.last_reset = datetime.utcnow()
    
    def add_spend(self, amount: float) -> Optional[BudgetAlert]:
        """
        Add spending to budget.
        
        Args:
            amount: Amount to add
        
        Returns:
            BudgetAlert if threshold exceeded, None otherwise
        """
        self.current_spend += amount
        
        # Check thresholds
        percent_used = (self.current_spend / self.limit) * 100 if self.limit > 0 else 0
        
        for threshold in self.alert_thresholds:
            # Check if we've crossed this threshold and haven't alerted yet
            if percent_used >= threshold and not any(
                alert.threshold_percent == threshold for alert in self.alerts_sent
            ):
                alert = self._create_alert(threshold, percent_used)
                self.alerts_sent.append(alert)
                return alert
        
        return None
    
    def _create_alert(self, threshold: float, percent_used: float) -> BudgetAlert:
        """Create budget alert."""
        severity = "info"
        if percent_used >= 100:
            severity = "critical"
        elif percent_used >= 90:
            severity = "warning"
        
        return BudgetAlert(
            alert_id=str(uuid.uuid4()),
            budget_name=self.name,
            period=self.period,
            budget_limit=self.limit,
            current_spend=self.current_spend,
            threshold_percent=threshold,
            exceeded_at=datetime.utcnow(),
            severity=severity,
            affected_users=[self.user_id] if self.user_id else [],
            affected_features=[self.feature] if self.feature else [],
            message=f"Budget '{self.name}' {percent_used:.1f}% consumed (threshold: {threshold}%)",
            acknowledged=False,
        )
    
    def get_status(self) -> Dict:
        """Get budget status."""
        percent_used = (self.current_spend / self.limit) * 100 if self.limit > 0 else 0
        remaining = max(0, self.limit - self.current_spend)
        
        return {
            "name": self.name,
            "period": self.period.value,
            "limit": self.limit,
            "current_spend": self.current_spend,
            "remaining": remaining,
            "percent_used": percent_used,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "alerts_sent": len(self.alerts_sent),
            "status": (
                "critical" if percent_used >= 100
                else "warning" if percent_used >= 90
                else "ok"
            ),
        }


class BudgetManager:
    """
    Manages cost budgets and alerts.
    
    Features:
    - Multiple budget types (global, per-user, per-feature)
    - Automatic period resets
    - Alert generation
    - Budget enforcement
    """
    
    def __init__(
        self,
        cost_tracker: Optional[CostTracker] = None,
        check_interval: int = 60,  # seconds
    ):
        """
        Initialize budget manager.
        
        Args:
            cost_tracker: Cost tracker instance
            check_interval: How often to check budgets (seconds)
        """
        self.cost_tracker = cost_tracker
        self.check_interval = check_interval
        
        self.budgets: Dict[str, Budget] = {}
        self.alerts: List[BudgetAlert] = []
        
        self._check_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the budget manager."""
        if self._running:
            return
        
        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
    
    async def stop(self):
        """Stop the budget manager."""
        self._running = False
        
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
    
    def create_budget(
        self,
        name: str,
        limit: float,
        period: BudgetPeriod,
        alert_thresholds: Optional[List[float]] = None,
        user_id: Optional[str] = None,
        feature: Optional[str] = None,
    ) -> Budget:
        """
        Create a new budget.
        
        Args:
            name: Budget name
            limit: Budget limit
            period: Budget period
            alert_thresholds: Alert thresholds
            user_id: User ID for user-specific budgets
            feature: Feature name for feature-specific budgets
        
        Returns:
            Created budget
        """
        budget = Budget(
            name=name,
            limit=limit,
            period=period,
            alert_thresholds=alert_thresholds,
            user_id=user_id,
            feature=feature,
        )
        
        self.budgets[name] = budget
        return budget
    
    def get_budget(self, name: str) -> Optional[Budget]:
        """Get budget by name."""
        return self.budgets.get(name)
    
    def delete_budget(self, name: str) -> bool:
        """Delete budget."""
        if name in self.budgets:
            del self.budgets[name]
            return True
        return False
    
    async def record_spend(
        self,
        amount: float,
        user_id: Optional[str] = None,
        feature: Optional[str] = None,
    ) -> List[BudgetAlert]:
        """
        Record spending and check budgets.
        
        Args:
            amount: Spending amount
            user_id: User ID
            feature: Feature name
        
        Returns:
            List of alerts generated
        """
        new_alerts = []
        
        for budget in self.budgets.values():
            # Check if budget applies
            if budget.user_id and budget.user_id != user_id:
                continue
            if budget.feature and budget.feature != feature:
                continue
            
            # Add spend
            alert = budget.add_spend(amount)
            if alert:
                self.alerts.append(alert)
                new_alerts.append(alert)
        
        return new_alerts
    
    async def _check_loop(self):
        """Background loop for checking budgets."""
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_budgets()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in budget check loop: {e}")
    
    async def _check_budgets(self):
        """Check all budgets and reset if needed."""
        for budget in self.budgets.values():
            if budget.should_reset():
                budget.reset()
    
    def get_all_budgets(self) -> List[Dict]:
        """Get status of all budgets."""
        return [budget.get_status() for budget in self.budgets.values()]
    
    def get_user_budgets(self, user_id: str) -> List[Dict]:
        """Get budgets for a specific user."""
        return [
            budget.get_status()
            for budget in self.budgets.values()
            if budget.user_id == user_id or budget.user_id is None
        ]
    
    def get_alerts(
        self,
        acknowledged: Optional[bool] = None,
        severity: Optional[str] = None,
    ) -> List[BudgetAlert]:
        """
        Get budget alerts.
        
        Args:
            acknowledged: Filter by acknowledged status
            severity: Filter by severity
        
        Returns:
            List of alerts
        """
        alerts = self.alerts
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        if severity is not None:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
            acknowledged_by: User who acknowledged
        
        Returns:
            True if alert found and acknowledged
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.utcnow()
                alert.acknowledged_by = acknowledged_by
                return True
        return False
    
    def get_budget_summary(self) -> Dict:
        """Get summary of all budgets."""
        total_limit = sum(b.limit for b in self.budgets.values())
        total_spend = sum(b.current_spend for b in self.budgets.values())
        
        critical_count = sum(
            1 for b in self.budgets.values()
            if (b.current_spend / b.limit if b.limit > 0 else 0) >= 1.0
        )
        
        warning_count = sum(
            1 for b in self.budgets.values()
            if 0.9 <= (b.current_spend / b.limit if b.limit > 0 else 0) < 1.0
        )
        
        return {
            "total_budgets": len(self.budgets),
            "total_limit": total_limit,
            "total_spend": total_spend,
            "total_remaining": max(0, total_limit - total_spend),
            "critical_budgets": critical_count,
            "warning_budgets": warning_count,
            "total_alerts": len(self.alerts),
            "unacknowledged_alerts": len([a for a in self.alerts if not a.acknowledged]),
        }
