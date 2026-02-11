"""
Cost calculator for estimating and analyzing costs
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta

from cost_analysis.models import ModelType, TokenUsage, CostRecord
from cost_analysis.pricing import (
    calculate_cost,
    estimate_monthly_cost,
    PRICING,
    USAGE_ESTIMATES,
)


class PricingModel:
    """
    Pricing model for cost calculations.
    """
    
    def __init__(self):
        """Initialize pricing model"""
        self.pricing = PRICING
    
    def get_price_per_1k_tokens(
        self,
        model: ModelType,
        token_type: str = "input"
    ) -> float:
        """
        Get price per 1K tokens for a model.
        
        Args:
            model: Model type
            token_type: "input" or "output"
        
        Returns:
            Price per 1K tokens in USD
        """
        pricing = self.pricing.get(model, self.pricing[ModelType.GEMINI_2_FLASH])
        return pricing.get(f"{token_type}_per_1k", 0.0)
    
    def calculate_request_cost(
        self,
        model: ModelType,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Calculate cost for a single request.
        
        Args:
            model: Model type
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        
        Returns:
            Total cost in USD
        """
        cost_data = calculate_cost(model, input_tokens, output_tokens)
        return cost_data["total_cost"]
    
    def estimate_cost_for_pattern(
        self,
        model: ModelType,
        pattern_name: str = "medium"
    ) -> Dict:
        """
        Estimate monthly cost for a usage pattern.
        
        Args:
            model: Model type
            pattern_name: Usage pattern name (light/medium/heavy/enterprise)
        
        Returns:
            Dictionary with cost estimates
        """
        pattern = USAGE_ESTIMATES.get(pattern_name, USAGE_ESTIMATES["medium"])
        
        return estimate_monthly_cost(
            model=model,
            requests_per_day=pattern["requests_per_day"],
            avg_input_tokens=pattern["avg_input_tokens"],
            avg_output_tokens=pattern["avg_output_tokens"],
        )
    
    def compare_model_costs(
        self,
        input_tokens: int,
        output_tokens: int,
        models: Optional[List[ModelType]] = None,
    ) -> Dict[ModelType, Dict]:
        """
        Compare costs across different models.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            models: List of models to compare (default: all)
        
        Returns:
            Dictionary mapping model to cost breakdown
        """
        if models is None:
            models = list(ModelType)
        
        comparison = {}
        for model in models:
            cost_data = calculate_cost(model, input_tokens, output_tokens)
            comparison[model] = cost_data
        
        return comparison


