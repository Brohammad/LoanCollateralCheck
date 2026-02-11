"""
Cost analytics and reporting
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json

from cost_analysis.models import CostRecord, UsageSummary, ModelType
from cost_analysis.tracker import CostTracker


class UsageReport:
    """
    Usage report with detailed analytics.
    """
    
    def __init__(
        self,
        summary: UsageSummary,
        top_users: List[Dict],
        top_models: List[Dict],
        daily_breakdown: Dict[str, float],
        hourly_pattern: Dict[int, float],
        recommendations: List[str],
    ):
        """Initialize usage report"""
        self.summary = summary
        self.top_users = top_users
        self.top_models = top_models
        self.daily_breakdown = daily_breakdown
        self.hourly_pattern = hourly_pattern
        self.recommendations = recommendations
    
    def to_dict(self) -> Dict:
        """Convert report to dictionary"""
        return {
            "summary": self.summary.dict(),
            "top_users": self.top_users,
            "top_models": self.top_models,
            "daily_breakdown": self.daily_breakdown,
            "hourly_pattern": self.hourly_pattern,
            "recommendations": self.recommendations,
        }
    
    def to_json(self) -> str:
        """Convert report to JSON"""
        return json.dumps(self.to_dict(), indent=2, default=str)


class CostAnalytics:
    """
    Advanced analytics for cost data.
    """
    
    def __init__(self, tracker: CostTracker):
        """
        Initialize cost analytics.
        
        Args:
            tracker: CostTracker instance
        """
        self.tracker = tracker
    
    def generate_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
    ) -> UsageReport:
        """
        Generate comprehensive usage report.
        
        Args:
            start_time: Start of time period
            end_time: End of time period
            user_id: Filter by user
        
        Returns:
            UsageReport with detailed analytics
        """
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(days=30)
        if end_time is None:
            end_time = datetime.utcnow()
        
        # Get summary
        summary = self.tracker.get_usage_summary(
            start_time=start_time,
            end_time=end_time,
            user_id=user_id,
        )
        
        # Get detailed records
        records = self.tracker.get_recent_requests(limit=10000, user_id=user_id)
        records = [r for r in records if start_time <= r.usage.timestamp <= end_time]
        
        # Analyze top users
        top_users = self._analyze_top_users(records)
        
        # Analyze top models
        top_models = self._analyze_top_models(records)
        
        # Daily breakdown
        daily_breakdown = self._analyze_daily_breakdown(records)
        
        # Hourly pattern
        hourly_pattern = self._analyze_hourly_pattern(records)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(summary, records)
        
        return UsageReport(
            summary=summary,
            top_users=top_users,
            top_models=top_models,
            daily_breakdown=daily_breakdown,
            hourly_pattern=hourly_pattern,
            recommendations=recommendations,
        )
    
    def _analyze_top_users(
        self,
        records: List[CostRecord],
        limit: int = 10,
    ) -> List[Dict]:
        """Analyze top users by cost"""
        user_costs = {}
        user_requests = {}
        
        for record in records:
            if not record.usage.user_id:
                continue
            
            user_id = record.usage.user_id
            user_costs[user_id] = user_costs.get(user_id, 0) + record.total_cost
            user_requests[user_id] = user_requests.get(user_id, 0) + 1
        
        # Sort by cost
        sorted_users = sorted(
            user_costs.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {
                "user_id": user_id,
                "total_cost": round(cost, 6),
                "request_count": user_requests.get(user_id, 0),
                "avg_cost_per_request": round(cost / user_requests.get(user_id, 1), 6),
            }
            for user_id, cost in sorted_users
        ]
    
    def _analyze_top_models(
        self,
        records: List[CostRecord],
    ) -> List[Dict]:
        """Analyze usage by model"""
        model_stats = {}
        
        for record in records:
            model = record.usage.model
            if model not in model_stats:
                model_stats[model] = {
                    "model": model.value,
                    "request_count": 0,
                    "total_cost": 0,
                    "total_tokens": 0,
                }
            
            stats = model_stats[model]
            stats["request_count"] += 1
            stats["total_cost"] += record.total_cost
            stats["total_tokens"] += record.usage.total_tokens
        
        # Calculate averages and sort
        result = []
        for model, stats in model_stats.items():
            stats["avg_cost_per_request"] = round(
                stats["total_cost"] / stats["request_count"], 6
            )
            stats["avg_tokens_per_request"] = round(
                stats["total_tokens"] / stats["request_count"], 2
            )
            stats["total_cost"] = round(stats["total_cost"], 6)
            result.append(stats)
        
        result.sort(key=lambda x: x["total_cost"], reverse=True)
        return result
    
    def _analyze_daily_breakdown(
        self,
        records: List[CostRecord],
    ) -> Dict[str, float]:
        """Analyze costs by day"""
        daily_costs = {}
        
        for record in records:
            date = record.usage.timestamp.date().isoformat()
            daily_costs[date] = daily_costs.get(date, 0) + record.total_cost
        
        return {date: round(cost, 6) for date, cost in sorted(daily_costs.items())}
    
    def _analyze_hourly_pattern(
        self,
        records: List[CostRecord],
    ) -> Dict[int, float]:
        """Analyze costs by hour of day"""
        hourly_costs = {hour: 0 for hour in range(24)}
        hourly_counts = {hour: 0 for hour in range(24)}
        
        for record in records:
            hour = record.usage.timestamp.hour
            hourly_costs[hour] += record.total_cost
            hourly_counts[hour] += 1
        
        # Calculate average cost per hour
        return {
            hour: round(hourly_costs[hour] / max(hourly_counts[hour], 1), 6)
            for hour in range(24)
        }
    
    def _generate_recommendations(
        self,
        summary: UsageSummary,
        records: List[CostRecord],
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Check if costs are high
        if summary.total_cost > 100:
            recommendations.append(
                f"High usage detected (${summary.total_cost:.2f}). Consider implementing cost optimization strategies."
            )
        
        # Check for expensive models
        if ModelType.GEMINI_15_PRO in summary.cost_by_model:
            pro_cost = summary.cost_by_model[ModelType.GEMINI_15_PRO]
            if pro_cost > summary.total_cost * 0.5:
                recommendations.append(
                    f"Gemini 1.5 Pro accounts for {(pro_cost/summary.total_cost*100):.1f}% of costs. "
                    "Consider using Gemini 1.5 Flash for non-critical operations."
                )
        
        # Check average tokens
        if summary.avg_tokens_per_request > 3000:
            recommendations.append(
                f"Average {summary.avg_tokens_per_request:.0f} tokens per request is high. "
                "Consider optimizing prompts and context management."
            )
        
        # Check for caching opportunities
        if summary.total_requests > 1000:
            recommendations.append(
                "High request volume detected. Implementing response caching could significantly reduce costs."
            )
        
        # Check cost per request
        if summary.avg_cost_per_request > 0.01:
            recommendations.append(
                f"Average cost per request (${summary.avg_cost_per_request:.4f}) is high. "
                "Review prompt efficiency and model selection."
            )
        
        return recommendations
    
    def get_cost_trends(
        self,
        days: int = 30,
    ) -> Dict:
        """
        Analyze cost trends over time.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Dictionary with trend analysis
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Get daily costs
        records = self.tracker.get_recent_requests(limit=100000)
        records = [r for r in records if start_time <= r.usage.timestamp <= end_time]
        
        daily_costs = {}
        for record in records:
            date = record.usage.timestamp.date()
            daily_costs[date] = daily_costs.get(date, 0) + record.total_cost
        
        if not daily_costs:
            return {
                "trend": "insufficient_data",
                "daily_avg": 0,
                "weekly_avg": 0,
                "monthly_projection": 0,
            }
        
        # Calculate averages
        daily_avg = sum(daily_costs.values()) / len(daily_costs)
        weekly_avg = daily_avg * 7
        monthly_projection = daily_avg * 30
        
        # Determine trend
        sorted_dates = sorted(daily_costs.keys())
        if len(sorted_dates) < 7:
            trend = "insufficient_data"
        else:
            recent_avg = sum(daily_costs[d] for d in sorted_dates[-7:]) / 7
            older_avg = sum(daily_costs[d] for d in sorted_dates[:7]) / 7
            
            if recent_avg > older_avg * 1.2:
                trend = "increasing"
            elif recent_avg < older_avg * 0.8:
                trend = "decreasing"
            else:
                trend = "stable"
        
        return {
            "trend": trend,
            "daily_avg": round(daily_avg, 6),
            "weekly_avg": round(weekly_avg, 6),
            "monthly_projection": round(monthly_projection, 2),
            "total_days": len(daily_costs),
            "daily_breakdown": {
                date.isoformat(): round(cost, 6)
                for date, cost in sorted(daily_costs.items())
            },
        }
    
    def compare_periods(
        self,
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime,
    ) -> Dict:
        """
        Compare costs between two time periods.
        
        Args:
            period1_start: Start of first period
            period1_end: End of first period
            period2_start: Start of second period
            period2_end: End of second period
        
        Returns:
            Dictionary with comparison metrics
        """
        summary1 = self.tracker.get_usage_summary(period1_start, period1_end)
        summary2 = self.tracker.get_usage_summary(period2_start, period2_end)
        
        cost_change = summary2.total_cost - summary1.total_cost
        cost_change_pct = (
            (cost_change / summary1.total_cost * 100)
            if summary1.total_cost > 0
            else 0
        )
        
        requests_change = summary2.total_requests - summary1.total_requests
        requests_change_pct = (
            (requests_change / summary1.total_requests * 100)
            if summary1.total_requests > 0
            else 0
        )
        
        return {
            "period1": {
                "start": period1_start.isoformat(),
                "end": period1_end.isoformat(),
                "total_cost": summary1.total_cost,
                "total_requests": summary1.total_requests,
                "avg_cost_per_request": summary1.avg_cost_per_request,
            },
            "period2": {
                "start": period2_start.isoformat(),
                "end": period2_end.isoformat(),
                "total_cost": summary2.total_cost,
                "total_requests": summary2.total_requests,
                "avg_cost_per_request": summary2.avg_cost_per_request,
            },
            "changes": {
                "cost_change": round(cost_change, 6),
                "cost_change_percentage": round(cost_change_pct, 2),
                "requests_change": requests_change,
                "requests_change_percentage": round(requests_change_pct, 2),
            },
        }
    
    def export_report(
        self,
        report: UsageReport,
        format: str = "json",
        filepath: Optional[str] = None,
    ) -> str:
        """
        Export report to file.
        
        Args:
            report: UsageReport to export
            format: Export format (json, csv)
            filepath: Output file path
        
        Returns:
            Exported content as string
        """
        if format == "json":
            content = report.to_json()
        elif format == "csv":
            # Implement CSV export
            content = self._export_to_csv(report)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        if filepath:
            with open(filepath, 'w') as f:
                f.write(content)
        
        return content
    
    def _export_to_csv(self, report: UsageReport) -> str:
        """Export report to CSV format"""
        import csv
        import io
        
        output = io.StringIO()
        
        # Summary section
        writer = csv.writer(output)
        writer.writerow(["Cost Analysis Report"])
        writer.writerow(["Generated", datetime.utcnow().isoformat()])
        writer.writerow([])
        
        writer.writerow(["Summary"])
        writer.writerow(["Total Requests", report.summary.total_requests])
        writer.writerow(["Total Cost", f"${report.summary.total_cost:.6f}"])
        writer.writerow(["Avg Cost/Request", f"${report.summary.avg_cost_per_request:.6f}"])
        writer.writerow([])
        
        # Top users
        writer.writerow(["Top Users"])
        writer.writerow(["User ID", "Total Cost", "Requests", "Avg Cost/Request"])
        for user in report.top_users:
            writer.writerow([
                user["user_id"],
                f"${user['total_cost']:.6f}",
                user["request_count"],
                f"${user['avg_cost_per_request']:.6f}",
            ])
        writer.writerow([])
        
        # Daily breakdown
        writer.writerow(["Daily Breakdown"])
        writer.writerow(["Date", "Cost"])
        for date, cost in report.daily_breakdown.items():
            writer.writerow([date, f"${cost:.6f}"])
        
        return output.getvalue()
