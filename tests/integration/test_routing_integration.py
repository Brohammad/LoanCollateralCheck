"""
End-to-End Routing Integration Tests

Tests the complete routing flow from classification to execution
across all components: classifier, router, registry, context, fallback, history.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from routing import (
    IntentClassifier,
    IntentRouter,
    RouteRegistry,
    ContextManager,
    FallbackHandler,
    IntentHistoryTracker,
    IntentType,
    IntentConfidence,
    Route,
)


class TestEndToEndRouting:
    """End-to-end routing integration tests"""
    
    @pytest.fixture
    async def routing_system(self):
        """Setup complete routing system"""
        classifier = IntentClassifier()
        registry = RouteRegistry()
        context_manager = ContextManager()
        fallback_handler = FallbackHandler()
        router = IntentRouter(registry, context_manager, fallback_handler)
        history_tracker = IntentHistoryTracker()
        
        # Register test routes
        async def handle_loan_application(intent, context):
            return {
                "message": "Loan application received",
                "loan_type": intent.entities.get("loan_type", "personal"),
                "amount": intent.entities.get("amount", "unspecified"),
                "status": "pending"
            }
        
        async def handle_credit_check(intent, context):
            return {
                "message": "Credit check initiated",
                "credit_score": 720,
                "status": "good"
            }
        
        async def handle_greeting(intent, context):
            return {
                "message": "Hello! How can I help you today?",
                "available_services": ["loans", "credit", "documents"]
            }
        
        # Register routes
        registry.register_route(
            Route(
                route_id="loan_application",
                intent_type=IntentType.LOAN_APPLICATION,
                handler_name="handle_loan_application",
                priority=1,
                requires_auth=False,
                min_confidence=0.6
            ),
            handle_loan_application
        )
        
        registry.register_route(
            Route(
                route_id="credit_check",
                intent_type=IntentType.CREDIT_HISTORY,
                handler_name="handle_credit_check",
                priority=1,
                requires_auth=False,
                min_confidence=0.6
            ),
            handle_credit_check
        )
        
        registry.register_route(
            Route(
                route_id="greeting",
                intent_type=IntentType.GREETING,
                handler_name="handle_greeting",
                priority=1,
                requires_auth=False,
                min_confidence=0.5
            ),
            handle_greeting
        )
        
        yield {
            "classifier": classifier,
            "router": router,
            "registry": registry,
            "context_manager": context_manager,
            "fallback_handler": fallback_handler,
            "history_tracker": history_tracker,
        }
    
    @pytest.mark.asyncio
    async def test_complete_loan_application_flow(self, routing_system):
        """Test complete loan application flow"""
        classifier = routing_system["classifier"]
        router = routing_system["router"]
        context_manager = routing_system["context_manager"]
        history_tracker = routing_system["history_tracker"]
        
        # Create session
        context = context_manager.create_session(user_id="test_user_001")
        
        # User input
        user_input = "I want to apply for a business loan of $50,000"
        
        # Classify
        intent = classifier.classify(user_input, context)
        
        # Track
        history_tracker.track(intent, user_id="test_user_001")
        
        # Route
        result = await router.route(intent, context=context)
        
        # Assertions
        assert intent.intent_type == IntentType.LOAN_APPLICATION
        assert intent.confidence >= 0.6
        assert "business" in str(intent.entities.get("loan_type", "")).lower()
        assert result.success
        assert result.response["message"] == "Loan application received"
        assert result.response["loan_type"] == "business"
        
        # Verify history
        history = history_tracker.get_history(user_id="test_user_001")
        assert len(history) == 1
        assert history[0].intent_type == IntentType.LOAN_APPLICATION
    
    @pytest.mark.asyncio
    async def test_multi_intent_conversation_flow(self, routing_system):
        """Test multi-intent detection and execution"""
        classifier = routing_system["classifier"]
        router = routing_system["router"]
        context_manager = routing_system["context_manager"]
        
        # Create session
        context = context_manager.create_session(user_id="test_user_002")
        
        # User input with multiple intents
        user_input = "Check my credit score and help me apply for a loan"
        
        # Classify multi-intent
        multi_result = classifier.classify_multi(user_input, context)
        
        # Assertions
        assert len(multi_result.all_intents) >= 2
        assert IntentType.CREDIT_HISTORY in [i.intent_type for i in multi_result.all_intents]
        assert IntentType.LOAN_APPLICATION in [i.intent_type for i in multi_result.all_intents]
        
        # Route all intents
        results = await router.route_multi(multi_result, context=context)
        
        # Verify both were executed
        assert len(results) >= 2
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_context_aware_conversation(self, routing_system):
        """Test context-aware routing across conversation"""
        classifier = routing_system["classifier"]
        router = routing_system["router"]
        context_manager = routing_system["context_manager"]
        
        # Create session
        context = context_manager.create_session(user_id="test_user_003")
        
        # First message - greeting
        intent1 = classifier.classify("Hello", context)
        result1 = await router.route(intent1, context=context)
        
        assert intent1.intent_type == IntentType.GREETING
        assert result1.success
        
        # Update context
        context_manager.update_session(
            context.session_id,
            intent=intent1,
            topic="loan_application"
        )
        
        # Second message - with context bonus
        intent2 = classifier.classify("How much can I borrow?", context)
        
        # Should get context bonus for topic continuity
        assert intent2.confidence > 0.5
        
        result2 = await router.route(intent2, context=context)
        assert result2.success
        
        # Verify conversation history
        history = context_manager.get_conversation_history(context.session_id)
        assert len(history) >= 2
    
    @pytest.mark.asyncio
    async def test_fallback_handling_low_confidence(self, routing_system):
        """Test fallback handling for unclear intents"""
        classifier = routing_system["classifier"]
        router = routing_system["router"]
        context_manager = routing_system["context_manager"]
        
        # Create session
        context = context_manager.create_session(user_id="test_user_004")
        
        # Unclear input
        user_input = "xyz abc def"
        
        # Classify
        intent = classifier.classify(user_input, context)
        
        # Should be UNKNOWN with low confidence
        assert intent.intent_type == IntentType.UNKNOWN or intent.confidence < 0.3
        
        # Route - should use fallback
        result = await router.route(intent, context=context)
        
        # Fallback should provide response
        assert result.response is not None
    
    @pytest.mark.asyncio
    async def test_route_priority_selection(self, routing_system):
        """Test priority-based route selection"""
        registry = routing_system["registry"]
        
        # Register multiple routes for same intent type
        async def premium_handler(intent, context):
            return {"tier": "premium"}
        
        async def standard_handler(intent, context):
            return {"tier": "standard"}
        
        registry.register_route(
            Route(
                route_id="premium_loan",
                intent_type=IntentType.LOAN_APPLICATION,
                handler_name="premium_handler",
                priority=1,  # Higher priority
                requires_auth=False,
                min_confidence=0.9
            ),
            premium_handler
        )
        
        registry.register_route(
            Route(
                route_id="standard_loan",
                intent_type=IntentType.LOAN_APPLICATION,
                handler_name="standard_handler",
                priority=2,  # Lower priority
                requires_auth=False,
                min_confidence=0.6
            ),
            standard_handler,
            override=True  # Override existing
        )
        
        # Get routes
        routes = registry.get_routes_for_intent(IntentType.LOAN_APPLICATION)
        
        # Verify priority order
        assert routes[0].priority <= routes[1].priority
    
    @pytest.mark.asyncio
    async def test_metrics_tracking_across_flow(self, routing_system):
        """Test metrics tracking throughout the flow"""
        classifier = routing_system["classifier"]
        router = routing_system["router"]
        registry = routing_system["registry"]
        context_manager = routing_system["context_manager"]
        history_tracker = routing_system["history_tracker"]
        
        # Create session
        context = context_manager.create_session(user_id="test_user_005")
        
        # Execute multiple intents
        test_inputs = [
            "I want a loan",
            "Check my credit",
            "Hello",
            "Apply for business loan",
        ]
        
        for user_input in test_inputs:
            intent = classifier.classify(user_input, context)
            history_tracker.track(intent, user_id="test_user_005")
            result = await router.route(intent, context=context)
        
        # Verify classifier statistics
        clf_stats = classifier.get_statistics()
        assert clf_stats["total_classifications"] >= len(test_inputs)
        
        # Verify route metrics
        route_metrics = registry.get_metrics("loan_application")
        assert route_metrics.total_executions >= 2
        
        # Verify history tracking
        history = history_tracker.get_history(user_id="test_user_005")
        assert len(history) >= len(test_inputs)
        
        # Verify frequency analysis
        frequency = history_tracker.get_frequency(user_id="test_user_005")
        assert IntentType.LOAN_APPLICATION in frequency
    
    @pytest.mark.asyncio
    async def test_session_management_and_cleanup(self, routing_system):
        """Test session creation, management, and cleanup"""
        context_manager = routing_system["context_manager"]
        
        # Create multiple sessions
        context1 = context_manager.create_session(user_id="user_001")
        context2 = context_manager.create_session(user_id="user_002")
        
        # Verify sessions exist
        assert context_manager.get_session(context1.session_id) is not None
        assert context_manager.get_session(context2.session_id) is not None
        
        # Update session
        context_manager.update_session(
            context1.session_id,
            context_data={"test_key": "test_value"}
        )
        
        # Verify update
        data = context_manager.get_context_data(context1.session_id, "test_key")
        assert data == "test_value"
        
        # End session
        context_manager.end_session(context1.session_id)
        
        # Verify ended
        assert context_manager.get_session(context1.session_id) is None
        
        # Session stats
        stats = context_manager.get_statistics()
        assert stats["total_sessions"] >= 1
    
    @pytest.mark.asyncio
    async def test_entity_extraction_across_intents(self, routing_system):
        """Test entity extraction for different intent types"""
        classifier = routing_system["classifier"]
        
        test_cases = [
            {
                "input": "I need a business loan of $75,000",
                "intent_type": IntentType.LOAN_APPLICATION,
                "expected_entities": {"loan_type": "business"},
            },
            {
                "input": "Upload my tax documents",
                "intent_type": IntentType.DOCUMENT_UPLOAD,
                "expected_entities": {"document_type": "tax"},
            },
            {
                "input": "Check collateral for my property",
                "intent_type": IntentType.COLLATERAL_CHECK,
                "expected_entities": {"asset_type": "property"},
            },
        ]
        
        for test_case in test_cases:
            intent = classifier.classify(test_case["input"])
            
            assert intent.intent_type == test_case["intent_type"]
            
            # Verify entity extraction
            for key, expected_value in test_case["expected_entities"].items():
                assert key in intent.entities
                assert expected_value in str(intent.entities[key]).lower()
    
    @pytest.mark.asyncio
    async def test_confidence_threshold_enforcement(self, routing_system):
        """Test that confidence thresholds are enforced"""
        classifier = routing_system["classifier"]
        router = routing_system["router"]
        registry = routing_system["registry"]
        context_manager = routing_system["context_manager"]
        
        # Create high-confidence route
        async def high_confidence_handler(intent, context):
            return {"tier": "high_confidence"}
        
        registry.register_route(
            Route(
                route_id="high_confidence_loan",
                intent_type=IntentType.LOAN_APPLICATION,
                handler_name="high_confidence_handler",
                priority=1,
                requires_auth=False,
                min_confidence=0.95  # Very high threshold
            ),
            high_confidence_handler,
            override=True
        )
        
        # Create session
        context = context_manager.create_session(user_id="test_user_007")
        
        # Medium confidence input
        intent = classifier.classify("maybe loan?", context)
        
        # Should fall back due to low confidence
        result = await router.route(intent, context=context)
        
        # If confidence < 0.95, should use fallback
        if intent.confidence < 0.95:
            assert result.route_id == "fallback" or not result.success
    
    @pytest.mark.asyncio
    async def test_user_pattern_analysis(self, routing_system):
        """Test user behavior pattern analysis"""
        classifier = routing_system["classifier"]
        history_tracker = routing_system["history_tracker"]
        
        user_id = "test_user_008"
        
        # Simulate user behavior
        user_inputs = [
            "Apply for loan",
            "Check credit",
            "Apply for business loan",
            "Apply for auto loan",
            "Check my credit score",
        ]
        
        for user_input in user_inputs:
            intent = classifier.classify(user_input)
            history_tracker.track(intent, user_id=user_id)
        
        # Analyze patterns
        patterns = history_tracker.get_user_patterns(user_id)
        
        assert patterns["total_intents"] == len(user_inputs)
        assert len(patterns["top_intents"]) > 0
        assert patterns["avg_confidence"] > 0
        
        # Most common should be loan application
        top_intent = patterns["top_intents"][0]
        assert top_intent["type"] in ["loan_application", "credit_history"]


class TestCrossComponentIntegration:
    """Tests integrating routing with other system components"""
    
    @pytest.mark.asyncio
    async def test_routing_with_authentication(self, routing_system):
        """Test routing with authentication requirements"""
        registry = routing_system["registry"]
        router = routing_system["router"]
        context_manager = routing_system["context_manager"]
        classifier = routing_system["classifier"]
        
        # Register secure route
        async def secure_handler(intent, context):
            return {"message": "Secure access granted"}
        
        registry.register_route(
            Route(
                route_id="secure_loan",
                intent_type=IntentType.LOAN_APPLICATION,
                handler_name="secure_handler",
                priority=1,
                requires_auth=True,  # Requires authentication
                min_confidence=0.6
            ),
            secure_handler,
            override=True
        )
        
        # Create session
        context = context_manager.create_session(user_id="test_user_009")
        
        # Classify
        intent = classifier.classify("Apply for loan", context)
        
        # Route without auth - should fail or fallback
        result_no_auth = await router.route(
            intent,
            context=context,
            user_authenticated=False
        )
        
        # Route with auth - should succeed
        result_with_auth = await router.route(
            intent,
            context=context,
            user_authenticated=True
        )
        
        # Verify auth enforcement
        if result_no_auth.route_id == "secure_loan":
            # If it routed to secure_loan without auth, that's a problem
            pytest.fail("Authentication requirement not enforced")
        
        assert result_with_auth.success or result_with_auth.route_id == "secure_loan"
    
    @pytest.mark.asyncio
    async def test_routing_with_context_requirements(self, routing_system):
        """Test routing with context requirements"""
        registry = routing_system["registry"]
        router = routing_system["router"]
        context_manager = routing_system["context_manager"]
        classifier = routing_system["classifier"]
        
        # Register route requiring context
        async def context_aware_handler(intent, context):
            return {
                "message": "Context-aware processing",
                "user_profile": context.context_data.get("user_profile")
            }
        
        registry.register_route(
            Route(
                route_id="context_loan",
                intent_type=IntentType.LOAN_APPLICATION,
                handler_name="context_aware_handler",
                priority=1,
                requires_auth=False,
                requires_context=["user_profile"],  # Requires context
                min_confidence=0.6
            ),
            context_aware_handler,
            override=True
        )
        
        # Create session
        context = context_manager.create_session(user_id="test_user_010")
        
        # Classify
        intent = classifier.classify("Apply for loan", context)
        
        # Route without context - should fallback
        result_no_context = await router.route(intent, context=context)
        
        # Add required context
        context_manager.set_context_data(
            context.session_id,
            "user_profile",
            {"name": "Test User", "age": 30}
        )
        
        # Get updated context
        updated_context = context_manager.get_session(context.session_id)
        
        # Route with context - should succeed
        result_with_context = await router.route(intent, context=updated_context)
        
        # Verify context requirement enforcement
        if result_with_context.success and result_with_context.route_id == "context_loan":
            assert result_with_context.response["user_profile"] is not None


class TestPerformanceAndLoad:
    """Performance and load testing"""
    
    @pytest.mark.asyncio
    async def test_classification_performance(self, routing_system):
        """Test classification performance"""
        classifier = routing_system["classifier"]
        
        test_inputs = [
            "Apply for loan",
            "Check credit",
            "Hello",
            "Upload document",
            "Find jobs",
        ] * 20  # 100 classifications
        
        start_time = datetime.utcnow()
        
        for user_input in test_inputs:
            intent = classifier.classify(user_input)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Should complete 100 classifications in < 1 second
        assert duration < 1.0
        
        # Average < 10ms per classification
        avg_time_ms = (duration / len(test_inputs)) * 1000
        assert avg_time_ms < 10
    
    @pytest.mark.asyncio
    async def test_concurrent_routing(self, routing_system):
        """Test concurrent routing operations"""
        classifier = routing_system["classifier"]
        router = routing_system["router"]
        context_manager = routing_system["context_manager"]
        
        # Create multiple sessions
        sessions = [
            context_manager.create_session(user_id=f"concurrent_user_{i}")
            for i in range(10)
        ]
        
        # Concurrent routing
        async def route_user_input(session_id):
            context = context_manager.get_session(session_id)
            intent = classifier.classify("Apply for loan", context)
            result = await router.route(intent, context=context)
            return result
        
        # Execute concurrently
        results = await asyncio.gather(*[
            route_user_input(session.session_id)
            for session in sessions
        ])
        
        # Verify all succeeded
        assert len(results) == 10
        assert all(r.success or r.route_id == "fallback" for r in results)
    
    @pytest.mark.asyncio
    async def test_memory_efficiency_large_history(self, routing_system):
        """Test memory efficiency with large history"""
        history_tracker = routing_system["history_tracker"]
        classifier = routing_system["classifier"]
        
        # Track many intents
        for i in range(1000):
            intent = classifier.classify(f"Test input {i}")
            history_tracker.track(intent, user_id=f"user_{i % 10}")
        
        # Verify tracking works
        assert len(history_tracker.history) <= history_tracker.max_history_size
        
        # Get statistics should work efficiently
        summary = history_tracker.get_summary()
        assert summary["total_intents"] > 0


class TestErrorHandlingAndRecovery:
    """Error handling and recovery tests"""
    
    @pytest.mark.asyncio
    async def test_handler_exception_recovery(self, routing_system):
        """Test graceful handling of handler exceptions"""
        registry = routing_system["registry"]
        router = routing_system["router"]
        context_manager = routing_system["context_manager"]
        classifier = routing_system["classifier"]
        
        # Register handler that raises exception
        async def failing_handler(intent, context):
            raise ValueError("Simulated handler error")
        
        registry.register_route(
            Route(
                route_id="failing_loan",
                intent_type=IntentType.LOAN_APPLICATION,
                handler_name="failing_handler",
                priority=1,
                requires_auth=False,
                min_confidence=0.6
            ),
            failing_handler,
            override=True
        )
        
        # Create session
        context = context_manager.create_session(user_id="test_user_error")
        
        # Classify and route
        intent = classifier.classify("Apply for loan", context)
        result = await router.route(intent, context=context)
        
        # Should handle error gracefully
        assert not result.success
        assert result.error is not None
        assert "error" in result.error.lower() or "simulated" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_invalid_session_handling(self, routing_system):
        """Test handling of invalid sessions"""
        context_manager = routing_system["context_manager"]
        
        # Try to get non-existent session
        context = context_manager.get_session("non_existent_session_id")
        
        # Should return None
        assert context is None
    
    @pytest.mark.asyncio
    async def test_malformed_input_handling(self, routing_system):
        """Test handling of malformed input"""
        classifier = routing_system["classifier"]
        
        malformed_inputs = [
            "",  # Empty
            " " * 100,  # Whitespace
            "🔥" * 50,  # Emojis
            "a" * 1000,  # Very long
        ]
        
        for user_input in malformed_inputs:
            # Should not crash
            intent = classifier.classify(user_input)
            assert intent is not None
            # Should be UNKNOWN for most malformed inputs
            assert intent.intent_type in [IntentType.UNKNOWN, IntentType.GREETING, IntentType.QUESTION]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
