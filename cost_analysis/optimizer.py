"""
Cost optimization recommendations
"""

import uuid
from typing import List, Dict, Optional
from datetime import datetime

from cost_analysis.models import (
    OptimizationRecommendation,
    OptimizationType,
    ModelType,
    CostRecord,
)
from cost_analysis.calculator import CostCalculator


class CostOptimizer:
    """
    Analyzes usage patterns and generates cost optimization recommendations.
    """
    
    def __init__(self):
        """Initialize cost optimizer"""
        self.calculator = CostCalculator()
    
    def analyze_and_recommend(
        self,
        usage_records: List[CostRecord],
    ) -> List[OptimizationRecommendation]:
        """
        Analyze usage and generate recommendations.
        
        Args:
            usage_records: List of cost records to analyze
        
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        # Model selection optimization
        model_rec = self._recommend_model_optimization(usage_records)
        if model_rec:
            recommendations.extend(model_rec)
        
        # Prompt optimization
        prompt_rec = self._recommend_prompt_optimization(usage_records)
        if prompt_rec:
            recommendations.append(prompt_rec)
        
        # Caching opportunities
        cache_rec = self._recommend_caching(usage_records)
        if cache_rec:
            recommendations.append(cache_rec)
        
        # Batch processing
        batch_rec = self._recommend_batch_processing(usage_records)
        if batch_rec:
            recommendations.append(batch_rec)
        
        # Rate limiting
        rate_rec = self._recommend_rate_limiting(usage_records)
        if rate_rec:
            recommendations.append(rate_rec)
        
        # Context management
        context_rec = self._recommend_context_management(usage_records)
        if context_rec:
            recommendations.append(context_rec)
        
        # Sort by priority and estimated savings
        recommendations.sort(
            key=lambda x: (x.priority, -x.estimated_savings)
        )
        
        return recommendations
    
    def _recommend_model_optimization(
        self,
        usage_records: List[CostRecord],
    ) -> List[OptimizationRecommendation]:
        """Recommend switching to more cost-effective models"""
        recommendations = []
        
        # Group by current model
        model_usage = {}
        for record in usage_records:
            model = record.usage.model
            if model not in model_usage:
                model_usage[model] = []
            model_usage[model].append(record)
        
        # Check each model for optimization opportunities
        for current_model, records in model_usage.items():
            if current_model == ModelType.GEMINI_2_FLASH:
                continue  # Already using the cheapest
            
            # Calculate savings if switching to cheaper model
            alternative_model = ModelType.GEMINI_15_FLASH
            if current_model == ModelType.GEMINI_15_FLASH:
                continue  # Already at this tier
            
            savings_analysis = self.calculator.calculate_savings_opportunity(
                current_model=current_model,
                current_usage=records,
                alternative_model=alternative_model,
            )
            
            if savings_analysis["savings"] > 0:
                monthly_savings = (savings_analysis["savings"] / len(records)) * 30 * len(records)
                
                recommendation = OptimizationRecommendation(
                    id=str(uuid.uuid4()),
                    type=OptimizationType.MODEL_SELECTION,
                    title=f"Switch from {current_model.value} to {alternative_model.value}",
                    description=f"Switching to {alternative_model.value} could reduce costs while maintaining quality for most use cases.",
                    estimated_savings=monthly_savings,
                    estimated_savings_percentage=savings_analysis["savings_percentage"],
                    priority=1 if savings_analysis["savings_percentage"] > 20 else 2,
                    effort="low",
                    current_state=f"Using {current_model.value} for {len(records)} requests",
                    recommended_state=f"Use {alternative_model.value} for cost-sensitive operations",
                    implementation_steps=[
                        f"Identify non-critical operations using {current_model.value}",
                        f"Update configuration to use {alternative_model.value} for those operations",
                        "Monitor quality metrics to ensure no degradation",
                        "Gradually migrate more operations if quality is maintained",
                    ],
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    def _recommend_prompt_optimization(
        self,
        usage_records: List[CostRecord],
    ) -> Optional[OptimizationRecommendation]:
        """Recommend optimizing prompts to reduce token usage"""
        if not usage_records:
            return None
        
        # Calculate average token usage
        avg_input_tokens = sum(r.usage.input_tokens for r in usage_records) / len(usage_records)
        avg_output_tokens = sum(r.usage.output_tokens for r in usage_records) / len(usage_records)
        
        # If average is high, recommend optimization
        if avg_input_tokens > 2000 or avg_output_tokens > 1000:
            # Estimate 20% reduction with prompt optimization
            potential_reduction = 0.20
            current_cost = sum(r.total_cost for r in usage_records)
            estimated_savings = current_cost * potential_reduction * 30  # Monthly
            
            return OptimizationRecommendation(
                id=str(uuid.uuid4()),
                type=OptimizationType.PROMPT_OPTIMIZATION,
                title="Optimize prompts to reduce token usage",
                description="Long prompts are increasing costs. Optimizing prompt structure and content can reduce token usage without sacrificing quality.",
                estimated_savings=estimated_savings,
                estimated_savings_percentage=potential_reduction * 100,
                priority=2,
                effort="medium",
                current_state=f"Average {avg_input_tokens:.0f} input tokens, {avg_output_tokens:.0f} output tokens per request",
                recommended_state="Reduce token usage by 20% through prompt optimization",
                implementation_steps=[
                    "Review existing prompts for redundancy and verbosity",
                    "Use concise instructions and examples",
                    "Remove unnecessary context",
                    "Use system messages effectively",
                    "Implement prompt templates",
                    "A/B test optimized prompts",
                ],
            )
        
        return None
    
    def _recommend_caching(
        self,
        usage_records: List[CostRecord],
    ) -> Optional[OptimizationRecommendation]:
        """Recommend implementing caching for repeated queries"""
        # Check for similar/repeated requests
        # This is a simplified check - in production, use more sophisticated similarity detection
        
        if len(usage_records) < 100:
            return None
        
        # Estimate 30% of requests could be cached
        cache_hit_rate = 0.30
        current_cost = sum(r.total_cost for r in usage_records)
        estimated_savings = current_cost * cache_hit_rate * 30  # Monthly
        
        return OptimizationRecommendation(
            id=str(uuid.uuid4()),
            type=OptimizationType.CACHING,
            title="Implement response caching",
            description="Many requests are similar or repeated. Implementing caching can significantly reduce API calls.",
            estimated_savings=estimated_savings,
            estimated_savings_percentage=cache_hit_rate * 100,
            priority=1,
            effort="medium",
            current_state="No caching implemented for LLM responses",
            recommended_state=f"Cache responses with {cache_hit_rate*100:.0f}% hit rate",
            implementation_steps=[
                "Implement Redis-based response cache",
                "Use content hashing for cache keys",
                "Set appropriate TTL (e.g., 1 hour for dynamic content)",
                "Implement cache warming for common queries",
                "Monitor cache hit rate and adjust strategy",
            ],
        )
    
    def _recommend_batch_processing(
        self,
        usage_records: List[CostRecord],
    ) -> Optional[OptimizationRecommendation]:
        """Recommend batch processing for similar requests"""
        # Check request frequency
        if len(usage_records) < 1000:
            return None
        
        # Estimate 15% savings with batch processing
        batch_savings = 0.15
        current_cost = sum(r.total_cost for r in usage_records)
        estimated_savings = current_cost * batch_savings * 30  # Monthly
        
        return OptimizationRecommendation(
            id=str(uuid.uuid4()),
            type=OptimizationType.BATCH_PROCESSING,
            title="Implement batch processing",
            description="High request volume detected. Batching similar requests can reduce overhead and costs.",
            estimated_savings=estimated_savings,
            estimated_savings_percentage=batch_savings * 100,
            priority=3,
            effort="high",
            current_state="Processing requests individually",
            recommended_state="Batch similar requests together",
            implementation_steps=[
                "Identify request patterns that can be batched",
                "Implement request queue with batching logic",
                "Set optimal batch size (e.g., 10-20 requests)",
                "Add batch timeout (e.g., 1 second)",
                "Handle batch failures gracefully",
            ],
        )
    
    def _recommend_rate_limiting(
        self,
        usage_records: List[CostRecord],
    ) -> Optional[OptimizationRecommendation]:
        """Recommend rate limiting to control costs"""
        # Check for usage spikes
        # Group by hour
        hourly_usage = {}
        for record in usage_records:
            hour = record.usage.timestamp.replace(minute=0, second=0, microsecond=0)
            if hour not in hourly_usage:
                hourly_usage[hour] = 0
            hourly_usage[hour] += record.total_cost
        
        if not hourly_usage:
            return None
        
        avg_hourly = sum(hourly_usage.values()) / len(hourly_usage)
        max_hourly = max(hourly_usage.values())
        
        # If max is more than 3x average, recommend rate limiting
        if max_hourly > avg_hourly * 3:
            # Estimate 10% savings by preventing spikes
            spike_savings = 0.10
            current_cost = sum(r.total_cost for r in usage_records)
            estimated_savings = current_cost * spike_savings * 30  # Monthly
            
            return OptimizationRecommendation(
                id=str(uuid.uuid4()),
                type=OptimizationType.RATE_LIMITING,
                title="Implement intelligent rate limiting",
                description="Usage spikes detected. Rate limiting can prevent cost spikes and encourage efficient usage.",
                estimated_savings=estimated_savings,
                estimated_savings_percentage=spike_savings * 100,
                priority=2,
                effort="low",
                current_state=f"No rate limiting. Max hourly cost: ${max_hourly:.2f}, Avg: ${avg_hourly:.2f}",
                recommended_state="Implement user-level and global rate limits",
                implementation_steps=[
                    "Define rate limits per user and globally",
                    "Implement sliding window rate limiter",
                    "Add informative error messages for rate-limited requests",
                    "Provide usage quotas in API responses",
                    "Monitor rate limit violations",
                ],
            )
        
        return None
    
    def _recommend_context_management(
        self,
        usage_records: List[CostRecord],
    ) -> Optional[OptimizationRecommendation]:
        """Recommend better context window management"""
        if not usage_records:
            return None
        
        # Check for very long inputs
        long_input_records = [r for r in usage_records if r.usage.input_tokens > 4000]
        
        if len(long_input_records) > len(usage_records) * 0.1:  # More than 10%
            # Estimate 25% savings on long requests
            context_savings = 0.25
            long_input_cost = sum(r.total_cost for r in long_input_records)
            estimated_savings = long_input_cost * context_savings * 30  # Monthly
            
            return OptimizationRecommendation(
                id=str(uuid.uuid4()),
                type=OptimizationType.CONTEXT_MANAGEMENT,
                title="Optimize context window usage",
                description="Many requests use very long context windows. Better context management can reduce token usage significantly.",
                estimated_savings=estimated_savings,
                estimated_savings_percentage=context_savings * 100,
                priority=2,
                effort="medium",
                current_state=f"{len(long_input_records)} requests with >4000 input tokens",
                recommended_state="Implement smart context pruning and summarization",
                implementation_steps=[
                    "Implement context window size limits",
                    "Add context summarization for long conversations",
                    "Prune irrelevant context",
                    "Use sliding window for conversation history",
                    "Implement semantic search for relevant context",
                ],
            )
        
        return None
