"""
Cost Analysis Integration Example
Demonstrates how to integrate cost tracking with the existing AI Agent System
"""

from fastapi import FastAPI, HTTPException, Depends
from datetime import datetime, timedelta
import logging

# Cost Analysis imports
from cost_analysis.tracker import CostTracker
from cost_analysis.budget import BudgetManager
from cost_analysis.middleware import cost_tracking_middleware
from cost_analysis.api import router as cost_router
from cost_analysis.models import ModelType, RequestType, BudgetPeriod

# Existing system imports (from previous parts)
# from app.gemini_client import GeminiClient
# from security.auth import get_current_user
# from monitoring.metrics import MetricsCollector

# Initialize FastAPI
app = FastAPI(
    title="AI Agent System with Cost Tracking",
    description="Production-ready AI Agent System with comprehensive cost management",
    version="1.0.0",
)

# Initialize cost tracking components
cost_tracker = CostTracker(db_path="data/costs.db")
budget_manager = BudgetManager(db_path="data/budgets.db")

# Add cost tracking middleware (automatic tracking for all requests)
app.add_middleware(
    cost_tracking_middleware(
        tracker=cost_tracker,
        enabled=True,
        add_headers=True,
    )
)

# Include cost analysis API routes
app.include_router(cost_router)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Example 1: Integrate with Gemini Client
class EnhancedGeminiClient:
    """Gemini client with automatic cost tracking"""
    
    def __init__(self, api_key: str):
        # self.client = genai.GenerativeModel(...)
        self.tracker = cost_tracker
        
    async def generate_content(
        self,
        prompt: str,
        model: ModelType = ModelType.GEMINI_15_PRO,
        user_id: str = None,
        session_id: str = None,
    ):
        """
        Generate content with automatic cost tracking
        """
        # Make API call
        # response = await self.client.generate_content_async(prompt)
        
        # Simulate response
        class MockResponse:
            class Usage:
                prompt_tokens = 1000
                completion_tokens = 500
            usage = Usage()
            text = "Generated response"
        
        response = MockResponse()
        
        # Track usage
        record = self.tracker.track_usage(
            model=model,
            request_type=RequestType.GENERATION,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            user_id=user_id,
            session_id=session_id,
            agent_name="gemini_client",
            metadata={
                "prompt_length": len(prompt),
                "model": model.value,
            },
        )
        
        logger.info(
            f"Generated content - Cost: ${record.total_cost:.6f}, "
            f"Tokens: {record.usage.total_tokens}, "
            f"User: {user_id}"
        )
        
        return response.text


# Example 2: Budget enforcement middleware
async def check_user_budget(user_id: str):
    """Check if user has exceeded their budget"""
    # Get user's daily budget
    budgets = budget_manager.list_budgets(user_id=user_id, period=BudgetPeriod.DAILY)
    
    if not budgets:
        # No budget set, allow request
        return True
    
    budget = budgets[0]
    
    # Update budget with current usage
    updated = budget_manager.update_budget_usage(budget.id, cost_tracker)
    
    # Check if budget exceeded
    if updated.percentage_used >= 100:
        # Get alerts
        alerts = budget_manager.get_alerts(
            budget_id=budget.id,
            acknowledged=False,
        )
        
        raise HTTPException(
            status_code=429,
            detail=f"Budget exceeded. Used: ${updated.current:.2f} / ${updated.limit:.2f}",
        )
    
    # Check if approaching limit
    if updated.percentage_used >= updated.critical_threshold * 100:
        logger.warning(
            f"User {user_id} approaching budget limit: "
            f"{updated.percentage_used:.1f}% used"
        )
    
    return True


