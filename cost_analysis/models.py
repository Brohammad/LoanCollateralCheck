"""
Data models for cost analysis and tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class ModelType(str, Enum):
    """LLM model types with their pricing."""
    
    GEMINI_FLASH = "gemini-2.0-flash-exp"
    GEMINI_PRO = "gemini-1.5-pro"
    GEMINI_ULTRA = "gemini-ultra"
    EMBEDDING = "text-embedding-004"


class OperationType(str, Enum):
    """Types of LLM operations."""
    
    GENERATION = "generation"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"
    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"


class CostCategory(str, Enum):
    """Cost categories for analysis."""
    
    LLM_GENERATION = "llm_generation"
    LLM_EMBEDDING = "llm_embedding"
    VECTOR_SEARCH = "vector_search"
    CACHING = "caching"
    STORAGE = "storage"
    COMPUTE = "compute"


class BudgetPeriod(str, Enum):
    """Budget tracking periods."""
    
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class TokenUsage(BaseModel):
    """Token usage information for a single operation."""
    
    operation_id: str = Field(..., description="Unique operation identifier")
    model_type: ModelType = Field(..., description="Model used")
    operation_type: OperationType = Field(..., description="Type of operation")
    
    prompt_tokens: int = Field(0, ge=0, description="Input tokens")
    completion_tokens: int = Field(0, ge=0, description="Output tokens")
    total_tokens: int = Field(0, ge=0, description="Total tokens")
    
    cached_tokens: int = Field(0, ge=0, description="Tokens from cache")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: float = Field(0.0, ge=0, description="Operation duration in ms")
    
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    api_key_id: Optional[str] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("total_tokens", always=True)
    def calculate_total_tokens(cls, v, values):
        """Calculate total tokens if not provided."""
        if v == 0:
            return values.get("prompt_tokens", 0) + values.get("completion_tokens", 0)
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "operation_id": "op_123",
                "model_type": "gemini-2.0-flash-exp",
                "operation_type": "generation",
                "prompt_tokens": 150,
                "completion_tokens": 350,
                "total_tokens": 500,
                "cached_tokens": 0,
                "duration_ms": 1250.5,
                "user_id": "user_456",
                "session_id": "session_789"
            }
        }


class CostRecord(BaseModel):
    """Cost record for a single operation."""
    
    record_id: str = Field(..., description="Unique record identifier")
    token_usage: TokenUsage = Field(..., description="Associated token usage")
    
    category: CostCategory = Field(..., description="Cost category")
    
    prompt_cost: float = Field(0.0, ge=0, description="Cost for input tokens")
    completion_cost: float = Field(0.0, ge=0, description="Cost for output tokens")
    total_cost: float = Field(0.0, ge=0, description="Total cost")
    
    cached_cost_savings: float = Field(0.0, ge=0, description="Savings from caching")
    
    currency: str = Field("USD", description="Currency code")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    tags: Dict[str, str] = Field(default_factory=dict, description="Custom tags")
    
    @validator("total_cost", always=True)
    def calculate_total_cost(cls, v, values):
        """Calculate total cost if not provided."""
        if v == 0.0:
            return values.get("prompt_cost", 0.0) + values.get("completion_cost", 0.0)
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "record_id": "rec_123",
                "category": "llm_generation",
                "prompt_cost": 0.00015,
                "completion_cost": 0.00035,
                "total_cost": 0.0005,
                "cached_cost_savings": 0.0,
                "currency": "USD",
                "tags": {"feature": "chat", "priority": "high"}
            }
        }


class BudgetAlert(BaseModel):
    """Budget alert when thresholds are exceeded."""
    
    alert_id: str = Field(..., description="Unique alert identifier")
    
    budget_name: str = Field(..., description="Budget name")
    period: BudgetPeriod = Field(..., description="Budget period")
    
    budget_limit: float = Field(..., ge=0, description="Budget limit")
    current_spend: float = Field(..., ge=0, description="Current spend")
    threshold_percent: float = Field(..., ge=0, le=100, description="Alert threshold %")
    
    exceeded_at: datetime = Field(default_factory=datetime.utcnow)
    
    severity: str = Field("warning", description="Alert severity: info/warning/critical")
    
    affected_users: list[str] = Field(default_factory=list)
    affected_features: list[str] = Field(default_factory=list)
    
    message: str = Field(..., description="Alert message")
    
    acknowledged: bool = Field(False, description="Whether alert was acknowledged")
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    @property
    def percent_used(self) -> float:
        """Calculate percentage of budget used."""
        if self.budget_limit == 0:
            return 0.0
        return (self.current_spend / self.budget_limit) * 100
    
    @property
    def remaining_budget(self) -> float:
        """Calculate remaining budget."""
        return max(0.0, self.budget_limit - self.current_spend)
    
    class Config:
        json_schema_extra = {
            "example": {
                "alert_id": "alert_123",
                "budget_name": "monthly_llm_budget",
                "period": "monthly",
                "budget_limit": 100.0,
                "current_spend": 85.50,
                "threshold_percent": 80.0,
                "severity": "warning",
                "message": "Budget 85.5% consumed (threshold: 80%)",
                "acknowledged": False
            }
        }


class OptimizationSuggestion(BaseModel):
    """Suggestion for cost optimization."""
    
    suggestion_id: str = Field(..., description="Unique suggestion identifier")
    
    category: str = Field(..., description="Optimization category")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed description")
    
    potential_savings: float = Field(0.0, ge=0, description="Estimated savings (USD/month)")
    potential_savings_percent: float = Field(0.0, ge=0, description="Estimated savings %")
    
    implementation_effort: str = Field(..., description="Effort: low/medium/high")
    priority: str = Field(..., description="Priority: low/medium/high/critical")
    
    current_cost: float = Field(0.0, ge=0, description="Current monthly cost")
    optimized_cost: float = Field(0.0, ge=0, description="Projected optimized cost")
    
    affected_operations: list[str] = Field(default_factory=list)
    
    action_items: list[str] = Field(default_factory=list, description="Steps to implement")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    implemented: bool = Field(False, description="Whether suggestion was implemented")
    implemented_at: Optional[datetime] = None
    
    actual_savings: Optional[float] = Field(None, description="Actual savings after implementation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "suggestion_id": "sug_123",
                "category": "caching",
                "title": "Implement prompt caching for repeated queries",
                "description": "30% of queries are repeated within 1 hour. Implement caching to reduce LLM calls.",
                "potential_savings": 45.0,
                "potential_savings_percent": 15.0,
                "implementation_effort": "medium",
                "priority": "high",
                "current_cost": 300.0,
                "optimized_cost": 255.0,
                "action_items": [
                    "Implement Redis-based prompt cache",
                    "Set TTL to 1 hour for repeated queries",
                    "Monitor cache hit rate"
                ],
                "implemented": False
            }
        }


class CostBreakdown(BaseModel):
    """Detailed cost breakdown."""
    
    period_start: datetime
    period_end: datetime
    
    total_cost: float = Field(0.0, ge=0)
    
    by_category: Dict[str, float] = Field(default_factory=dict)
    by_model: Dict[str, float] = Field(default_factory=dict)
    by_operation: Dict[str, float] = Field(default_factory=dict)
    by_user: Dict[str, float] = Field(default_factory=dict)
    by_feature: Dict[str, float] = Field(default_factory=dict)
    
    total_tokens: int = Field(0, ge=0)
    total_requests: int = Field(0, ge=0)
    
    avg_cost_per_request: float = Field(0.0, ge=0)
    avg_tokens_per_request: float = Field(0.0, ge=0)
    
    cache_hit_rate: float = Field(0.0, ge=0, le=1)
    cost_savings_from_cache: float = Field(0.0, ge=0)


class CostTrend(BaseModel):
    """Cost trend analysis."""
    
    period: BudgetPeriod
    data_points: list[tuple[datetime, float]] = Field(default_factory=list)
    
    trend_direction: str = Field(..., description="increasing/decreasing/stable")
    trend_percent: float = Field(0.0, description="Trend change percentage")
    
    forecast_next_period: float = Field(0.0, ge=0)
    confidence_interval: tuple[float, float] = Field((0.0, 0.0))
    
    anomalies: list[datetime] = Field(default_factory=list, description="Detected anomalies")
