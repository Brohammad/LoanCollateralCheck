"""
Routing Data Models

Pydantic models for intent classification, routing, and context management.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Intent type classification"""
    # Core intents
    GREETING = "greeting"
    QUESTION = "question"
    COMMAND = "command"
    FEEDBACK = "feedback"
    
    # Business intents
    LOAN_APPLICATION = "loan_application"
    COLLATERAL_CHECK = "collateral_check"
    CREDIT_HISTORY = "credit_history"
    DOCUMENT_UPLOAD = "document_upload"
    
    # LinkedIn intents
    PROFILE_ANALYSIS = "profile_analysis"
    JOB_MATCHING = "job_matching"
    SKILL_RECOMMENDATION = "skill_recommendation"
    
    # System intents
    HELP = "help"
    STATUS = "status"
    SETTINGS = "settings"
    
    # Composite intents
    MULTI_INTENT = "multi_intent"
    CLARIFICATION_NEEDED = "clarification_needed"
    UNKNOWN = "unknown"


class IntentConfidence(str, Enum):
    """Confidence level for intent classification"""
    VERY_HIGH = "very_high"  # > 0.9
    HIGH = "high"  # 0.75 - 0.9
    MEDIUM = "medium"  # 0.5 - 0.75
    LOW = "low"  # 0.3 - 0.5
    VERY_LOW = "very_low"  # < 0.3


class FallbackStrategy(str, Enum):
    """Fallback strategy when intent is unclear"""
    ASK_CLARIFICATION = "ask_clarification"
    USE_DEFAULT = "use_default"
    USE_HISTORY = "use_history"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    PROVIDE_OPTIONS = "provide_options"


class Intent(BaseModel):
    """Intent classification result"""
    intent_id: str = Field(..., description="Unique intent identifier")
    type: IntentType = Field(..., description="Intent type")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    confidence_level: IntentConfidence = Field(..., description="Confidence level")
    
    # Intent details
    user_input: str = Field(..., description="Original user input")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Intent parameters")
    
    # Context
    requires_context: bool = Field(False, description="Requires conversation context")
    context_keys: List[str] = Field(default_factory=list, description="Required context keys")
    
    # Metadata
    language: str = Field("en", description="Detected language")
    sentiment: Optional[str] = Field(None, description="Sentiment (positive/negative/neutral)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "intent_id": "intent_12345",
                "type": "loan_application",
                "confidence": 0.92,
                "confidence_level": "very_high",
                "user_input": "I want to apply for a business loan",
                "entities": {"loan_type": "business"},
                "parameters": {"amount": None},
                "requires_context": False,
            }
        }


class MultiIntentResult(BaseModel):
    """Result when multiple intents are detected"""
    primary_intent: Intent = Field(..., description="Primary/main intent")
    secondary_intents: List[Intent] = Field(default_factory=list, description="Additional intents")
    execution_order: List[str] = Field(default_factory=list, description="Intent IDs in execution order")
    requires_clarification: bool = Field(False, description="User needs to clarify priority")
    
    @property
    def all_intents(self) -> List[Intent]:
        """Get all intents (primary + secondary)"""
        return [self.primary_intent] + self.secondary_intents
    
    @property
    def intent_count(self) -> int:
        """Total number of intents"""
        return len(self.all_intents)


class IntentContext(BaseModel):
    """Context for intent processing"""
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    
    # Conversation state
    conversation_history: List[Intent] = Field(default_factory=list, description="Previous intents")
    current_topic: Optional[str] = Field(None, description="Current conversation topic")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Session context data")
    
    # User preferences
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    language: str = Field("en", description="User language")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction: datetime = Field(default_factory=datetime.utcnow)
    interaction_count: int = Field(0, description="Number of interactions in session")
    
    def add_intent(self, intent: Intent):
        """Add intent to conversation history"""
        self.conversation_history.append(intent)
        self.last_interaction = datetime.utcnow()
        self.interaction_count += 1
        
        # Update current topic based on intent
        if intent.type != IntentType.UNKNOWN:
            self.current_topic = intent.type.value
    
    def get_last_intent(self) -> Optional[Intent]:
        """Get last intent from history"""
        return self.conversation_history[-1] if self.conversation_history else None
    
    def get_recent_intents(self, n: int = 5) -> List[Intent]:
        """Get last N intents"""
        return self.conversation_history[-n:]