# Example 3: API endpoint with cost tracking
@app.post("/api/v1/generate")
async def generate_content(
    prompt: str,
    model: str = "gemini-1.5-pro",
    # user: dict = Depends(get_current_user),  # From security module
):
    """
    Generate content with automatic cost tracking and budget enforcement
    """
    user_id = "user123"  # user.get("id")
    
    # Check budget before processing
    await check_user_budget(user_id)
    
    # Map string to ModelType
    model_type = {
        "gemini-2.0-flash": ModelType.GEMINI_2_FLASH,
        "gemini-1.5-pro": ModelType.GEMINI_15_PRO,
        "gemini-1.5-flash": ModelType.GEMINI_15_FLASH,
    }.get(model, ModelType.GEMINI_15_PRO)
    
    # Generate content (cost is automatically tracked by middleware)
    client = EnhancedGeminiClient(api_key="dummy")
    response = await client.generate_content(
        prompt=prompt,
        model=model_type,
        user_id=user_id,
    )
    
    # Get user's current cost
    summary = cost_tracker.get_usage_summary(
        start_time=datetime.utcnow() - timedelta(hours=24),
        end_time=datetime.utcnow(),
        user_id=user_id,
    )
    
    return {
        "response": response,
        "cost_info": {
            "today_cost": summary.total_cost,
            "today_requests": summary.total_requests,
            "today_tokens": summary.total_tokens,
        },
    }


# Example 4: Setup user budgets
@app.on_event("startup")
async def setup_budgets():
    """Create default budgets on startup"""
    
    # System-wide daily budget
    try:
        budget_manager.create_budget(
            name="System Daily Budget",
            period=BudgetPeriod.DAILY,
            limit=100.0,
            warning_threshold=0.8,
            critical_threshold=0.95,
        )
        logger.info("Created system daily budget")
    except Exception as e:
        logger.warning(f"System budget already exists: {e}")
    
    # Default user budget template
    default_user_limit = 10.0
    logger.info(f"Default per-user daily limit: ${default_user_limit}")


# Example 5: Cost monitoring endpoint
@app.get("/api/v1/monitoring/costs")
async def get_cost_monitoring():
    """
    Get current cost monitoring status
    Integrates with monitoring system from PART 1
    """
    now = datetime.utcnow()
    
    # Get metrics for different time periods
    last_hour = cost_tracker.get_usage_summary(
        start_time=now - timedelta(hours=1),
        end_time=now,
    )
    
    last_24h = cost_tracker.get_usage_summary(
        start_time=now - timedelta(hours=24),
        end_time=now,
    )
    
    last_30d = cost_tracker.get_usage_summary(
        start_time=now - timedelta(days=30),
        end_time=now,
    )
    
    # Get active budgets
    budgets = budget_manager.list_budgets()
    
    # Get recent alerts
    alerts = budget_manager.get_alerts(
        acknowledged=False,
        limit=10,
    )
    
    return {
        "timestamp": now.isoformat(),
        "metrics": {
            "last_hour": {
                "requests": last_hour.total_requests,
                "cost": last_hour.total_cost,
                "tokens": last_hour.total_tokens,
            },
            "last_24h": {
                "requests": last_24h.total_requests,
                "cost": last_24h.total_cost,
                "tokens": last_24h.total_tokens,
            },
            "last_30d": {
                "requests": last_30d.total_requests,
                "cost": last_30d.total_cost,
                "tokens": last_30d.total_tokens,
            },
        },
        "budgets": {
            "active_count": len(budgets),
            "total_limit": sum(b.limit for b in budgets),
            "total_used": sum(b.current for b in budgets),
        },
        "alerts": {
            "unacknowledged_count": len(alerts),
            "alerts": [
                {
                    "level": a.level,
                    "message": a.message,
                    "budget": a.budget_name,
                }
                for a in alerts
            ],
        },
    }


