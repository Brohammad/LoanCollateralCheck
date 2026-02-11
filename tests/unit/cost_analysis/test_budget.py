"""
Unit tests for budget manager
"""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from cost_analysis.budget import BudgetManager
from cost_analysis.tracker import CostTracker
from cost_analysis.models import ModelType, RequestType, BudgetPeriod, AlertLevel


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_budgets.db"
        yield str(db_path)


@pytest.fixture
def budget_manager(temp_db):
    """Create budget manager instance"""
    return BudgetManager(db_path=temp_db)


@pytest.fixture
def cost_tracker():
    """Create cost tracker instance"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = CostTracker(db_path=str(Path(tmpdir) / "test_costs.db"))
        yield tracker


class TestBudgetManager:
    """Test BudgetManager functionality"""
    
    def test_create_budget_daily(self, budget_manager):
        """Test creating daily budget"""
        budget = budget_manager.create_budget(
            name="Daily Budget",
            period=BudgetPeriod.DAILY,
            limit=10.0,
        )
        
        assert budget is not None
        assert budget.name == "Daily Budget"
        assert budget.period == BudgetPeriod.DAILY
        assert budget.limit == 10.0
        assert budget.current == 0.0
        assert budget.warning_threshold == 0.8
        assert budget.critical_threshold == 0.95
    
    def test_create_budget_monthly(self, budget_manager):
        """Test creating monthly budget"""
        budget = budget_manager.create_budget(
            name="Monthly Budget",
            period=BudgetPeriod.MONTHLY,
            limit=1000.0,
            warning_threshold=0.7,
            critical_threshold=0.9,
        )
        
        assert budget.period == BudgetPeriod.MONTHLY
        assert budget.limit == 1000.0
        assert budget.warning_threshold == 0.7
        assert budget.critical_threshold == 0.9
    
    def test_create_budget_with_filters(self, budget_manager):
        """Test creating budget with user and model filters"""
        budget = budget_manager.create_budget(
            name="User Budget",
            period=BudgetPeriod.WEEKLY,
            limit=50.0,
            user_id="user123",
            model=ModelType.GEMINI_15_PRO,
        )
        
        assert budget.user_id == "user123"
        assert budget.model == ModelType.GEMINI_15_PRO
    
    def test_get_budget(self, budget_manager):
        """Test getting budget by ID"""
        created = budget_manager.create_budget(
            name="Test Budget",
            period=BudgetPeriod.DAILY,
            limit=10.0,
        )
        
        retrieved = budget_manager.get_budget(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name
    
    def test_get_budget_nonexistent(self, budget_manager):
        """Test getting non-existent budget"""
        budget = budget_manager.get_budget("nonexistent")
        assert budget is None
    
    def test_list_budgets_empty(self, budget_manager):
        """Test listing budgets when none exist"""
        budgets = budget_manager.list_budgets()
        assert len(budgets) == 0
    
    def test_list_budgets_multiple(self, budget_manager):
        """Test listing multiple budgets"""
        for i in range(3):
            budget_manager.create_budget(
                name=f"Budget {i}",
                period=BudgetPeriod.DAILY,
                limit=10.0 * (i + 1),
            )
        
        budgets = budget_manager.list_budgets()
        assert len(budgets) == 3
    
    def test_list_budgets_filter_by_user(self, budget_manager):
        """Test filtering budgets by user"""
        budget_manager.create_budget(
            name="User1 Budget",
            period=BudgetPeriod.DAILY,
            limit=10.0,
            user_id="user1",
        )
        
        budget_manager.create_budget(
            name="User2 Budget",
            period=BudgetPeriod.DAILY,
            limit=10.0,
            user_id="user2",
        )
        
        # Filter by user1
        budgets = budget_manager.list_budgets(user_id="user1")
        assert len(budgets) == 1
        assert budgets[0].user_id == "user1"
    
    def test_list_budgets_filter_by_period(self, budget_manager):
        """Test filtering budgets by period"""
        budget_manager.create_budget(
            name="Daily Budget",
            period=BudgetPeriod.DAILY,
            limit=10.0,
        )
        
        budget_manager.create_budget(
            name="Monthly Budget",
            period=BudgetPeriod.MONTHLY,
            limit=1000.0,
        )
        
        # Filter by daily
        budgets = budget_manager.list_budgets(period=BudgetPeriod.DAILY)
        assert len(budgets) == 1
        assert budgets[0].period == BudgetPeriod.DAILY
    
    def test_update_budget_usage(self, budget_manager, cost_tracker):
        """Test updating budget usage from tracker"""
        # Create budget
        budget = budget_manager.create_budget(
            name="Test Budget",
            period=BudgetPeriod.DAILY,
            limit=10.0,
        )
        
        # Track some costs
        cost_tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000000,  # $1.25
            output_tokens=1000000,  # $5.00
        )
        
        # Update budget
        updated = budget_manager.update_budget_usage(budget.id, cost_tracker)
        
        assert updated.current == 6.25
        assert updated.percentage_used == 62.5
    
    def test_update_budget_usage_with_filters(self, budget_manager, cost_tracker):
        """Test updating budget with user/model filters"""
        # Create budget for specific user
        budget = budget_manager.create_budget(
            name="User Budget",
            period=BudgetPeriod.DAILY,
            limit=10.0,
            user_id="user123",
        )
        
        # Track costs for different users
        cost_tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000000,
            output_tokens=1000000,
            user_id="user123",
        )
        
        cost_tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000000,
            output_tokens=1000000,
            user_id="user456",
        )
        
        # Update budget (should only count user123)
        updated = budget_manager.update_budget_usage(budget.id, cost_tracker)
        
        assert updated.current == 6.25  # Only user123's cost
    
    def test_budget_alert_warning(self, budget_manager, cost_tracker):
        """Test warning alert generation"""
        # Create budget with low limit
        budget = budget_manager.create_budget(
            name="Test Budget",
            period=BudgetPeriod.DAILY,
            limit=10.0,
            warning_threshold=0.8,
        )
        
        # Track costs to exceed warning threshold (80% of $10 = $8)
        cost_tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1600000,  # $2.00
            output_tokens=1600000,  # $8.00
        )
        
        # Update budget (should trigger warning alert)
        updated = budget_manager.update_budget_usage(budget.id, cost_tracker)
        
        assert updated.percentage_used == 100.0
        
        # Check for alerts
        alerts = budget_manager.get_alerts(budget_id=budget.id)
        assert len(alerts) > 0
        assert any(a.level == AlertLevel.WARNING for a in alerts)
    
    def test_budget_alert_critical(self, budget_manager, cost_tracker):
        """Test critical alert generation"""
        # Create budget with low limit
        budget = budget_manager.create_budget(
            name="Test Budget",
            period=BudgetPeriod.DAILY,
            limit=5.0,
            critical_threshold=0.95,
        )
        
        # Track costs to exceed critical threshold (95% of $5 = $4.75)
        cost_tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=800000,  # $1.00
            output_tokens=800000,  # $4.00
        )
        
        # Update budget (should trigger critical alert)
        updated = budget_manager.update_budget_usage(budget.id, cost_tracker)
        
        assert updated.percentage_used == 100.0
        
        # Check for critical alert
        alerts = budget_manager.get_alerts(budget_id=budget.id, level=AlertLevel.CRITICAL)
        assert len(alerts) > 0
    
    def test_acknowledge_alert(self, budget_manager, cost_tracker):
        """Test acknowledging alerts"""
        # Create budget and trigger alert
        budget = budget_manager.create_budget(
            name="Test Budget",
            period=BudgetPeriod.DAILY,
            limit=5.0,
        )
        
        cost_tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=800000,
            output_tokens=800000,
        )
        
        budget_manager.update_budget_usage(budget.id, cost_tracker)
        
        # Get alerts
        alerts = budget_manager.get_alerts(budget_id=budget.id, acknowledged=False)
        assert len(alerts) > 0
        
        # Acknowledge first alert
        alert = alerts[0]
        acknowledged = budget_manager.acknowledge_alert(alert.id, "admin")
        
        assert acknowledged.acknowledged is True
        assert acknowledged.acknowledged_by == "admin"
        assert acknowledged.acknowledged_at is not None
    
    def test_get_alerts_filter_by_level(self, budget_manager, cost_tracker):
        """Test filtering alerts by level"""
        budget = budget_manager.create_budget(
            name="Test Budget",
            period=BudgetPeriod.DAILY,
            limit=10.0,
        )
        
        # Trigger warning
        cost_tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1600000,
            output_tokens=1600000,
        )
        budget_manager.update_budget_usage(budget.id, cost_tracker)
        
        # Get warning alerts
        alerts = budget_manager.get_alerts(level=AlertLevel.WARNING)
        assert len(alerts) > 0
        assert all(a.level == AlertLevel.WARNING for a in alerts)
    
    def test_delete_budget(self, budget_manager):
        """Test deleting budget"""
        budget = budget_manager.create_budget(
            name="Test Budget",
            period=BudgetPeriod.DAILY,
            limit=10.0,
        )
        
        # Verify it exists
        assert budget_manager.get_budget(budget.id) is not None
        
        # Delete it
        budget_manager.delete_budget(budget.id)
        
        # Verify it's gone
        assert budget_manager.get_budget(budget.id) is None
    
    def test_reset_budget(self, budget_manager, cost_tracker):
        """Test resetting budget"""
        budget = budget_manager.create_budget(
            name="Test Budget",
            period=BudgetPeriod.DAILY,
            limit=10.0,
        )
        
        # Add usage
        cost_tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000000,
            output_tokens=1000000,
        )
        budget = budget_manager.update_budget_usage(budget.id, cost_tracker)
        assert budget.current > 0
        
        # Reset
        reset = budget_manager.reset_budget(budget.id)
        
        assert reset.current == 0.0
        assert reset.percentage_used == 0.0
    
    def test_budget_period_range_daily(self, budget_manager):
        """Test period range calculation for daily budget"""
        budget = budget_manager.create_budget(
            name="Daily Budget",
            period=BudgetPeriod.DAILY,
            limit=10.0,
        )
        
        start, end = budget_manager._get_period_range(budget)
        
        # Should be today
        assert start.date() == datetime.utcnow().date()
        assert end.date() == datetime.utcnow().date()
    
    def test_budget_period_range_weekly(self, budget_manager):
        """Test period range calculation for weekly budget"""
        budget = budget_manager.create_budget(
            name="Weekly Budget",
            period=BudgetPeriod.WEEKLY,
            limit=50.0,
        )
        
        start, end = budget_manager._get_period_range(budget)
        
        # Should span 7 days
        delta = end - start
        assert delta.days == 6  # Inclusive range
    
    def test_budget_period_range_monthly(self, budget_manager):
        """Test period range calculation for monthly budget"""
        budget = budget_manager.create_budget(
            name="Monthly Budget",
            period=BudgetPeriod.MONTHLY,
            limit=1000.0,
        )
        
        start, end = budget_manager._get_period_range(budget)
        
        # Should be current month
        now = datetime.utcnow()
        assert start.month == now.month
        assert start.year == now.year
        assert end.month == now.month
        assert end.year == now.year
