"""
FastAPI endpoints for cost analysis
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from cost_analysis.tracker import CostTracker
from cost_analysis.calculator import CostCalculator
from cost_analysis.budget import BudgetManager
from cost_analysis.optimizer import CostOptimizer
from cost_analysis.analytics import CostAnalytics
from cost_analysis.models import (
    ModelType,
    BudgetPeriod,
    AlertLevel,
    UsageSummary,
    Budget,
    BudgetAlert,
    OptimizationRecommendation,
)

router = APIRouter(prefix="/api/v1/cost", tags=["cost-analysis"])

# Initialize components
cost_tracker = CostTracker()
cost_calculator = CostCalculator()
budget_manager = BudgetManager()
cost_optimizer = CostOptimizer()
cost_analytics = CostAnalytics(cost_tracker)


# Request/Response Models
class CostEstimateRequest(BaseModel):
    """Request for cost estimate"""
    model: ModelType
    input_tokens: int = Field(gt=0)
    output_tokens: int = Field(gt=0)


class CostEstimateResponse(BaseModel):
    """Response with cost estimate"""
    model: ModelType
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    input_price_per_1k: float
    output_price_per_1k: float


class CreateBudgetRequest(BaseModel):
    """Request to create budget"""
    name: str
    period: BudgetPeriod
    limit: float = Field(gt=0)
    user_id: Optional[str] = None
    model: Optional[ModelType] = None
    warning_threshold: float = Field(default=0.8, ge=0, le=1)
    critical_threshold: float = Field(default=0.95, ge=0, le=1)


# Endpoints

@router.get("/summary")
async def get_cost_summary(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    model: Optional[ModelType] = Query(None, description="Filter by model"),
) -> UsageSummary:
    """
    Get cost summary for a time period.
    
    Returns aggregated usage statistics including:
    - Total costs and token counts
    - Breakdown by model and request type
    - Average costs per request
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    summary = cost_tracker.get_usage_summary(
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        model=model,
    )
    
    return summary


@router.post("/estimate", response_model=CostEstimateResponse)
async def estimate_cost(request: CostEstimateRequest):
    """
    Estimate cost for a request.
    
    Calculates the cost based on token counts and current pricing.
    """
    from cost_analysis.pricing import calculate_cost
    
    cost_data = calculate_cost(
        model=request.model,
        input_tokens=request.input_tokens,
        output_tokens=request.output_tokens,
    )
    
    return CostEstimateResponse(
        model=request.model,
        input_tokens=request.input_tokens,
        output_tokens=request.output_tokens,
        total_tokens=request.input_tokens + request.output_tokens,
        **cost_data,
    )


@router.get("/trends")
async def get_cost_trends(
    days: int = Query(default=30, ge=7, le=365),
):
    """
    Get cost trends over time.
    
    Returns:
    - Daily average costs
    - Cost trend (increasing/decreasing/stable)
    - Monthly projection
    """
    trends = cost_analytics.get_cost_trends(days=days)
    return trends


@router.get("/report")
async def get_usage_report(
    days: int = Query(default=30, ge=1, le=365),
    user_id: Optional[str] = Query(None),
):
    """
    Generate comprehensive usage report.
    
    Includes:
    - Summary statistics
    - Top users by cost
    - Top models by usage
    - Daily and hourly breakdowns
    - Recommendations
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    report = cost_analytics.generate_report(
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
    )
    
    return report.to_dict()


@router.get("/compare")
async def compare_periods(
    period1_days: int = Query(..., ge=1, le=365, description="Days in first period"),
    period2_days: int = Query(..., ge=1, le=365, description="Days in second period"),
):
    """
    Compare costs between two time periods.
    
    Returns comparison metrics showing changes in costs and usage.
    """
    end_time = datetime.utcnow()
    
    period2_start = end_time - timedelta(days=period2_days)
    period2_end = end_time
    
    period1_end = period2_start
    period1_start = period1_end - timedelta(days=period1_days)
    
    comparison = cost_analytics.compare_periods(
        period1_start=period1_start,
        period1_end=period1_end,
        period2_start=period2_start,
        period2_end=period2_end,
    )
    
    return comparison


@router.get("/budgets", response_model=List[Budget])
async def list_budgets(
    user_id: Optional[str] = Query(None),
    period: Optional[BudgetPeriod] = Query(None),
):
    """List all budgets with optional filters."""
    budgets = budget_manager.list_budgets(user_id=user_id, period=period)
    return budgets


@router.post("/budgets", response_model=Budget)
async def create_budget(request: CreateBudgetRequest):
    """Create a new budget."""
    budget = budget_manager.create_budget(
        name=request.name,
        period=request.period,
        limit=request.limit,
        user_id=request.user_id,
        model=request.model,
        warning_threshold=request.warning_threshold,
        critical_threshold=request.critical_threshold,
    )
    return budget


@router.get("/budgets/{budget_id}", response_model=Budget)
async def get_budget(budget_id: str):
    """Get budget by ID."""
    budget = budget_manager.get_budget(budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.post("/budgets/{budget_id}/update")
async def update_budget_usage(budget_id: str):
    """Update budget usage from cost tracker."""
    try:
        budget = budget_manager.update_budget_usage(budget_id, cost_tracker)
        return budget
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/budgets/{budget_id}")
async def delete_budget(budget_id: str):
    """Delete a budget."""
    budget_manager.delete_budget(budget_id)
    return {"message": "Budget deleted successfully"}


@router.get("/budgets/{budget_id}/alerts", response_model=List[BudgetAlert])
async def get_budget_alerts(
    budget_id: str,
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get alerts for a budget."""
    alerts = budget_manager.get_alerts(
        budget_id=budget_id,
        acknowledged=acknowledged,
        limit=limit,
    )
    return alerts