# Example 6: Cost optimization endpoint
@app.get("/api/v1/monitoring/optimization")
async def get_optimization_suggestions():
    """
    Get cost optimization suggestions
    """
    from cost_analysis.optimizer import CostOptimizer
    from cost_analysis.analytics import CostAnalytics
    
    optimizer = CostOptimizer()
    analytics = CostAnalytics(cost_tracker)
    
    # Get recent usage
    records = cost_tracker.get_recent_requests(limit=1000)
    
    # Get recommendations
    recommendations = optimizer.analyze_and_recommend(records)
    
    # Get cost trends
    trends = analytics.get_cost_trends(days=30)
    
    return {
        "recommendations": [
            {
                "type": rec.optimization_type,
                "priority": rec.priority,
                "savings": rec.estimated_savings,
                "description": rec.description,
                "effort": rec.implementation_effort,
                "steps": rec.implementation_steps,
            }
            for rec in recommendations[:5]  # Top 5
        ],
        "trends": trends,
        "potential_savings": sum(r.estimated_savings for r in recommendations),
    }


# Example 7: User cost dashboard endpoint
@app.get("/api/v1/users/{user_id}/dashboard")
async def get_user_dashboard(user_id: str):
    """
    Get user's cost dashboard
    """
    now = datetime.utcnow()
    
    # Get user's usage
    summary = cost_tracker.get_usage_summary(
        start_time=now - timedelta(days=30),
        end_time=now,
        user_id=user_id,
    )
    
    # Get user's budgets
    budgets = budget_manager.list_budgets(user_id=user_id)
    
    # Get recent requests
    recent = cost_tracker.get_recent_requests(
        limit=10,
        user_id=user_id,
    )
    
    return {
        "user_id": user_id,
        "period": "last_30_days",
        "summary": {
            "total_requests": summary.total_requests,
            "total_cost": summary.total_cost,
            "total_tokens": summary.total_tokens,
            "by_model": summary.by_model,
            "by_request_type": summary.by_request_type,
        },
        "budgets": [
            {
                "name": b.name,
                "limit": b.limit,
                "current": b.current,
                "percentage": b.percentage_used,
                "period": b.period,
            }
            for b in budgets
        ],
        "recent_requests": [
            {
                "timestamp": r.usage.timestamp.isoformat(),
                "model": r.usage.model.value,
                "tokens": r.usage.total_tokens,
                "cost": r.total_cost,
            }
            for r in recent
        ],
    }


# Example 8: Administrative endpoints
@app.post("/api/v1/admin/budgets/user/{user_id}")
async def create_user_budget(
    user_id: str,
    limit: float,
    period: str = "daily",
):
    """
    Create budget for a specific user (admin only)
    """
    period_map = {
        "daily": BudgetPeriod.DAILY,
        "weekly": BudgetPeriod.WEEKLY,
        "monthly": BudgetPeriod.MONTHLY,
        "yearly": BudgetPeriod.YEARLY,
    }
    
    budget = budget_manager.create_budget(
        name=f"{user_id} {period.title()} Budget",
        period=period_map[period],
        limit=limit,
        user_id=user_id,
    )
    
    logger.info(f"Created {period} budget for {user_id}: ${limit}")
    
    return {
        "budget_id": budget.id,
        "user_id": user_id,
        "limit": limit,
        "period": period,
    }


@app.post("/api/v1/admin/cleanup")
async def cleanup_old_data(days: int = 90):
    """
    Cleanup old cost records (admin only)
    """
    deleted = cost_tracker.cleanup_old_records(days=days)
    
    logger.info(f"Cleaned up {deleted} records older than {days} days")
    
    return {
        "deleted": deleted,
        "cutoff_days": days,
    }


# Example 9: Health check with cost info
@app.get("/health")
async def health_check():
    """
    Health check endpoint including cost tracking status
    """
    try:
        # Check cost tracker
        summary = cost_tracker.get_usage_summary(
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
        )
        
        # Check budget manager
        budgets = budget_manager.list_budgets()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "cost_tracker": {
                    "status": "healthy",
                    "recent_requests": summary.total_requests,
                },
                "budget_manager": {
                    "status": "healthy",
                    "active_budgets": len(budgets),
                },
            },
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
