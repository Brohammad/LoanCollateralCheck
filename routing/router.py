"""
Intent Router

Routes classified intents to appropriate handlers with validation and execution.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from routing.models import (
    Intent,
    IntentType,
    IntentContext,
    Route,
    RouteResult,
    MultiIntentResult,
    FallbackResult,
    IntentConfidence,
)
from routing.route_registry import RouteRegistry
from routing.context_manager import ContextManager
from routing.fallback_handler import FallbackHandler

logger = logging.getLogger(__name__)


class IntentRouter:
    """
    Routes intents to handlers with validation and execution
    
    Features:
    - Route lookup and validation
    - Confidence threshold checking
    - Authentication validation
    - Context requirement validation
    - Multi-intent execution ordering
    - Fallback handling
    - Execution metrics tracking
    """
    
    def __init__(
        self,
        registry: RouteRegistry,
        context_manager: ContextManager,
        fallback_handler: FallbackHandler
    ):
        """
        Initialize router
        
        Args:
            registry: Route registry
            context_manager: Context manager
            fallback_handler: Fallback handler
        """
        self.registry = registry
        self.context_manager = context_manager
        self.fallback_handler = fallback_handler
    
    async def route(
        self,
        intent: Intent,
        context: Optional[IntentContext] = None,
        user_authenticated: bool = False
    ) -> RouteResult:
        """
        Route a single intent
        
        Args:
            intent: Classified intent
            context: Optional session context
            user_authenticated: Whether user is authenticated
        
        Returns:
            RouteResult with execution outcome
        """
        start_time = datetime.utcnow()
        
        # Get routes for intent type
        routes = self.registry.get_routes_for_intent(intent.intent_type, enabled_only=True)
        
        if not routes:
            logger.warning(f"No routes found for intent: {intent.intent_type}")
            return await self._handle_no_route(intent, context)
        
        # Find first suitable route
        for route in routes:
            # Check confidence threshold
            if intent.confidence < route.min_confidence:
                logger.debug(f"Intent confidence {intent.confidence} below route minimum {route.min_confidence}")
                continue
            
            # Check authentication
            if route.requires_auth and not user_authenticated:
                logger.warning(f"Route {route.route_id} requires authentication")
                continue
            
            # Check context requirements
            if route.requires_context and context:
                missing_keys = [
                    key for key in route.requires_context
                    if key not in context.context_data
                ]
                if missing_keys:
                    logger.warning(f"Route {route.route_id} missing context keys: {missing_keys}")
                    continue
            elif route.requires_context:
                logger.warning(f"Route {route.route_id} requires context but none provided")
                continue
            
            # Execute route
            try:
                result = await self._execute_route(route, intent, context)
                
                # Update metrics
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                self.registry.update_metrics(
                    route.route_id,
                    success=result.success,
                    execution_time_ms=execution_time,
                    confidence=intent.confidence
                )
                
                return result
            
            except Exception as e:
                logger.error(f"Error executing route {route.route_id}: {e}")
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                # Update metrics
                self.registry.update_metrics(
                    route.route_id,
                    success=False,
                    execution_time_ms=execution_time,
                    confidence=intent.confidence
                )
                
                return RouteResult(
                    route_id=route.route_id,
                    intent=intent,
                    success=False,
                    error=str(e),
                    execution_time_ms=execution_time
                )
        
        # No suitable route found - use fallback
        logger.info(f"No suitable route found for intent: {intent.intent_type}")
        return await self._handle_no_route(intent, context)
    
    async def route_multi(
        self,
        multi_intent: MultiIntentResult,
        context: Optional[IntentContext] = None,
        user_authenticated: bool = False
    ) -> List[RouteResult]:
        """
        Route multiple intents in order
        
        Args:
            multi_intent: Multi-intent result
            context: Optional session context
            user_authenticated: Whether user is authenticated
        
        Returns:
            List of RouteResults in execution order
        """
        results = []
        
        # Execute intents in order
        for intent_id in multi_intent.execution_order:
            # Find intent by ID
            intent = None
            if multi_intent.primary_intent.intent_id == intent_id:
                intent = multi_intent.primary_intent
            else:
                intent = next(
                    (i for i in multi_intent.secondary_intents if i.intent_id == intent_id),
                    None
                )
            
            if not intent:
                logger.error(f"Intent {intent_id} not found in multi-intent result")
                continue
            
            # Route intent
            result = await self.route(intent, context, user_authenticated)
            results.append(result)
            
            # Update context with result
            if context:
                context.add_intent(intent)
                context.context_data[f"result_{intent_id}"] = result.dict()
        
        return results
    
    async def _execute_route(
        self,
        route: Route,
        intent: Intent,
        context: Optional[IntentContext]
    ) -> RouteResult:
        """
        Execute a route's handler
        
        Args:
            route: Route to execute
            intent: Intent to handle
            context: Optional session context
        
        Returns:
            RouteResult with execution outcome
        """
        start_time = datetime.utcnow()
        
        # Get handler
        handler = self.registry.get_handler(route.route_id)
        if not handler:
            raise ValueError(f"Handler not found for route: {route.route_id}")
        
        # Prepare handler arguments
        handler_args = {
            "intent": intent,
            "context": context,
        }
        
        # Execute handler
        try:
            response = await handler(**handler_args)
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return RouteResult(
                route_id=route.route_id,
                intent=intent,
                success=True,
                response=response,
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Handler execution error: {e}")
            
            return RouteResult(
                route_id=route.route_id,
                intent=intent,
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    async def _handle_no_route(
        self,
        intent: Intent,
        context: Optional[IntentContext]
    ) -> RouteResult:
        """
        Handle case where no route found
        
        Args:
            intent: Intent that couldn't be routed
            context: Optional session context
        
        Returns:
            RouteResult from fallback handler
        """
        # Use fallback handler
        fallback_result = await self.fallback_handler.handle(intent, context)
        
        return RouteResult(
            route_id="fallback",
            intent=intent,
            success=fallback_result.handled,
            response=fallback_result.response,
            execution_time_ms=0.0
        )
    
    def validate_route(
        self,
        route_id: str,
        intent: Intent,
        context: Optional[IntentContext] = None,
        user_authenticated: bool = False
    ) -> Dict[str, Any]:
        """
        Validate if route can handle intent
        
        Args:
            route_id: Route ID to validate
            intent: Intent to validate
            context: Optional session context
            user_authenticated: Whether user is authenticated
        
        Returns:
            Validation result with can_route and reasons
        """
        route = self.registry.get_route(route_id)
        if not route:
            return {
                "can_route": False,
                "reasons": [f"Route {route_id} not found"]
            }
        
        reasons = []
        
        # Check enabled
        if not route.enabled:
            reasons.append("Route is disabled")
        
        # Check intent type
        if route.intent_type != intent.intent_type:
            reasons.append(f"Route expects {route.intent_type}, got {intent.intent_type}")
        
        # Check confidence
        if intent.confidence < route.min_confidence:
            reasons.append(f"Confidence {intent.confidence} below minimum {route.min_confidence}")
        
        # Check authentication
        if route.requires_auth and not user_authenticated:
            reasons.append("Route requires authentication")
        
        # Check context requirements
        if route.requires_context:
            if not context:
                reasons.append("Route requires context but none provided")
            else:
                missing_keys = [
                    key for key in route.requires_context
                    if key not in context.context_data
                ]
                if missing_keys:
                    reasons.append(f"Missing context keys: {missing_keys}")
        
        return {
            "can_route": len(reasons) == 0,
            "reasons": reasons
        }
