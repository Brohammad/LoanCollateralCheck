"""
Data models for cost analysis
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class ModelType(str, Enum):
    """LLM model types"""
    GEMINI_2_FLASH = "gemini-2.0-flash-exp"
    GEMINI_15_PRO = "gemini-1.5-pro"
    GEMINI_15_FLASH = "gemini-1.5-flash"
    TEXT_EMBEDDING = "text-embedding-004"
    
    
class RequestType(str, Enum):
    """Type of API request"""
    GENERATION = "generation"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"


class TokenUsage(BaseModel):
    """Token usage information for a single request"""
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model: ModelType
    request_type: RequestType
    
    # Token counts
    input_tokens: int = Field(ge=0, description="Number of input tokens")
    output_tokens: int = Field(ge=0, description="Number of output tokens")
    total_tokens: int = Field(ge=0, description="Total tokens used")
    
    # Context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    agent_name: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("total_tokens", always=True)
    def calculate_total(cls, v, values):
        """Calculate total tokens from input and output"""
        if v == 0 and "input_tokens" in values and "output_tokens" in values:
            return values["input_tokens"] + values["output_tokens"]
        return v
    
    class Config:
        use_enum_values = True


class CostRecord(BaseModel):
    """Cost record for a single request"""
    usage: TokenUsage
    
    # Costs (in USD)
    input_cost: float = Field(ge=0, description="Cost of input tokens")
    output_cost: float = Field(ge=0, description="Cost of output tokens")
    total_cost: float = Field(ge=0, description="Total cost")
    
    # Pricing used
    input_price_per_1k: float = Field(ge=0, description="Input price per 1K tokens")
    output_price_per_1k: float = Field(ge=0, description="Output price per 1K tokens")
    
    @validator("total_cost", always=True)
    def calculate_total_cost(cls, v, values):
        """Calculate total cost from input and output"""
        if v == 0 and "input_cost" in values and "output_cost" in values:
            return values["input_cost"] + values["output_cost"]
        return v


class UsageSummary(BaseModel):
    """Summary of usage over a time period"""
    start_time: datetime
    end_time: datetime
    
    # Request counts
    total_requests: int = 0
    requests_by_type: Dict[RequestType, int] = Field(default_factory=dict)
    requests_by_model: Dict[ModelType, int] = Field(default_factory=dict)
    
    # Token counts
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tokens_by_model: Dict[ModelType, int] = Field(default_factory=dict)
    
    # Costs
    total_cost: float = 0.0
    cost_by_model: Dict[ModelType, float] = Field(default_factory=dict)
    cost_by_user: Dict[str, float] = Field(default_factory=dict)
    
    # Averages
    avg_tokens_per_request: float = 0.0
    avg_cost_per_request: float = 0.0
    
    class Config:
        use_enum_values = True


class BudgetPeriod(str, Enum):
    """Budget period types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Budget(BaseModel):
    """Budget configuration"""
    id: str
    name: str
    period: BudgetPeriod
    limit: float = Field(gt=0, description="Budget limit in USD")
    
    # Optional filters
    user_id: Optional[str] = None
    model: Optional[ModelType] = None
    
    # Alert thresholds (percentage of budget)
    warning_threshold: float = Field(default=0.8, ge=0, le=1)
    critical_threshold: float = Field(default=0.95, ge=0, le=1)
    
    # Current usage
    current_usage: float = Field(default=0.0, ge=0)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def usage_percentage(self) -> float:
        """Calculate current usage as percentage of limit"""
        return (self.current_usage / self.limit) * 100 if self.limit > 0 else 0
    
    @property
    def remaining(self) -> float:
        """Calculate remaining budget"""
        return max(0, self.limit - self.current_usage)
    
    @property
    def is_exceeded(self) -> bool:
        """Check if budget is exceeded"""
        return self.current_usage >= self.limit
    
    @property
    def is_critical(self) -> bool:
        """Check if usage is at critical level"""
        return self.current_usage >= (self.limit * self.critical_threshold)
    
    @property
    def is_warning(self) -> bool:
        """Check if usage is at warning level"""
        return self.current_usage >= (self.limit * self.warning_threshold)
    
    class Config:
        use_enum_values = True


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class BudgetAlert(BaseModel):
    """Budget alert"""
    id: str
    budget_id: str
    level: AlertLevel
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Alert details
    current_usage: float
    budget_limit: float
    usage_percentage: float
    
    # Alert status
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    class Config:
        use_enum_values = True


class OptimizationType(str, Enum):
    """Types of optimization recommendations"""
    MODEL_SELECTION = "model_selection"
    PROMPT_OPTIMIZATION = "prompt_optimization"
    CACHING = "caching"
    BATCH_PROCESSING = "batch_processing"
    RATE_LIMITING = "rate_limiting"
    CONTEXT_MANAGEMENT = "context_management"


class OptimizationRecommendation(BaseModel):
    """Cost optimization recommendation"""
    id: str
    type: OptimizationType
    title: str
    description: str
    
    # Impact estimation
    estimated_savings: float = Field(ge=0, description="Estimated monthly savings in USD")
    estimated_savings_percentage: float = Field(ge=0, le=100, description="Estimated savings percentage")
    
    # Implementation
    priority: int = Field(ge=1, le=5, description="Priority (1=highest, 5=lowest)")
    effort: str = Field(description="Implementation effort (low/medium/high)")
    
    # Details
    current_state: str
    recommended_state: str
    implementation_steps: list[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    implemented: bool = False
    implemented_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
