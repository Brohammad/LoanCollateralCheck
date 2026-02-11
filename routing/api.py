"""
Routing API Endpoints

FastAPI endpoints for intent routing system.
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from routing.intent_classifier import IntentClassifier
from routing.router import IntentRouter
from routing.route_registry import RouteRegistry
from routing.context_manager import ContextManager
from routing.fallback_handler import FallbackHandler
from routing.intent_history_tracker import IntentHistoryTracker
from routing.models import (
    Intent,
    IntentType,
    IntentContext,
    Route,
    RouteResult,
    MultiIntentResult,
    FallbackStrategy,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/routing", tags=["routing"])

# Global instances (should be initialized in app startup)
classifier: Optional[IntentClassifier] = None
route_registry: Optional[RouteRegistry] = None
context_manager: Optional[ContextManager] = None
fallback_handler: Optional[FallbackHandler] = None
intent_router: Optional[IntentRouter] = None
history_tracker: Optional[IntentHistoryTracker] = None


def init_routing_system():
    """Initialize routing system components"""
    global classifier, route_registry, context_manager, fallback_handler, intent_router, history_tracker
    
    classifier = IntentClassifier()
    route_registry = RouteRegistry()
    context_manager = ContextManager()
    fallback_handler = FallbackHandler()
    intent_router = IntentRouter(route_registry, context_manager, fallback_handler)
    history_tracker = IntentHistoryTracker()
    
    logger.info("Routing system initialized")


def get_classifier() -> IntentClassifier:
    """Dependency for classifier"""
    if classifier is None:
        raise HTTPException(status_code=500, detail="Routing system not initialized")
    return classifier


def get_router() -> IntentRouter:
    """Dependency for router"""
    if intent_router is None:
        raise HTTPException(status_code=500, detail="Routing system not initialized")
    return intent_router


def get_registry() -> RouteRegistry:
    """Dependency for registry"""
    if route_registry is None:
        raise HTTPException(status_code=500, detail="Routing system not initialized")
    return route_registry


def get_context_manager() -> ContextManager:
    """Dependency for context manager"""
    if context_manager is None:
        raise HTTPException(status_code=500, detail="Routing system not initialized")
    return context_manager


def get_history_tracker() -> IntentHistoryTracker:
    """Dependency for history tracker"""
    if history_tracker is None:
        raise HTTPException(status_code=500, detail="Routing system not initialized")
    return history_tracker


# Request/Response models
class ClassifyRequest(BaseModel):
    """Request to classify intent"""
    user_input: str = Field(..., description="User input text")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    user_id: Optional[str] = Field(None, description="User ID")
    detect_multiple: bool = Field(False, description="Detect multiple intents")


class RouteRequest(BaseModel):
    """Request to route intent"""
    user_input: str = Field(..., description="User input text")
    session_id: Optional[str] = Field(None, description="Session ID")
    user_id: str = Field(..., description="User ID")
    user_authenticated: bool = Field(False, description="User authentication status")


class RegisterRouteRequest(BaseModel):
    """Request to register route"""
    route: Route
    # Note: Handler must be registered separately via Python API


# Endpoints
@router.post("/classify", response_model=Intent)
async def classify_intent(
    request: ClassifyRequest,
    clf: IntentClassifier = Depends(get_classifier),
    ctx_mgr: ContextManager = Depends(get_context_manager),
    tracker: IntentHistoryTracker = Depends(get_history_tracker)
):
    """
    Classify user input into intent
    
    Returns Intent object with type, confidence, entities, etc.
    """
    # Get context if session provided
    context = None
    if request.session_id:
        context = ctx_mgr.get_session(request.session_id)
    
    # Classify
    if request.detect_multiple:
        multi_result = clf.classify_multi(request.user_input, context)
        intent = multi_result.primary_intent
    else:
        intent = clf.classify(request.user_input, context)
    
    # Track intent
    if request.user_id:
        tracker.track(intent, user_id=request.user_id)
    else:
        tracker.track(intent)
    
    return intent


@router.post("/classify-multi", response_model=MultiIntentResult)
async def classify_multi_intent(
    request: ClassifyRequest,
    clf: IntentClassifier = Depends(get_classifier),
    ctx_mgr: ContextManager = Depends(get_context_manager),
    tracker: IntentHistoryTracker = Depends(get_history_tracker)
):
    """
    Classify user input for multiple intents
    
    Returns MultiIntentResult with primary and secondary intents.
    """
    # Get context if session provided
    context = None
    if request.session_id:
        context = ctx_mgr.get_session(request.session_id)
    
    # Classify
    multi_result = clf.classify_multi(request.user_input, context)
    
    # Track all intents
    for intent in multi_result.all_intents:
        if request.user_id:
            tracker.track(intent, user_id=request.user_id)
        else:
            tracker.track(intent)
    
    return multi_result


@router.post("/route", response_model=RouteResult)
async def route_intent(
    request: RouteRequest,
    clf: IntentClassifier = Depends(get_classifier),
    rtr: IntentRouter = Depends(get_router),
    ctx_mgr: ContextManager = Depends(get_context_manager),
    tracker: IntentHistoryTracker = Depends(get_history_tracker)
):
    """
    Classify and route user input to handler
    
    Returns RouteResult with handler response.
    """
    # Get or create session
    context = ctx_mgr.get_or_create_session(
        session_id=request.session_id,
        user_id=request.user_id
    )
    
    # Classify
    intent = clf.classify(request.user_input, context)
    
    # Track
    tracker.track(intent, user_id=request.user_id)
    
    # Route
    result = await rtr.route(
        intent,
        context=context,
        user_authenticated=request.user_authenticated
    )
    
    # Update context
    ctx_mgr.update_session(
        context.session_id,
        intent=intent,
        context_data={"last_result": result.dict()}
    )
    
    return result


@router.get("/routes", response_model=List[Route])
async def list_routes(
    intent_type: Optional[IntentType] = Query(None, description="Filter by intent type"),
    enabled_only: bool = Query(False, description="Return only enabled routes"),
    registry: RouteRegistry = Depends(get_registry)
):
    """List all registered routes"""
    return registry.list_routes(intent_type=intent_type, enabled_only=enabled_only)


@router.get("/routes/{route_id}", response_model=Route)
async def get_route(
    route_id: str,
    registry: RouteRegistry = Depends(get_registry)
):
    """Get route by ID"""
    route = registry.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")
    return route


@router.post("/routes/{route_id}/enable")
async def enable_route(
    route_id: str,
    registry: RouteRegistry = Depends(get_registry)
):
    """Enable a route"""
    route = registry.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")
    
    registry.enable_route(route_id)
    return {"message": f"Route {route_id} enabled"}


@router.post("/routes/{route_id}/disable")
async def disable_route(
    route_id: str,
    registry: RouteRegistry = Depends(get_registry)
):
    """Disable a route"""
    route = registry.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")
    
    registry.disable_route(route_id)
    return {"message": f"Route {route_id} disabled"}


@router.get("/routes/{route_id}/metrics")
async def get_route_metrics(
    route_id: str,
    registry: RouteRegistry = Depends(get_registry)
):
    """Get metrics for a route"""
    metrics = registry.get_metrics(route_id)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Metrics for route {route_id} not found")
    return metrics


@router.get("/metrics/summary")
async def get_metrics_summary(
    registry: RouteRegistry = Depends(get_registry)
):
    """Get overall routing metrics summary"""
    return registry.get_summary()


@router.get("/metrics/top-routes")
async def get_top_routes(
    n: int = Query(10, ge=1, le=100, description="Number of routes to return"),
    by: str = Query("executions", regex="^(executions|success_rate|avg_time)$"),
    registry: RouteRegistry = Depends(get_registry)
):
    """Get top N routes by metric"""
    top_routes = registry.get_top_routes(n=n, by=by)
    return [
        {"route_id": route_id, "metrics": metrics.dict()}
        for route_id, metrics in top_routes
    ]


@router.post("/sessions")
async def create_session(
    user_id: str,
    language: str = "en",
    ctx_mgr: ContextManager = Depends(get_context_manager)
):
    """Create a new session"""
    context = ctx_mgr.create_session(user_id=user_id, language=language)
    return {"session_id": context.session_id}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    ctx_mgr: ContextManager = Depends(get_context_manager)
):
    """Get session context"""
    context = ctx_mgr.get_session(session_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return context


@router.delete("/sessions/{session_id}")
async def end_session(
    session_id: str,
    ctx_mgr: ContextManager = Depends(get_context_manager)
):
    """End a session"""
    ctx_mgr.end_session(session_id)
    return {"message": f"Session {session_id} ended"}


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    n: Optional[int] = Query(None, ge=1, description="Number of recent intents"),
    ctx_mgr: ContextManager = Depends(get_context_manager)
):
    """Get conversation history for session"""
    history = ctx_mgr.get_conversation_history(session_id, n=n)
    return {"session_id": session_id, "history": history}


@router.get("/history")
async def get_intent_history(
    user_id: Optional[str] = Query(None, description="Filter by user"),
    intent_type: Optional[IntentType] = Query(None, description="Filter by intent type"),
    hours: Optional[int] = Query(None, ge=1, description="Last N hours"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Max results"),
    tracker: IntentHistoryTracker = Depends(get_history_tracker)
):
    """Get intent history with filters"""
    since = datetime.utcnow() - timedelta(hours=hours) if hours else None
    
    history = tracker.get_history(
        user_id=user_id,
        intent_type=intent_type,
        since=since,
        limit=limit
    )
    
    return {
        "count": len(history),
        "history": history
    }


@router.get("/history/frequency")
async def get_intent_frequency(
    user_id: Optional[str] = Query(None, description="Filter by user"),
    hours: Optional[int] = Query(24, ge=1, description="Last N hours"),
    tracker: IntentHistoryTracker = Depends(get_history_tracker)
):
    """Get intent frequency counts"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    frequency = tracker.get_frequency(user_id=user_id, since=since)
    
    return {
        "frequency": {
            itype.value: count
            for itype, count in frequency.items()
        }
    }


