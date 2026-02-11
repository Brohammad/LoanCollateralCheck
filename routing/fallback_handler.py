"""
Fallback Handler

Handles low-confidence intents and routing failures with multiple strategies.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from routing.models import (
    Intent,
    IntentContext,
    FallbackResult,
    FallbackStrategy,
    IntentType,
    IntentConfidence,
)

logger = logging.getLogger(__name__)


class FallbackHandler:
    """
    Handles unclear intents and routing failures
    
    Features:
    - Multiple fallback strategies
    - Strategy selection based on context
    - Clarification generation
    - Default responses
    - History-based inference
    - Human escalation
    """
    
    def __init__(
        self,
        default_strategy: FallbackStrategy = FallbackStrategy.ASK_CLARIFICATION,
        enable_history_fallback: bool = True,
        enable_escalation: bool = True
    ):
        """
        Initialize fallback handler
        
        Args:
            default_strategy: Default fallback strategy
            enable_history_fallback: Whether to use history fallback
            enable_escalation: Whether to enable human escalation
        """
        self.default_strategy = default_strategy
        self.enable_history_fallback = enable_history_fallback
        self.enable_escalation = enable_escalation
        
        # Default responses by intent type
        self.default_responses = {
            IntentType.GREETING: "Hello! How can I help you today?",
            IntentType.QUESTION: "I'm not sure I understand your question. Could you rephrase it?",
            IntentType.COMMAND: "I'm not sure what you want me to do. Could you be more specific?",
            IntentType.HELP: "I'm here to help! What do you need assistance with?",
            IntentType.UNKNOWN: "I'm not sure how to help with that. Could you try asking in a different way?",
        }
    
    async def handle(
        self,
        intent: Intent,
        context: Optional[IntentContext] = None
    ) -> FallbackResult:
        """
        Handle unclear intent with fallback strategy
        
        Args:
            intent: Intent that couldn't be routed
            context: Optional session context
        
        Returns:
            FallbackResult with strategy and response
        """
        # Select strategy
        strategy = self._select_strategy(intent, context)
        
        # Execute strategy
        if strategy == FallbackStrategy.ASK_CLARIFICATION:
            return await self._ask_clarification(intent, context)
        
        elif strategy == FallbackStrategy.USE_DEFAULT:
            return await self._use_default(intent, context)
        
        elif strategy == FallbackStrategy.USE_HISTORY:
            return await self._use_history(intent, context)
        
        elif strategy == FallbackStrategy.ESCALATE_TO_HUMAN:
            return await self._escalate_to_human(intent, context)
        
        elif strategy == FallbackStrategy.PROVIDE_OPTIONS:
            return await self._provide_options(intent, context)
        
        else:
            logger.warning(f"Unknown strategy: {strategy}")
            return await self._use_default(intent, context)
    
    def _select_strategy(
        self,
        intent: Intent,
        context: Optional[IntentContext]
    ) -> FallbackStrategy:
        """
        Select appropriate fallback strategy
        
        Args:
            intent: Intent that couldn't be routed
            context: Optional session context
        
        Returns:
            Selected FallbackStrategy
        """
        # Very low confidence - ask clarification
        if intent.confidence_level == IntentConfidence.VERY_LOW:
            return FallbackStrategy.ASK_CLARIFICATION
        
        # Unknown intent - provide options
        if intent.intent_type == IntentType.UNKNOWN:
            return FallbackStrategy.PROVIDE_OPTIONS
        
        # Has context and history enabled - try history
        if context and self.enable_history_fallback:
            if len(context.conversation_history) > 0:
                return FallbackStrategy.USE_HISTORY
        
        # Multiple failed attempts - escalate
        if context and self.enable_escalation:
            recent_intents = context.get_recent_intents(n=5)
            failed_count = sum(
                1 for i in recent_intents
                if i.confidence_level in [IntentConfidence.LOW, IntentConfidence.VERY_LOW]
            )
            if failed_count >= 3:
                return FallbackStrategy.ESCALATE_TO_HUMAN
        
        # Default strategy
        return self.default_strategy
    
    async def _ask_clarification(
        self,
        intent: Intent,
        context: Optional[IntentContext]
    ) -> FallbackResult:
        """
        Ask user for clarification
        
        Args:
            intent: Intent that needs clarification
            context: Optional session context
        
        Returns:
            FallbackResult with clarification request
        """
        # Generate clarification questions
        clarifications = []
        
        if intent.intent_type == IntentType.LOAN_APPLICATION:
            clarifications = [
                "What type of loan are you interested in? (business, personal, auto, home)",
                "How much would you like to borrow?",
                "What is the purpose of this loan?",
            ]
        
        elif intent.intent_type == IntentType.COLLATERAL_CHECK:
            clarifications = [
                "What type of asset would you like to use as collateral? (property, vehicle, equipment)",
                "Do you have the asset information ready?",
            ]
        
        elif intent.intent_type == IntentType.CREDIT_HISTORY:
            clarifications = [
                "Would you like to check your credit score?",
                "Would you like to see your credit report?",
                "Are you looking for ways to improve your credit?",
            ]
        
        elif intent.intent_type == IntentType.DOCUMENT_UPLOAD:
            clarifications = [
                "What type of document would you like to upload? (tax return, bank statement, ID, etc.)",
                "Is this for a loan application or another purpose?",
            ]
        
        elif intent.intent_type == IntentType.PROFILE_ANALYSIS:
            clarifications = [
                "Would you like me to analyze your LinkedIn profile?",
                "Are you looking for profile improvement suggestions?",
            ]
        
        elif intent.intent_type == IntentType.JOB_MATCHING:
            clarifications = [
                "What type of job are you looking for?",
                "Would you like job recommendations based on your profile?",
            ]
        
        else:
            # Generic clarification
            clarifications = [
                "Could you please provide more details?",
                "I'm not sure I understand. Could you rephrase that?",
                "What specifically would you like help with?",
            ]
        
        response = "I need a bit more information to help you. " + clarifications[0]
        
        return FallbackResult(
            strategy_used=FallbackStrategy.ASK_CLARIFICATION,
            intent=intent,
            handled=True,
            response=response,
            clarification_options=clarifications
        )
    
    async def _use_default(
        self,
        intent: Intent,
        context: Optional[IntentContext]
    ) -> FallbackResult:
        """
        Use default response
        
        Args:
            intent: Intent to handle
            context: Optional session context
        
        Returns:
            FallbackResult with default response
        """
        response = self.default_responses.get(
            intent.intent_type,
            "I'm not sure how to help with that. Could you try asking in a different way?"
        )
        
        return FallbackResult(
            strategy_used=FallbackStrategy.USE_DEFAULT,
            intent=intent,
            handled=True,
            response=response
        )
    
    async def _use_history(
        self,
        intent: Intent,
        context: Optional[IntentContext]
    ) -> FallbackResult:
        """
        Use conversation history to infer intent
        
        Args:
            intent: Intent to handle
            context: Session context with history
        
        Returns:
            FallbackResult with history-based response
        """
        if not context or not context.conversation_history:
            # Fall back to default
            return await self._use_default(intent, context)
        
        # Get recent intents
        recent = context.get_recent_intents(n=3)
        
        # Find most common recent intent type
        intent_counts = {}
        for i in recent:
            intent_counts[i.intent_type] = intent_counts.get(i.intent_type, 0) + 1
        
        if intent_counts:
            most_common = max(intent_counts.items(), key=lambda x: x[1])[0]
            
            response = f"Based on our conversation, I think you're asking about {most_common.value}. Is that correct?"
            
            return FallbackResult(
                strategy_used=FallbackStrategy.USE_HISTORY,
                intent=intent,
                handled=True,
                response=response,
                suggested_actions=[
                    f"Continue with {most_common.value}",
                    "Try a different topic",
                ]
            )
        
        # Fall back to default
        return await self._use_default(intent, context)
    
    async def _escalate_to_human(
        self,
        intent: Intent,
        context: Optional[IntentContext]
    ) -> FallbackResult:
        """
        Escalate to human agent
        
        Args:
            intent: Intent to escalate
            context: Optional session context
        
        Returns:
            FallbackResult with escalation message
        """
        response = (
            "I'm having trouble understanding your request. "
            "Let me connect you with a human agent who can better assist you. "
            "Please wait a moment..."
        )
        
        return FallbackResult(
            strategy_used=FallbackStrategy.ESCALATE_TO_HUMAN,
            intent=intent,
            handled=True,
            response=response,
            suggested_actions=[
                "Wait for human agent",
                "Try rephrasing your request",
            ]
        )
    
    async def _provide_options(
        self,
        intent: Intent,
        context: Optional[IntentContext]
    ) -> FallbackResult:
        """
        Provide multiple options for user
        
        Args:
            intent: Intent to handle
            context: Optional session context
        
        Returns:
            FallbackResult with options
        """
        # Common options
        options = [
            "Apply for a loan",
            "Check collateral requirements",
            "View credit history",
            "Upload documents",
            "Analyze LinkedIn profile",
            "Find job matches",
            "Get skill recommendations",
            "Get help",
            "Check application status",
        ]
        
        response = "I'm not sure what you need. Here are some things I can help with:"
        
        return FallbackResult(
            strategy_used=FallbackStrategy.PROVIDE_OPTIONS,
            intent=intent,
            handled=True,
            response=response,
            suggested_actions=options
        )
    
    def set_default_response(self, intent_type: IntentType, response: str):
        """
        Set custom default response for intent type
        
        Args:
            intent_type: Intent type
            response: Default response
        """
        self.default_responses[intent_type] = response
    
    def get_default_response(self, intent_type: IntentType) -> Optional[str]:
        """
        Get default response for intent type
        
        Args:
            intent_type: Intent type
        
        Returns:
            Default response or None
        """
        return self.default_responses.get(intent_type)
