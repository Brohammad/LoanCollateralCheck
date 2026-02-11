"""
Cost calculator for LLM API usage.

Provides accurate cost calculations based on current pricing models.
"""

from datetime import datetime
from typing import Dict, Optional
import uuid

from cost_analysis.models import (
    TokenUsage,
    CostRecord,
    ModelType,
    CostCategory,
)


# Pricing per 1M tokens (as of 2026)
# These are example prices - update with actual pricing
PRICING_PER_MILLION_TOKENS = {
    ModelType.GEMINI_FLASH: {
        "prompt": 0.075,  # $0.075 per 1M input tokens
        "completion": 0.30,  # $0.30 per 1M output tokens
    },
    ModelType.GEMINI_PRO: {
        "prompt": 1.25,  # $1.25 per 1M input tokens
        "completion": 5.00,  # $5.00 per 1M output tokens
    },
    ModelType.GEMINI_ULTRA: {
        "prompt": 5.00,  # $5.00 per 1M input tokens
        "completion": 20.00,  # $20.00 per 1M output tokens
    },
    ModelType.EMBEDDING: {
        "prompt": 0.025,  # $0.025 per 1M tokens
        "completion": 0.0,  # Embeddings don't have completion tokens
    },
}

# Cache discount (tokens served from cache cost less)
CACHE_DISCOUNT = 0.5  # 50% discount for cached tokens