class CostCalculator:
    """
    Advanced cost calculator with analytics and projections.
    """
    
    def __init__(self):
        """Initialize cost calculator"""
        self.pricing_model = PricingModel()
    
    def calculate_projected_cost(
        self,
        historical_usage: List[CostRecord],
        projection_days: int = 30,
    ) -> Dict:
        """
        Project future costs based on historical usage.
        
        Args:
            historical_usage: List of historical cost records
            projection_days: Number of days to project
        
        Returns:
            Dictionary with projected costs
        """
        if not historical_usage:
            return {
                "projected_cost": 0.0,
                "daily_avg": 0.0,
                "confidence": "low",
            }
        
        # Calculate daily average from historical data
        total_cost = sum(record.total_cost for record in historical_usage)
        
        # Calculate time span of historical data
        timestamps = [record.usage.timestamp for record in historical_usage]
        time_span = (max(timestamps) - min(timestamps)).days + 1
        
        daily_avg = total_cost / time_span if time_span > 0 else total_cost
        projected_cost = daily_avg * projection_days
        
        # Confidence based on amount of historical data
        confidence = "low"
        if len(historical_usage) > 100:
            confidence = "high"
        elif len(historical_usage) > 30:
            confidence = "medium"
        
        return {
            "projected_cost": round(projected_cost, 2),
            "daily_avg": round(daily_avg, 2),
            "historical_days": time_span,
            "historical_requests": len(historical_usage),
            "projection_days": projection_days,
            "confidence": confidence,
        }
    
    def calculate_cost_breakdown(
        self,
        usage_records: List[CostRecord],
    ) -> Dict:
        """
        Calculate detailed cost breakdown.
        
        Args:
            usage_records: List of cost records
        
        Returns:
            Dictionary with cost breakdown by various dimensions
        """
        breakdown = {
            "total_cost": 0.0,
            "by_model": {},
            "by_request_type": {},
            "by_agent": {},
            "by_user": {},
            "by_date": {},
        }
        
        for record in usage_records:
            cost = record.total_cost
            breakdown["total_cost"] += cost
            
            # By model
            model = record.usage.model
            breakdown["by_model"][model] = breakdown["by_model"].get(model, 0.0) + cost
            
            # By request type
            req_type = record.usage.request_type
            breakdown["by_request_type"][req_type] = breakdown["by_request_type"].get(req_type, 0.0) + cost
            
            # By agent
            if record.usage.agent_name:
                agent = record.usage.agent_name
                breakdown["by_agent"][agent] = breakdown["by_agent"].get(agent, 0.0) + cost
            
            # By user
            if record.usage.user_id:
                user = record.usage.user_id
                breakdown["by_user"][user] = breakdown["by_user"].get(user, 0.0) + cost
            
            # By date
            date = record.usage.timestamp.date().isoformat()
            breakdown["by_date"][date] = breakdown["by_date"].get(date, 0.0) + cost
        
        # Round all values
        breakdown["total_cost"] = round(breakdown["total_cost"], 6)
        for category in ["by_model", "by_request_type", "by_agent", "by_user", "by_date"]:
            breakdown[category] = {k: round(v, 6) for k, v in breakdown[category].items()}
        
        return breakdown
    
    def calculate_savings_opportunity(
        self,
        current_model: ModelType,
        current_usage: List[CostRecord],
        alternative_model: ModelType,
    ) -> Dict:
        """
        Calculate potential savings by switching models.
        
        Args:
            current_model: Current model being used
            current_usage: Usage records with current model
            alternative_model: Alternative model to compare
        
        Returns:
            Dictionary with savings analysis
        """
        current_cost = sum(record.total_cost for record in current_usage)
        
        # Calculate cost with alternative model
        alternative_cost = 0.0
        for record in current_usage:
            alt_cost_data = calculate_cost(
                model=alternative_model,
                input_tokens=record.usage.input_tokens,
                output_tokens=record.usage.output_tokens,
            )
            alternative_cost += alt_cost_data["total_cost"]
        
        savings = current_cost - alternative_cost
        savings_percentage = (savings / current_cost * 100) if current_cost > 0 else 0
        
        return {
            "current_model": current_model,
            "current_cost": round(current_cost, 6),
            "alternative_model": alternative_model,
            "alternative_cost": round(alternative_cost, 6),
            "savings": round(savings, 6),
            "savings_percentage": round(savings_percentage, 2),
            "recommendation": "switch" if savings > 0 else "keep_current",
        }
    
    def calculate_roi(
        self,
        implementation_cost: float,
        monthly_savings: float,
    ) -> Dict:
        """
        Calculate return on investment for optimization.
        
        Args:
            implementation_cost: One-time cost to implement
            monthly_savings: Expected monthly savings
        
        Returns:
            Dictionary with ROI analysis
        """
        if monthly_savings <= 0:
            return {
                "roi": -100,
                "payback_months": float('inf'),
                "yearly_savings": 0,
            }
        
        yearly_savings = monthly_savings * 12
        roi = ((yearly_savings - implementation_cost) / implementation_cost * 100) if implementation_cost > 0 else float('inf')
        payback_months = implementation_cost / monthly_savings if monthly_savings > 0 else float('inf')
        
        return {
            "implementation_cost": implementation_cost,
            "monthly_savings": round(monthly_savings, 2),
            "yearly_savings": round(yearly_savings, 2),
            "roi_percentage": round(roi, 2),
            "payback_months": round(payback_months, 1),
            "recommendation": "proceed" if payback_months < 12 else "evaluate",
        }
    
    def calculate_cost_per_user(
        self,
        usage_records: List[CostRecord],
    ) -> Dict[str, Dict]:
        """
        Calculate cost per user with statistics.
        
        Args:
            usage_records: List of cost records
        
        Returns:
            Dictionary mapping user_id to usage statistics
        """
        user_stats = {}
        
        for record in usage_records:
            if not record.usage.user_id:
                continue
            
            user_id = record.usage.user_id
            if user_id not in user_stats:
                user_stats[user_id] = {
                    "total_cost": 0.0,
                    "request_count": 0,
                    "total_tokens": 0,
                    "avg_cost_per_request": 0.0,
                    "avg_tokens_per_request": 0.0,
                }
            
            stats = user_stats[user_id]
            stats["total_cost"] += record.total_cost
            stats["request_count"] += 1
            stats["total_tokens"] += record.usage.total_tokens
        
        # Calculate averages
        for user_id, stats in user_stats.items():
            if stats["request_count"] > 0:
                stats["avg_cost_per_request"] = stats["total_cost"] / stats["request_count"]
                stats["avg_tokens_per_request"] = stats["total_tokens"] / stats["request_count"]
            
            # Round values
            stats["total_cost"] = round(stats["total_cost"], 6)
            stats["avg_cost_per_request"] = round(stats["avg_cost_per_request"], 6)
            stats["avg_tokens_per_request"] = round(stats["avg_tokens_per_request"], 2)
        
        return user_stats
