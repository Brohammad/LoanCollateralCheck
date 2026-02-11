"""
Cost analytics for generating reports and visualizations.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import statistics

from cost_analysis.models import (
    CostBreakdown,
    CostTrend,
    BudgetPeriod,
)
from cost_analysis.tracker import CostTracker


class CostAnalytics:
    """
    Provides analytics and reporting for cost data.
    
    Features:
    - Cost breakdowns by various dimensions
    - Trend analysis
    - Forecasting
    - Anomaly detection
    - Report generation
    """
    
    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        """
        Initialize cost analytics.
        
        Args:
            cost_tracker: Cost tracker instance
        """
        self.cost_tracker = cost_tracker
    
    async def generate_cost_breakdown(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> CostBreakdown:
        """
        Generate detailed cost breakdown for a period.
        
        Args:
            period_start: Start of period
            period_end: End of period
        
        Returns:
            Cost breakdown
        """
        if not self.cost_tracker:
            return self._empty_breakdown(period_start, period_end)
        
        # Get operations for period
        all_operations = self.cost_tracker.get_recent_operations(limit=10000)
        operations = [
            (usage, cost)
            for usage, cost in all_operations
            if period_start <= usage.timestamp <= period_end
        ]
        
        if not operations:
            return self._empty_breakdown(period_start, period_end)
        
        # Calculate totals
        total_cost = sum(cost.total_cost for _, cost in operations)
        total_tokens = sum(usage.total_tokens for usage, _ in operations)
        total_requests = len(operations)
        
        # By category
        by_category = defaultdict(float)
        for _, cost in operations:
            by_category[cost.category.value] += cost.total_cost
        
        # By model
        by_model = defaultdict(float)
        for usage, cost in operations:
            by_model[usage.model_type.value] += cost.total_cost
        
        # By operation
        by_operation = defaultdict(float)
        for usage, cost in operations:
            by_operation[usage.operation_type.value] += cost.total_cost
        
        # By user
        by_user = defaultdict(float)
        for usage, cost in operations:
            if usage.user_id:
                by_user[usage.user_id] += cost.total_cost
        
        # By feature (from metadata)
        by_feature = defaultdict(float)
        for usage, cost in operations:
            feature = usage.metadata.get("feature", "unknown")
            by_feature[feature] += cost.total_cost
        
        # Calculate cache metrics
        cached_ops = sum(1 for usage, _ in operations if usage.cached_tokens > 0)
        cache_hit_rate = cached_ops / total_requests if total_requests > 0 else 0.0
        cost_savings_from_cache = sum(cost.cached_cost_savings for _, cost in operations)
        
        return CostBreakdown(
            period_start=period_start,
            period_end=period_end,
            total_cost=total_cost,
            by_category=dict(by_category),
            by_model=dict(by_model),
            by_operation=dict(by_operation),
            by_user=dict(by_user),
            by_feature=dict(by_feature),
            total_tokens=total_tokens,
            total_requests=total_requests,
            avg_cost_per_request=total_cost / total_requests if total_requests > 0 else 0.0,
            avg_tokens_per_request=total_tokens / total_requests if total_requests > 0 else 0.0,
            cache_hit_rate=cache_hit_rate,
            cost_savings_from_cache=cost_savings_from_cache,
        )
    
    def _empty_breakdown(self, period_start: datetime, period_end: datetime) -> CostBreakdown:
        """Return empty cost breakdown."""
        return CostBreakdown(
            period_start=period_start,
            period_end=period_end,
            total_cost=0.0,
            by_category={},
            by_model={},
            by_operation={},
            by_user={},
            by_feature={},
            total_tokens=0,
            total_requests=0,
            avg_cost_per_request=0.0,
            avg_tokens_per_request=0.0,
            cache_hit_rate=0.0,
            cost_savings_from_cache=0.0,
        )
    
    async def analyze_trend(
        self,
        period: BudgetPeriod,
        num_periods: int = 30,
    ) -> CostTrend:
        """
        Analyze cost trends over time.
        
        Args:
            period: Period granularity
            num_periods: Number of periods to analyze
        
        Returns:
            Cost trend analysis
        """
        if not self.cost_tracker:
            return self._empty_trend(period)
        
        # Calculate period duration
        if period == BudgetPeriod.HOURLY:
            period_duration = timedelta(hours=1)
        elif period == BudgetPeriod.DAILY:
            period_duration = timedelta(days=1)
        elif period == BudgetPeriod.WEEKLY:
            period_duration = timedelta(weeks=1)
        elif period == BudgetPeriod.MONTHLY:
            period_duration = timedelta(days=30)
        else:
            period_duration = timedelta(days=1)
        
        # Get data points
        data_points = []
        end_time = datetime.utcnow()
        
        for i in range(num_periods):
            period_end = end_time - (i * period_duration)
            period_start = period_end - period_duration
            
            breakdown = await self.generate_cost_breakdown(period_start, period_end)
            data_points.append((period_start, breakdown.total_cost))
        
        data_points.reverse()  # Chronological order
        
        # Analyze trend
        if len(data_points) < 3:
            return self._empty_trend(period)
        
        # Calculate trend direction
        costs = [cost for _, cost in data_points]
        recent_avg = statistics.mean(costs[-7:]) if len(costs) >= 7 else statistics.mean(costs)
        older_avg = statistics.mean(costs[:7]) if len(costs) >= 14 else statistics.mean(costs[:-7]) if len(costs) > 7 else recent_avg
        
        trend_percent = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0.0
        
        if trend_percent > 10:
            trend_direction = "increasing"
        elif trend_percent < -10:
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"
        
        # Simple forecast (linear extrapolation)
        if len(costs) >= 3:
            # Calculate simple moving average for forecast
            forecast_next_period = recent_avg * (1 + (trend_percent / 100))
            
            # Confidence interval (±20%)
            confidence_interval = (
                forecast_next_period * 0.8,
                forecast_next_period * 1.2,
            )
        else:
            forecast_next_period = recent_avg
            confidence_interval = (recent_avg, recent_avg)
        
        # Detect anomalies (values > 2 std deviations)
        if len(costs) >= 5:
            mean_cost = statistics.mean(costs)
            std_dev = statistics.stdev(costs)
            
            anomalies = [
                timestamp
                for timestamp, cost in data_points
                if abs(cost - mean_cost) > 2 * std_dev
            ]
        else:
            anomalies = []
        
        return CostTrend(
            period=period,
            data_points=data_points,
            trend_direction=trend_direction,
            trend_percent=trend_percent,
            forecast_next_period=forecast_next_period,
            confidence_interval=confidence_interval,
            anomalies=anomalies,
        )
    
    def _empty_trend(self, period: BudgetPeriod) -> CostTrend:
        """Return empty trend."""
        return CostTrend(
            period=period,
            data_points=[],
            trend_direction="stable",
            trend_percent=0.0,
            forecast_next_period=0.0,
            confidence_interval=(0.0, 0.0),
            anomalies=[],
        )
    
    async def generate_report(
        self,
        period_start: datetime,
        period_end: datetime,
        include_breakdowns: bool = True,
        include_trends: bool = True,
        include_top_users: int = 10,
        include_top_features: int = 10,
    ) -> Dict:
        """
        Generate comprehensive cost report.
        
        Args:
            period_start: Start of period
            period_end: End of period
            include_breakdowns: Include detailed breakdowns
            include_trends: Include trend analysis
            include_top_users: Number of top users to include
            include_top_features: Number of top features to include
        
        Returns:
            Comprehensive report dictionary
        """
        report = {
            "report_generated_at": datetime.utcnow().isoformat(),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "period_days": (period_end - period_start).days,
        }
        
        # Cost breakdown
        breakdown = await self.generate_cost_breakdown(period_start, period_end)
        report["summary"] = {
            "total_cost": breakdown.total_cost,
            "total_requests": breakdown.total_requests,
            "total_tokens": breakdown.total_tokens,
            "avg_cost_per_request": breakdown.avg_cost_per_request,
            "avg_tokens_per_request": breakdown.avg_tokens_per_request,
            "cache_hit_rate": breakdown.cache_hit_rate,
            "cost_savings_from_cache": breakdown.cost_savings_from_cache,
        }
        
        if include_breakdowns:
            report["breakdowns"] = {
                "by_category": breakdown.by_category,
                "by_model": breakdown.by_model,
                "by_operation": breakdown.by_operation,
            }
            
            # Top users
            if breakdown.by_user:
                sorted_users = sorted(
                    breakdown.by_user.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
                report["top_users"] = dict(sorted_users[:include_top_users])
            
            # Top features
            if breakdown.by_feature:
                sorted_features = sorted(
                    breakdown.by_feature.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
                report["top_features"] = dict(sorted_features[:include_top_features])
        
        if include_trends:
            # Analyze trend
            period_days = (period_end - period_start).days
            if period_days <= 1:
                trend_period = BudgetPeriod.HOURLY
            elif period_days <= 7:
                trend_period = BudgetPeriod.DAILY
            else:
                trend_period = BudgetPeriod.WEEKLY
            
            trend = await self.analyze_trend(trend_period, num_periods=min(30, period_days))
            
            report["trend"] = {
                "direction": trend.trend_direction,
                "change_percent": trend.trend_percent,
                "forecast_next_period": trend.forecast_next_period,
                "confidence_interval": trend.confidence_interval,
                "anomalies_detected": len(trend.anomalies),
            }
        
        # Calculate projections
        if breakdown.total_cost > 0:
            days_in_period = max((period_end - period_start).days, 1)
            daily_avg = breakdown.total_cost / days_in_period
            
            report["projections"] = {
                "daily_average": daily_avg,
                "weekly_projection": daily_avg * 7,
                "monthly_projection": daily_avg * 30,
                "yearly_projection": daily_avg * 365,
            }
        
        return report
    
    async def compare_periods(
        self,
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime,
    ) -> Dict:
        """
        Compare costs between two periods.
        
        Args:
            period1_start: Period 1 start
            period1_end: Period 1 end
            period2_start: Period 2 start
            period2_end: Period 2 end
        
        Returns:
            Comparison analysis
        """
        breakdown1 = await self.generate_cost_breakdown(period1_start, period1_end)
        breakdown2 = await self.generate_cost_breakdown(period2_start, period2_end)
        
        # Calculate changes
        cost_change = breakdown2.total_cost - breakdown1.total_cost
        cost_change_percent = (
            (cost_change / breakdown1.total_cost * 100)
            if breakdown1.total_cost > 0
            else 0.0
        )
        
        requests_change = breakdown2.total_requests - breakdown1.total_requests
        requests_change_percent = (
            (requests_change / breakdown1.total_requests * 100)
            if breakdown1.total_requests > 0
            else 0.0
        )
        
        return {
            "period1": {
                "start": period1_start.isoformat(),
                "end": period1_end.isoformat(),
                "total_cost": breakdown1.total_cost,
                "total_requests": breakdown1.total_requests,
                "avg_cost_per_request": breakdown1.avg_cost_per_request,
            },
            "period2": {
                "start": period2_start.isoformat(),
                "end": period2_end.isoformat(),
                "total_cost": breakdown2.total_cost,
                "total_requests": breakdown2.total_requests,
                "avg_cost_per_request": breakdown2.avg_cost_per_request,
            },
            "changes": {
                "cost_change": cost_change,
                "cost_change_percent": cost_change_percent,
                "requests_change": requests_change,
                "requests_change_percent": requests_change_percent,
                "efficiency_change": (
                    breakdown2.avg_cost_per_request - breakdown1.avg_cost_per_request
                ),
            },
        }