@router.get("/history/top-intents")
async def get_top_intents(
    n: int = Query(10, ge=1, le=50),
    user_id: Optional[str] = Query(None),
    hours: Optional[int] = Query(24, ge=1),
    tracker: IntentHistoryTracker = Depends(get_history_tracker)
):
    """Get top N most frequent intents"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    top_intents = tracker.get_top_intents(n=n, user_id=user_id, since=since)
    
    return {
        "top_intents": [
            {"type": itype.value, "count": count}
            for itype, count in top_intents
        ]
    }


@router.get("/history/confidence-stats")
async def get_confidence_stats(
    intent_type: Optional[IntentType] = Query(None),
    user_id: Optional[str] = Query(None),
    hours: Optional[int] = Query(24, ge=1),
    tracker: IntentHistoryTracker = Depends(get_history_tracker)
):
    """Get confidence statistics"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    stats = tracker.get_confidence_stats(
        intent_type=intent_type,
        user_id=user_id,
        since=since
    )
    
    return stats


@router.get("/history/hourly-volume")
async def get_hourly_volume(
    hours: int = Query(24, ge=1, le=168),
    user_id: Optional[str] = Query(None),
    tracker: IntentHistoryTracker = Depends(get_history_tracker)
):
    """Get intent volume by hour"""
    volume = tracker.get_hourly_volume(hours=hours, user_id=user_id)
    return {"volume": volume}


@router.get("/history/user-patterns/{user_id}")
async def get_user_patterns(
    user_id: str,
    tracker: IntentHistoryTracker = Depends(get_history_tracker)
):
    """Get behavior patterns for a user"""
    patterns = tracker.get_user_patterns(user_id)
    return patterns


@router.get("/history/summary")
async def get_history_summary(
    tracker: IntentHistoryTracker = Depends(get_history_tracker)
):
    """Get overall history summary"""
    return tracker.get_summary()


@router.get("/classifier/statistics")
async def get_classifier_statistics(
    clf: IntentClassifier = Depends(get_classifier)
):
    """Get classifier statistics"""
    return clf.get_statistics()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "components": {
            "classifier": classifier is not None,
            "router": intent_router is not None,
            "registry": route_registry is not None,
            "context_manager": context_manager is not None,
            "fallback_handler": fallback_handler is not None,
            "history_tracker": history_tracker is not None,
        }
    }
