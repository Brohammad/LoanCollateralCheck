"""
Route Registry

Manages registration and lookup of intent routes.
Supports dynamic route registration, priority handling, and route metrics.
"""

import logging
from typing import Dict, List, Optional, Callable
from collections import defaultdict
from datetime import datetime, timedelta

from routing.models import (
    Route,
    IntentType,
    RouteMetrics,
)

logger = logging.getLogger(__name__)


class RouteRegistry:
    """
    Registry for managing intent routes
    
    Features:
    - Dynamic route registration
    - Priority-based routing
    - Route metrics tracking
    - Route enabling/disabling
    - Handler validation
    """
    
    def __init__(self):
        """Initialize route registry"""
        self.routes: Dict[str, Route] = {}
        self.routes_by_intent: Dict[IntentType, List[Route]] = defaultdict(list)
        self.handlers: Dict[str, Callable] = {}
        self.metrics: Dict[str, RouteMetrics] = {}
    
    def register_route(
        self,
        route: Route,
        handler: Callable,
        override: bool = False
    ):
        """
        Register a route with its handler
        
        Args:
            route: Route configuration
            handler: Handler function/callable
            override: Whether to override existing route
        """
        if route.route_id in self.routes and not override:
            raise ValueError(f"Route {route.route_id} already registered. Use override=True to replace.")
        
        # Validate handler
        if not callable(handler):
            raise ValueError(f"Handler must be callable")
        
        # Register route
        self.routes[route.route_id] = route
        self.handlers[route.route_id] = handler
        
        # Index by intent type
        self.routes_by_intent[route.intent_type].append(route)
        
        # Sort by priority (ascending, so priority 1 comes first)
        self.routes_by_intent[route.intent_type].sort(key=lambda r: r.priority)
        
        # Initialize metrics
        if route.route_id not in self.metrics:
            self.metrics[route.route_id] = RouteMetrics(route_id=route.route_id)
        
        logger.info(f"Registered route: {route.route_id} for intent: {route.intent_type}")
    
    def unregister_route(self, route_id: str):
        """Unregister a route"""
        if route_id not in self.routes:
            raise ValueError(f"Route {route_id} not found")
        
        route = self.routes[route_id]
        
        # Remove from routes
        del self.routes[route_id]
        del self.handlers[route_id]
        
        # Remove from intent index
        self.routes_by_intent[route.intent_type] = [
            r for r in self.routes_by_intent[route.intent_type]
            if r.route_id != route_id
        ]
        
        logger.info(f"Unregistered route: {route_id}")
    
    def get_route(self, route_id: str) -> Optional[Route]:
        """Get route by ID"""
        return self.routes.get(route_id)
    
    def get_routes_for_intent(
        self,
        intent_type: IntentType,
        enabled_only: bool = True
    ) -> List[Route]:
        """
        Get all routes for an intent type
        
        Args:
            intent_type: Intent type
            enabled_only: Return only enabled routes
        
        Returns:
            List of routes sorted by priority
        """
        routes = self.routes_by_intent.get(intent_type, [])
        
        if enabled_only:
            routes = [r for r in routes if r.enabled]
        
        return routes
    
    def get_handler(self, route_id: str) -> Optional[Callable]:
        """Get handler for a route"""
        return self.handlers.get(route_id)
    
    def enable_route(self, route_id: str):
        """Enable a route"""
        if route_id in self.routes:
            self.routes[route_id].enabled = True
            logger.info(f"Enabled route: {route_id}")
    
    def disable_route(self, route_id: str):
        """Disable a route"""
        if route_id in self.routes:
            self.routes[route_id].enabled = False
            logger.info(f"Disabled route: {route_id}")
    
    def update_metrics(
        self,
        route_id: str,
        success: bool,
        execution_time_ms: float,
        confidence: float
    ):
        """Update route metrics"""
        if route_id not in self.metrics:
            self.metrics[route_id] = RouteMetrics(route_id=route_id)
        
        metrics = self.metrics[route_id]
        
        # Update execution counts
        metrics.total_executions += 1
        if success:
            metrics.successful_executions += 1
        else:
            metrics.failed_executions += 1
        
        # Update timing metrics
        if metrics.total_executions == 1:
            metrics.avg_execution_time_ms = execution_time_ms
            metrics.min_execution_time_ms = execution_time_ms
            metrics.max_execution_time_ms = execution_time_ms
        else:
            # Update average
            total_time = metrics.avg_execution_time_ms * (metrics.total_executions - 1)
            metrics.avg_execution_time_ms = (total_time + execution_time_ms) / metrics.total_executions
            
            # Update min/max
            metrics.min_execution_time_ms = min(metrics.min_execution_time_ms, execution_time_ms)
            metrics.max_execution_time_ms = max(metrics.max_execution_time_ms, execution_time_ms)
        
        # Update confidence average
        if metrics.total_executions == 1:
            metrics.avg_confidence = confidence
        else:
            total_confidence = metrics.avg_confidence * (metrics.total_executions - 1)
            metrics.avg_confidence = (total_confidence + confidence) / metrics.total_executions
        
        # Update timestamps
        metrics.last_execution = datetime.utcnow()
        metrics.executions_last_hour += 1
        metrics.executions_last_day += 1
    
    def get_metrics(self, route_id: str) -> Optional[RouteMetrics]:
        """Get metrics for a route"""
        return self.metrics.get(route_id)
    
    def get_all_metrics(self) -> Dict[str, RouteMetrics]:
        """Get metrics for all routes"""
        return self.metrics.copy()
    
    def get_top_routes(self, n: int = 10, by: str = "executions") -> List[tuple]:
        """
        Get top N routes by metric
        
        Args:
            n: Number of routes to return
            by: Metric to sort by (executions, success_rate, avg_time)
        
        Returns:
            List of (route_id, metric_value) tuples
        """
        if by == "executions":
            sorted_metrics = sorted(
                self.metrics.items(),
                key=lambda x: x[1].total_executions,
                reverse=True
            )
        elif by == "success_rate":
            sorted_metrics = sorted(
                self.metrics.items(),
                key=lambda x: x[1].success_rate,
                reverse=True
            )
        elif by == "avg_time":
            sorted_metrics = sorted(
                self.metrics.items(),
                key=lambda x: x[1].avg_execution_time_ms
            )
        else:
            raise ValueError(f"Unknown metric: {by}")
        
        return [(route_id, metrics) for route_id, metrics in sorted_metrics[:n]]
    
    def list_routes(
        self,
        intent_type: Optional[IntentType] = None,
        enabled_only: bool = False
    ) -> List[Route]:
        """
        List all routes
        
        Args:
            intent_type: Filter by intent type
            enabled_only: Return only enabled routes
        
        Returns:
            List of routes
        """
        if intent_type:
            routes = self.get_routes_for_intent(intent_type, enabled_only=False)
        else:
            routes = list(self.routes.values())
        
        if enabled_only:
            routes = [r for r in routes if r.enabled]
        
        return routes
    
    def reset_metrics(self, route_id: Optional[str] = None):
        """
        Reset metrics
        
        Args:
            route_id: Specific route ID to reset, or None to reset all
        """
        if route_id:
            if route_id in self.metrics:
                self.metrics[route_id] = RouteMetrics(route_id=route_id)
        else:
            self.metrics = {
                route_id: RouteMetrics(route_id=route_id)
                for route_id in self.routes.keys()
            }
        
        logger.info(f"Reset metrics for: {route_id or 'all routes'}")
    
    def get_summary(self) -> Dict[str, any]:
        """Get registry summary"""
        total_routes = len(self.routes)
        enabled_routes = sum(1 for r in self.routes.values() if r.enabled)
        
        # Count by intent type
        by_intent = {
            intent_type: len(routes)
            for intent_type, routes in self.routes_by_intent.items()
        }
        
        # Total executions
        total_executions = sum(m.total_executions for m in self.metrics.values())
        total_successes = sum(m.successful_executions for m in self.metrics.values())
        total_failures = sum(m.failed_executions for m in self.metrics.values())
        
        return {
            "total_routes": total_routes,
            "enabled_routes": enabled_routes,
            "disabled_routes": total_routes - enabled_routes,
            "routes_by_intent": by_intent,
            "total_executions": total_executions,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "overall_success_rate": (total_successes / total_executions * 100) if total_executions > 0 else 0.0,
        }
