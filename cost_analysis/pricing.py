"""
Pricing information for different LLM models
"""

from typing import Dict
from cost_analysis.models import ModelType


# Pricing in USD per 1 million tokens
# Source: Google AI Pricing (as of 2024)
# Note: These are example prices. Update with actual pricing from your provider.

PRICING: Dict[ModelType, Dict[str, float]] = {
    # Gemini 2.0 Flash (Experimental - Free during preview)
    ModelType.GEMINI_2_FLASH: {
        "input_per_1m": 0.0,    # Free during preview
        "output_per_1m": 0.0,   # Free during preview
        "input_per_1k": 0.0,
        "output_per_1k": 0.0,
    },
    
    # Gemini 1.5 Pro
    ModelType.GEMINI_15_PRO: {
        "input_per_1m": 1.25,      # $1.25 per 1M input tokens (≤128K)
        "output_per_1m": 5.00,     # $5.00 per 1M output tokens
        "input_per_1k": 0.00125,
        "output_per_1k": 0.00500,
    },
    
    # Gemini 1.5 Flash
    ModelType.GEMINI_15_FLASH: {
        "input_per_1m": 0.075,     # $0.075 per 1M input tokens (≤128K)
        "output_per_1m": 0.30,     # $0.30 per 1M output tokens
        "input_per_1k": 0.000075,
        "output_per_1k": 0.000300,
    },
    
    # Text Embedding
    ModelType.TEXT_EMBEDDING: {
        "input_per_1m": 0.00,      # Embeddings are typically free or very cheap
        "output_per_1m": 0.00,     # No output tokens for embeddings
        "input_per_1k": 0.00,
        "output_per_1k": 0.00,
    },
}


# Context pricing tiers (for models with variable pricing based on context length)
CONTEXT_PRICING_TIERS = {
    ModelType.GEMINI_15_PRO: {
        "128k": {"input_per_1m": 1.25, "output_per_1m": 5.00},
        "128k+": {"input_per_1m": 2.50, "output_per_1m": 10.00},  # >128K context
    },
    ModelType.GEMINI_15_FLASH: {
        "128k": {"input_per_1m": 0.075, "output_per_1m": 0.30},
        "128k+": {"input_per_1m": 0.15, "output_per_1m": 0.60},  # >128K context
    },
}


def get_pricing(model: ModelType, context_length: int = 0) -> Dict[str, float]:
    """
    Get pricing for a model, considering context length if applicable.
    
    Args:
        model: The model type
        context_length: Total context length (input + output tokens)
    
    Returns:
        Dictionary with pricing information
    """
    base_pricing = PRICING.get(model, PRICING[ModelType.GEMINI_2_FLASH])
    
    # Check if model has context-based pricing tiers
    if model in CONTEXT_PRICING_TIERS and context_length > 128000:
        tier_pricing = CONTEXT_PRICING_TIERS[model]["128k+"]
        return {
            "input_per_1m": tier_pricing["input_per_1m"],
            "output_per_1m": tier_pricing["output_per_1m"],
            "input_per_1k": tier_pricing["input_per_1m"] / 1000,
            "output_per_1k": tier_pricing["output_per_1m"] / 1000,
        }
    
    return base_pricing


def calculate_cost(
    model: ModelType,
    input_tokens: int,
    output_tokens: int,
    context_length: int = 0
) -> Dict[str, float]:
    """
    Calculate cost for a request.
    
    Args:
        model: The model type
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        context_length: Total context length (optional)
    
    Returns:
        Dictionary with cost breakdown
    """
    pricing = get_pricing(model, context_length or (input_tokens + output_tokens))
    
    input_cost = (input_tokens / 1000) * pricing["input_per_1k"]
    output_cost = (output_tokens / 1000) * pricing["output_per_1k"]
    total_cost = input_cost + output_cost
    
    return {
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(total_cost, 6),
        "input_price_per_1k": pricing["input_per_1k"],
        "output_price_per_1k": pricing["output_per_1k"],
    }


# Monthly cost estimates for different usage patterns
USAGE_ESTIMATES = {
    "light": {
        "requests_per_day": 100,
        "avg_input_tokens": 500,
        "avg_output_tokens": 200,
        "description": "Light usage: ~100 requests/day",
    },
    "medium": {
        "requests_per_day": 1000,
        "avg_input_tokens": 1000,
        "avg_output_tokens": 500,
        "description": "Medium usage: ~1K requests/day",
    },
    "heavy": {
        "requests_per_day": 10000,
        "avg_input_tokens": 2000,
        "avg_output_tokens": 1000,
        "description": "Heavy usage: ~10K requests/day",
    },
    "enterprise": {
        "requests_per_day": 100000,
        "avg_input_tokens": 3000,
        "avg_output_tokens": 1500,
        "description": "Enterprise usage: ~100K requests/day",
    },
}


def estimate_monthly_cost(
    model: ModelType,
    requests_per_day: int,
    avg_input_tokens: int,
    avg_output_tokens: int
) -> Dict[str, float]:
    """
    Estimate monthly cost based on usage pattern.
    
    Args:
        model: The model type
        requests_per_day: Average requests per day
        avg_input_tokens: Average input tokens per request
        avg_output_tokens: Average output tokens per request
    
    Returns:
        Dictionary with cost estimates
    """
    days_per_month = 30
    total_requests = requests_per_day * days_per_month
    
    cost_per_request = calculate_cost(model, avg_input_tokens, avg_output_tokens)
    
    monthly_cost = cost_per_request["total_cost"] * total_requests
    yearly_cost = monthly_cost * 12
    
    return {
        "requests_per_day": requests_per_day,
        "requests_per_month": total_requests,
        "cost_per_request": cost_per_request["total_cost"],
        "daily_cost": cost_per_request["total_cost"] * requests_per_day,
        "monthly_cost": round(monthly_cost, 2),
        "yearly_cost": round(yearly_cost, 2),
    }
