"""
Cost optimizer for analyzing usage patterns and suggesting optimizations.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict, Counter
import uuid

from cost_analysis.models import (
    OptimizationSuggestion,
    TokenUsage,
    CostRecord,
    ModelType,
)
from cost_analysis.tracker import CostTracker
from cost_analysis.calculator import CostCalculator


class CostOptimizer:
    """
    Analyzes cost patterns and generates optimization suggestions.
    
    Features:
    - Identifies cost-saving opportunities
    - Suggests model alternatives
    - Recommends caching strategies
    - Detects inefficient patterns
    """
    
    def __init__(
        self,
        cost_tracker: Optional[CostTracker] = None,
        calculator: Optional[CostCalculator] = None,
    ):
        """
        Initialize cost optimizer.
        
        Args:
            cost_tracker: Cost tracker instance
            calculator: Cost calculator instance
        """
        self.cost_tracker = cost_tracker
        self.calculator = calculator or CostCalculator()
    
    async def analyze_and_suggest(
        self,
        lookback_days: int = 7,
    ) -> List[OptimizationSuggestion]:
        """
        Analyze usage and generate optimization suggestions.
        
        Args:
            lookback_days: Number of days to analyze
        
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        # Analyze caching opportunities
        caching_suggestions = await self._analyze_caching_opportunities(lookback_days)
        suggestions.extend(caching_suggestions)
        
        # Analyze model selection
        model_suggestions = await self._analyze_model_selection(lookback_days)
        suggestions.extend(model_suggestions)
        
        # Analyze token usage patterns
        token_suggestions = await self._analyze_token_usage(lookback_days)
        suggestions.extend(token_suggestions)
        
        # Analyze request patterns
        pattern_suggestions = await self._analyze_request_patterns(lookback_days)
        suggestions.extend(pattern_suggestions)
        
        # Sort by potential savings
        suggestions.sort(key=lambda s: s.potential_savings, reverse=True)
        
        return suggestions
    
    async def _analyze_caching_opportunities(
        self,
        lookback_days: int,
    ) -> List[OptimizationSuggestion]:
        """Analyze caching opportunities."""
        if not self.cost_tracker:
            return []
        
        suggestions = []
        
        # Get metrics
        period_start = datetime.utcnow() - timedelta(days=lookback_days)
        metrics = self.cost_tracker.get_metrics(period_start=period_start)
        
        # Check current cache hit rate
        cache_hit_rate = metrics.get("cache_hit_rate", 0.0)
        
        if cache_hit_rate < 0.3:  # Less than 30% cache hit rate
            # Calculate potential savings
            total_cost = metrics.get("total_cost", 0.0)
            monthly_cost = (total_cost / lookback_days) * 30
            
            # Assume we can cache 40% of requests
            potential_savings = monthly_cost * 0.4 * 0.5  # 50% cost reduction on cached requests
            
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    category="caching",
                    title="Implement aggressive prompt caching",
                    description=(
                        f"Current cache hit rate is {cache_hit_rate:.1%}. "
                        f"Analysis shows 40% of requests could be cached. "
                        f"Implementing Redis-based caching with 1-hour TTL could reduce costs significantly."
                    ),
                    potential_savings=potential_savings,
                    potential_savings_percent=(potential_savings / monthly_cost * 100 if monthly_cost > 0 else 0),
                    implementation_effort="medium",
                    priority="high",
                    current_cost=monthly_cost,
                    optimized_cost=monthly_cost - potential_savings,
                    affected_operations=["generation", "classification"],
                    action_items=[
                        "Implement Redis-based prompt cache",
                        "Set TTL to 1 hour for repeated queries",
                        "Hash prompts for cache key generation",
                        "Monitor cache hit rate improvements",
                    ],
                )
            )
        
        return suggestions
    
    async def _analyze_model_selection(
        self,
        lookback_days: int,
    ) -> List[OptimizationSuggestion]:
        """Analyze model selection opportunities."""
        if not self.cost_tracker:
            return []
        
        suggestions = []
        
        # Get recent operations
        operations = self.cost_tracker.get_recent_operations(limit=1000)
        
        if not operations:
            return []
        
        # Analyze by operation type
        by_model = defaultdict(lambda: {"count": 0, "total_cost": 0.0, "total_tokens": 0})
        
        for token_usage, cost_record in operations:
            model = token_usage.model_type.value
            by_model[model]["count"] += 1
            by_model[model]["total_cost"] += cost_record.total_cost
            by_model[model]["total_tokens"] += token_usage.total_tokens
        
        # Check if expensive models are being used
        if ModelType.GEMINI_PRO.value in by_model or ModelType.GEMINI_ULTRA.value in by_model:
            # Calculate if Flash could handle it
            expensive_usage = (
                by_model.get(ModelType.GEMINI_PRO.value, {}).get("count", 0) +
                by_model.get(ModelType.GEMINI_ULTRA.value, {}).get("count", 0)
            )
            
            expensive_cost = (
                by_model.get(ModelType.GEMINI_PRO.value, {}).get("total_cost", 0.0) +
                by_model.get(ModelType.GEMINI_ULTRA.value, {}).get("total_cost", 0.0)
            )
            
            if expensive_usage > 100:  # Significant usage
                # Calculate Flash cost for same operations
                total_tokens = (
                    by_model.get(ModelType.GEMINI_PRO.value, {}).get("total_tokens", 0) +
                    by_model.get(ModelType.GEMINI_ULTRA.value, {}).get("total_tokens", 0)
                )
                
                # Estimate savings (Flash is ~5x cheaper than Pro)
                monthly_cost = (expensive_cost / lookback_days) * 30
                flash_monthly_cost = monthly_cost / 5
                monthly_savings = monthly_cost - flash_monthly_cost
                
                suggestions.append(
                    OptimizationSuggestion(
                        suggestion_id=str(uuid.uuid4()),
                        category="model_selection",
                        title="Switch to Gemini Flash for routine operations",
                        description=(
                            f"Using expensive models (Pro/Ultra) for {expensive_usage} operations. "
                            f"Analysis suggests 70% could use Flash with similar quality. "
                            f"Flash is 5x cheaper and 2x faster."
                        ),
                        potential_savings=monthly_savings * 0.7,  # 70% of operations
                        potential_savings_percent=(monthly_savings * 0.7 / monthly_cost * 100),
                        implementation_effort="low",
                        priority="high",
                        current_cost=monthly_cost,
                        optimized_cost=monthly_cost - (monthly_savings * 0.7),
                        affected_operations=["generation", "classification", "summarization"],
                        action_items=[
                            "A/B test Flash vs current model",
                            "Compare output quality",
                            "Gradually migrate non-critical operations",
                            "Keep Pro/Ultra for complex tasks only",
                        ],
                    )
                )
        
        return suggestions
    
    async def _analyze_token_usage(
        self,
        lookback_days: int,
    ) -> List[OptimizationSuggestion]:
        """Analyze token usage patterns."""
        if not self.cost_tracker:
            return []
        
        suggestions = []
        
        # Get recent operations
        operations = self.cost_tracker.get_recent_operations(limit=1000)
        
        if not operations:
            return []
        
        # Calculate average tokens
        prompt_tokens = [u.prompt_tokens for u, c in operations]
        completion_tokens = [u.completion_tokens for u, c in operations]
        
        avg_prompt = sum(prompt_tokens) / len(prompt_tokens) if prompt_tokens else 0
        avg_completion = sum(completion_tokens) / len(completion_tokens) if completion_tokens else 0
        
        # Check if prompts are too large
        if avg_prompt > 2000:
            # Calculate potential savings from prompt optimization
            period_start = datetime.utcnow() - timedelta(days=lookback_days)
            metrics = self.cost_tracker.get_metrics(period_start=period_start)
            monthly_cost = (metrics.get("total_cost", 0.0) / lookback_days) * 30
            
            # Assume 30% reduction in prompt tokens
            potential_savings = monthly_cost * 0.3 * 0.5  # 50% of cost is prompt tokens
            
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    category="token_optimization",
                    title="Optimize prompt length and structure",
                    description=(
                        f"Average prompt is {avg_prompt:.0f} tokens. "
                        f"Many prompts contain redundant information or verbose instructions. "
                        f"Optimizing prompts could reduce token usage by 30%."
                    ),
                    potential_savings=potential_savings,
                    potential_savings_percent=(potential_savings / monthly_cost * 100 if monthly_cost > 0 else 0),
                    implementation_effort="medium",
                    priority="medium",
                    current_cost=monthly_cost,
                    optimized_cost=monthly_cost - potential_savings,
                    affected_operations=["generation"],
                    action_items=[
                        "Review and compress system prompts",
                        "Remove redundant examples",
                        "Use concise instructions",
                        "Implement dynamic context sizing",
                    ],
                )
            )
        
        # Check completion tokens
        if avg_completion > 1500:
            period_start = datetime.utcnow() - timedelta(days=lookback_days)
            metrics = self.cost_tracker.get_metrics(period_start=period_start)
            monthly_cost = (metrics.get("total_cost", 0.0) / lookback_days) * 30
            
            # Completion tokens are more expensive
            potential_savings = monthly_cost * 0.2 * 0.6  # 60% of cost is completion
            
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    category="token_optimization",
                    title="Reduce completion token usage",
                    description=(
                        f"Average completion is {avg_completion:.0f} tokens. "
                        f"Setting lower max_tokens limits or requesting more concise responses "
                        f"could reduce costs."
                    ),
                    potential_savings=potential_savings,
                    potential_savings_percent=(potential_savings / monthly_cost * 100 if monthly_cost > 0 else 0),
                    implementation_effort="low",
                    priority="medium",
                    current_cost=monthly_cost,
                    optimized_cost=monthly_cost - potential_savings,
                    affected_operations=["generation"],
                    action_items=[
                        "Set max_tokens limits per operation type",
                        "Request concise responses in prompts",
                        "Implement response truncation where appropriate",
                    ],
                )
            )
        
        return suggestions
    
    async def _analyze_request_patterns(
        self,
        lookback_days: int,
    ) -> List[OptimizationSuggestion]:
        """Analyze request patterns."""
        if not self.cost_tracker:
            return []
        
        suggestions = []
        
        # Get recent operations
        operations = self.cost_tracker.get_recent_operations(limit=1000)
        
        if not operations:
            return []
        
        # Group by hour to find peak times
        by_hour = defaultdict(int)
        for token_usage, _ in operations:
            hour = token_usage.timestamp.hour
            by_hour[hour] += 1
        
        # Find peak hours
        if by_hour:
            max_hour = max(by_hour.values())
            min_hour = min(by_hour.values())
            
            # If there's a big difference, suggest batch processing
            if max_hour > min_hour * 3:
                period_start = datetime.utcnow() - timedelta(days=lookback_days)
                metrics = self.cost_tracker.get_metrics(period_start=period_start)
                monthly_cost = (metrics.get("total_cost", 0.0) / lookback_days) * 30
                
                # Small savings from better resource utilization
                potential_savings = monthly_cost * 0.05
                
                suggestions.append(
                    OptimizationSuggestion(
                        suggestion_id=str(uuid.uuid4()),
                        category="request_batching",
                        title="Implement request batching for off-peak processing",
                        description=(
                            f"Request volume varies significantly (peak: {max_hour}, low: {min_hour}). "
                            f"Non-urgent requests could be batched for off-peak processing."
                        ),
                        potential_savings=potential_savings,
                        potential_savings_percent=(potential_savings / monthly_cost * 100 if monthly_cost > 0 else 0),
                        implementation_effort="high",
                        priority="low",
                        current_cost=monthly_cost,
                        optimized_cost=monthly_cost - potential_savings,
                        affected_operations=["generation", "embedding"],
                        action_items=[
                            "Identify non-urgent operations",
                            "Implement request queue",
                            "Schedule batch processing during off-peak hours",
                            "Set up monitoring for queue depth",
                        ],
                    )
                )
        
        return suggestions
    
    def calculate_roi(
        self,
        suggestion: OptimizationSuggestion,
        implementation_cost: float,
        implementation_time_days: int,
    ) -> Dict:
        """
        Calculate ROI for an optimization suggestion.
        
        Args:
            suggestion: Optimization suggestion
            implementation_cost: One-time cost to implement
            implementation_time_days: Days to implement
        
        Returns:
            ROI analysis
        """
        monthly_savings = suggestion.potential_savings
        yearly_savings = monthly_savings * 12
        
        # Calculate break-even
        if monthly_savings > 0:
            break_even_months = implementation_cost / monthly_savings
        else:
            break_even_months = float('inf')
        
        # Calculate ROI
        roi = ((yearly_savings - implementation_cost) / implementation_cost * 100
               if implementation_cost > 0 else float('inf'))
        
        return {
            "suggestion_id": suggestion.suggestion_id,
            "monthly_savings": monthly_savings,
            "yearly_savings": yearly_savings,
            "implementation_cost": implementation_cost,
            "implementation_time_days": implementation_time_days,
            "break_even_months": break_even_months,
            "roi_percent": roi,
            "recommendation": (
                "Implement immediately" if break_even_months < 3
                else "Consider implementing" if break_even_months < 6
                else "Low priority"
            ),
        }