class CostCalculator:
    """
    Calculates costs for LLM operations based on token usage.
    
    Features:
    - Accurate pricing per model
    - Cache cost savings calculation
    - Custom pricing support
    - Currency conversion (future)
    """
    
    def __init__(
        self,
        pricing: Optional[Dict[ModelType, Dict[str, float]]] = None,
        currency: str = "USD",
    ):
        """
        Initialize cost calculator.
        
        Args:
            pricing: Custom pricing table (None for default)
            currency: Currency code
        """
        self.pricing = pricing or PRICING_PER_MILLION_TOKENS
        self.currency = currency
    
    async def calculate_cost(
        self,
        token_usage: TokenUsage,
        category: Optional[CostCategory] = None,
    ) -> CostRecord:
        """
        Calculate cost for token usage.
        
        Args:
            token_usage: Token usage record
            category: Cost category (auto-detected if None)
        
        Returns:
            Cost record with calculated costs
        """
        # Get pricing for model
        model_pricing = self.pricing.get(token_usage.model_type)
        if model_pricing is None:
            raise ValueError(f"No pricing found for model: {token_usage.model_type}")
        
        # Calculate prompt cost
        prompt_cost = self._calculate_token_cost(
            tokens=token_usage.prompt_tokens,
            price_per_million=model_pricing["prompt"],
        )
        
        # Calculate completion cost
        completion_cost = self._calculate_token_cost(
            tokens=token_usage.completion_tokens,
            price_per_million=model_pricing["completion"],
        )
        
        # Calculate cache savings
        cached_cost_savings = 0.0
        if token_usage.cached_tokens > 0:
            cached_cost_savings = self._calculate_token_cost(
                tokens=token_usage.cached_tokens,
                price_per_million=model_pricing["prompt"],
            ) * CACHE_DISCOUNT
        
        # Determine category
        if category is None:
            if token_usage.model_type == ModelType.EMBEDDING:
                category = CostCategory.LLM_EMBEDDING
            else:
                category = CostCategory.LLM_GENERATION
        
        # Create cost record
        cost_record = CostRecord(
            record_id=str(uuid.uuid4()),
            token_usage=token_usage,
            category=category,
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=prompt_cost + completion_cost,
            cached_cost_savings=cached_cost_savings,
            currency=self.currency,
            timestamp=datetime.utcnow(),
            tags={},
        )
        
        return cost_record
    
    def _calculate_token_cost(self, tokens: int, price_per_million: float) -> float:
        """
        Calculate cost for tokens.
        
        Args:
            tokens: Number of tokens
            price_per_million: Price per 1M tokens
        
        Returns:
            Cost in currency
        """
        return (tokens / 1_000_000) * price_per_million
    
    def estimate_cost(
        self,
        model_type: ModelType,
        prompt_tokens: int,
        completion_tokens: int = 0,
    ) -> float:
        """
        Estimate cost without creating records.
        
        Args:
            model_type: Model to use
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
        
        Returns:
            Estimated cost
        """
        model_pricing = self.pricing.get(model_type)
        if model_pricing is None:
            return 0.0
        
        prompt_cost = self._calculate_token_cost(prompt_tokens, model_pricing["prompt"])
        completion_cost = self._calculate_token_cost(completion_tokens, model_pricing["completion"])
        
        return prompt_cost + completion_cost
    
    def get_pricing_info(self, model_type: ModelType) -> Dict[str, float]:
        """
        Get pricing information for a model.
        
        Args:
            model_type: Model type
        
        Returns:
            Dictionary with pricing per 1M tokens
        """
        return self.pricing.get(model_type, {})
    
    def compare_models(
        self,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Dict[ModelType, float]:
        """
        Compare costs across different models.
        
        Args:
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
        
        Returns:
            Dictionary mapping models to costs
        """
        comparison = {}
        
        for model_type in [ModelType.GEMINI_FLASH, ModelType.GEMINI_PRO, ModelType.GEMINI_ULTRA]:
            cost = self.estimate_cost(model_type, prompt_tokens, completion_tokens)
            comparison[model_type] = cost
        
        return comparison
    
    def calculate_monthly_projection(
        self,
        daily_requests: int,
        avg_prompt_tokens: int,
        avg_completion_tokens: int,
        model_type: ModelType,
    ) -> Dict[str, float]:
        """
        Project monthly costs based on usage patterns.
        
        Args:
            daily_requests: Average requests per day
            avg_prompt_tokens: Average prompt tokens per request
            avg_completion_tokens: Average completion tokens per request
            model_type: Model to use
        
        Returns:
            Dictionary with projections
        """
        # Calculate cost per request
        cost_per_request = self.estimate_cost(
            model_type=model_type,
            prompt_tokens=avg_prompt_tokens,
            completion_tokens=avg_completion_tokens,
        )
        
        # Project costs
        daily_cost = cost_per_request * daily_requests
        monthly_cost = daily_cost * 30
        yearly_cost = daily_cost * 365
        
        return {
            "cost_per_request": cost_per_request,
            "daily_cost": daily_cost,
            "monthly_cost": monthly_cost,
            "yearly_cost": yearly_cost,
            "total_daily_tokens": (avg_prompt_tokens + avg_completion_tokens) * daily_requests,
        }
    
    def calculate_break_even(
        self,
        current_model: ModelType,
        alternative_model: ModelType,
        monthly_requests: int,
        avg_prompt_tokens: int,
        avg_completion_tokens: int,
        migration_cost: float = 0.0,
    ) -> Dict[str, any]:
        """
        Calculate break-even analysis for switching models.
        
        Args:
            current_model: Current model
            alternative_model: Alternative model to consider
            monthly_requests: Monthly request volume
            avg_prompt_tokens: Average prompt tokens
            avg_completion_tokens: Average completion tokens
            migration_cost: One-time migration cost
        
        Returns:
            Break-even analysis
        """
        # Calculate costs for both models
        current_cost = self.estimate_cost(current_model, avg_prompt_tokens, avg_completion_tokens)
        alternative_cost = self.estimate_cost(alternative_model, avg_prompt_tokens, avg_completion_tokens)
        
        current_monthly = current_cost * monthly_requests
        alternative_monthly = alternative_cost * monthly_requests
        
        monthly_savings = current_monthly - alternative_monthly
        
        # Calculate break-even
        if monthly_savings <= 0:
            break_even_months = float('inf')
        else:
            break_even_months = migration_cost / monthly_savings
        
        return {
            "current_model": current_model.value,
            "current_monthly_cost": current_monthly,
            "alternative_model": alternative_model.value,
            "alternative_monthly_cost": alternative_monthly,
            "monthly_savings": monthly_savings,
            "yearly_savings": monthly_savings * 12,
            "migration_cost": migration_cost,
            "break_even_months": break_even_months,
            "recommendation": (
                f"Switch to {alternative_model.value}"
                if monthly_savings > 0 and break_even_months < 6
                else f"Keep {current_model.value}"
            ),
        }
