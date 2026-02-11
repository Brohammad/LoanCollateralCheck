"""
Polymorphic Intent Routing Module

Advanced intent classification and routing system with:
- Multi-intent detection and handling
- Confidence scoring with thresholds
- Context-aware routing
- Fallback strategies
- Intent history tracking
- Dynamic route registration
"""

from .models import (
    Intent,
    IntentType,
    IntentConfidence,
    Route,
    RouteResult,
    IntentContext,
    MultiIntentResult,
    FallbackStrategy,
    FallbackResult,
    IntentPattern,
    RouteMetrics,
)

from .intent_classifier import IntentClassifier
from .router import IntentRouter
from .route_registry import RouteRegistry
from .context_manager import ContextManager
from .fallback_handler import FallbackHandler
from .intent_history_tracker import IntentHistoryTracker

__all__ = [
    # Models
    "Intent",
    "IntentType",
    "IntentConfidence",
    "Route",
    "RouteResult",
    "IntentContext",
    "MultiIntentResult",
    "FallbackStrategy",
    "FallbackResult",
    "IntentPattern",
    "RouteMetrics",
    # Components
    "IntentClassifier",
    "IntentRouter",
    "RouteRegistry",
    "ContextManager",
    "FallbackHandler",
    "IntentHistoryTracker",
]

__version__ = "1.0.0"