class Route(BaseModel):
    """Route definition for intent handling"""
    route_id: str = Field(..., description="Unique route identifier")
    intent_type: IntentType = Field(..., description="Intent type this route handles")
    handler_name: str = Field(..., description="Handler function/class name")
    
    # Route configuration
    priority: int = Field(1, ge=1, le=10, description="Route priority (1=highest)")
    requires_auth: bool = Field(False, description="Requires authentication")
    requires_context: List[str] = Field(default_factory=list, description="Required context keys")
    
    # Conditions
    min_confidence: float = Field(0.5, ge=0, le=1, description="Minimum confidence threshold")
    max_concurrent: Optional[int] = Field(None, description="Max concurrent executions")
    
    # Rate limiting
    rate_limit: Optional[int] = Field(None, description="Max requests per minute")
    
    # Metadata
    description: Optional[str] = Field(None, description="Route description")
    tags: List[str] = Field(default_factory=list, description="Route tags")
    enabled: bool = Field(True, description="Route is enabled")
    
    class Config:
        json_schema_extra = {
            "example": {
                "route_id": "route_loan_app",
                "intent_type": "loan_application",
                "handler_name": "handle_loan_application",
                "priority": 1,
                "requires_auth": True,
                "min_confidence": 0.7,
                "description": "Process loan application requests",
            }
        }


class RouteResult(BaseModel):
    """Result of route execution"""
    route_id: str = Field(..., description="Route that was executed")
    intent: Intent = Field(..., description="Intent that was routed")
    
    # Execution result
    success: bool = Field(..., description="Execution was successful")
    response: Any = Field(None, description="Handler response")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    # Metrics
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    tokens_used: Optional[int] = Field(None, description="Tokens used (if LLM call)")
    
    # Follow-up
    requires_followup: bool = Field(False, description="Requires follow-up action")
    followup_intent: Optional[IntentType] = Field(None, description="Suggested follow-up intent")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "route_id": "route_loan_app",
                "intent": {"intent_id": "intent_123", "type": "loan_application"},
                "success": True,
                "response": {"status": "initiated", "application_id": "APP123"},
                "execution_time_ms": 245.5,
            }
        }


class FallbackResult(BaseModel):
    """Result of fallback handling"""
    strategy_used: FallbackStrategy = Field(..., description="Fallback strategy used")
    intent: Intent = Field(..., description="Original intent")
    
    # Result
    handled: bool = Field(..., description="Fallback successfully handled")
    response: Any = Field(None, description="Fallback response")
    suggested_actions: List[str] = Field(default_factory=list, description="Suggested user actions")
    
    # Options provided
    clarification_options: Optional[List[Dict[str, Any]]] = Field(
        None, description="Clarification options for user"
    )
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IntentPattern(BaseModel):
    """Pattern for intent matching"""
    pattern_id: str = Field(..., description="Pattern identifier")
    intent_type: IntentType = Field(..., description="Intent type")
    
    # Pattern matching
    keywords: List[str] = Field(default_factory=list, description="Keywords to match")
    phrases: List[str] = Field(default_factory=list, description="Exact phrases to match")
    regex_patterns: List[str] = Field(default_factory=list, description="Regex patterns")
    
    # Weights
    keyword_weight: float = Field(0.3, description="Weight for keyword matches")
    phrase_weight: float = Field(0.5, description="Weight for phrase matches")
    regex_weight: float = Field(0.2, description="Weight for regex matches")
    
    # Entity extraction
    entity_patterns: Dict[str, str] = Field(
        default_factory=dict,
        description="Entity extraction patterns (entity_name: regex)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "pattern_id": "pattern_loan",
                "intent_type": "loan_application",
                "keywords": ["loan", "apply", "application", "borrow"],
                "phrases": ["apply for a loan", "loan application"],
                "entity_patterns": {"loan_type": r"(business|personal|auto|home)\s+loan"},
            }
        }


class RouteMetrics(BaseModel):
    """Metrics for route performance"""
    route_id: str = Field(..., description="Route identifier")
    
    # Execution metrics
    total_executions: int = Field(0, description="Total executions")
    successful_executions: int = Field(0, description="Successful executions")
    failed_executions: int = Field(0, description="Failed executions")
    
    # Timing metrics
    avg_execution_time_ms: float = Field(0.0, description="Average execution time")
    min_execution_time_ms: float = Field(0.0, description="Minimum execution time")
    max_execution_time_ms: float = Field(0.0, description="Maximum execution time")
    
    # Confidence metrics
    avg_confidence: float = Field(0.0, description="Average intent confidence")
    
    # Recent activity
    last_execution: Optional[datetime] = Field(None, description="Last execution time")
    executions_last_hour: int = Field(0, description="Executions in last hour")
    executions_last_day: int = Field(0, description="Executions in last 24 hours")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_executions == 0:
            return 0.0
        return (self.successful_executions / self.total_executions) * 100
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate"""
        if self.total_executions == 0:
            return 0.0
        return (self.failed_executions / self.total_executions) * 100