@router.post("/budgets/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    acknowledged_by: str = Query(..., description="User acknowledging the alert"),
):
    """Acknowledge a budget alert."""
    try:
        alert = budget_manager.acknowledge_alert(alert_id, acknowledged_by)
        return alert
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/alerts", response_model=List[BudgetAlert])
async def get_all_alerts(
    level: Optional[AlertLevel] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get all budget alerts."""
    alerts = budget_manager.get_alerts(
        level=level,
        acknowledged=acknowledged,
        limit=limit,
    )
    return alerts


@router.get("/optimize", response_model=List[OptimizationRecommendation])
async def get_optimization_recommendations(
    days: int = Query(default=30, ge=7, le=90),
):
    """
    Get cost optimization recommendations.
    
    Analyzes usage patterns and suggests ways to reduce costs.
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # Get recent usage records
    records = cost_tracker.get_recent_requests(limit=10000)
    records = [r for r in records if start_time <= r.usage.timestamp <= end_time]
    
    if not records:
        return []
    
    recommendations = cost_optimizer.analyze_and_recommend(records)
    return recommendations


@router.get("/breakdown")
async def get_cost_breakdown(
    days: int = Query(default=30, ge=1, le=365),
    user_id: Optional[str] = Query(None),
):
    """
    Get detailed cost breakdown by various dimensions.
    
    Returns costs grouped by:
    - Model
    - Request type
    - Agent
    - User
    - Date
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    records = cost_tracker.get_recent_requests(limit=10000, user_id=user_id)
    records = [r for r in records if start_time <= r.usage.timestamp <= end_time]
    
    breakdown = cost_calculator.calculate_cost_breakdown(records)
    return breakdown


@router.get("/users/{user_id}/costs")
async def get_user_costs(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365),
):
    """Get cost summary for a specific user."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    summary = cost_tracker.get_usage_summary(
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
    )
    
    return summary


@router.get("/models/compare")
async def compare_model_costs(
    input_tokens: int = Query(..., gt=0),
    output_tokens: int = Query(..., gt=0),
):
    """
    Compare costs across different models for a given token count.
    
    Helps in choosing the most cost-effective model.
    """
    comparison = cost_calculator.pricing_model.compare_model_costs(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    
    # Convert enum keys to strings for JSON serialization
    return {model.value: costs for model, costs in comparison.items()}


@router.post("/cleanup")
async def cleanup_old_records(
    days: int = Query(default=90, ge=30, le=365, description="Delete records older than this many days"),
):
    """
    Clean up old cost records.
    
    Deletes records older than specified number of days to save storage.
    """
    deleted = cost_tracker.cleanup_old_records(days=days)
    return {
        "message": f"Deleted {deleted} old records",
        "deleted_count": deleted,
        "cutoff_days": days,
    }


@router.get("/health")
async def health_check():
    """Health check endpoint for cost analysis service."""
    try:
        # Try to get recent summary
        summary = cost_tracker.get_usage_summary(
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
        )
        
        return {
            "status": "healthy",
            "recent_requests": summary.total_requests,
            "recent_cost": summary.total_cost,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
