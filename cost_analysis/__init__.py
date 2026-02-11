"""
Cost Analysis and Optimization Module

This module provides comprehensive cost tracking, analysis, and optimization
for LLM API usage in the AI Agent System.

Features:
- Real-time token usage tracking
- Cost calculation per request
- Budget management and alerts
- Usage analytics and reporting
- Cost optimization recommendations
- Historical data analysis
"""

from cost_analysis.tracker import CostTracker, TokenUsage
from cost_analysis.calculator import CostCalculator, PricingModel
from cost_analysis.budget import BudgetManager, Budget, BudgetAlert
from cost_analysis.optimizer import CostOptimizer, OptimizationRecommendation
from cost_analysis.analytics import CostAnalytics, UsageReport
from cost_analysis.middleware import cost_tracking_middleware

__all__ = [
    "CostTracker",
    "TokenUsage",
    "CostCalculator",
    "PricingModel",
    "BudgetManager",
    "Budget",
    "BudgetAlert",
    "CostOptimizer",
    "OptimizationRecommendation",
    "CostAnalytics",
    "UsageReport",
    "cost_tracking_middleware",
]

__version__ = "1.0.0"
