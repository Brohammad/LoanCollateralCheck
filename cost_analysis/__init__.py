"""
Cost Analysis and Optimization Module

Provides comprehensive cost tracking, analysis, and optimization for LLM API usage.
Tracks token usage, calculates costs, provides budget alerts, and suggests optimizations.
"""

from cost_analysis.tracker import CostTracker
from cost_analysis.calculator import CostCalculator
from cost_analysis.budgets import BudgetManager
from cost_analysis.optimizer import CostOptimizer
from cost_analysis.analytics import CostAnalytics
from cost_analysis.models import (
    TokenUsage,
    CostRecord,
    BudgetAlert,
    OptimizationSuggestion,
)

__all__ = [
    "CostTracker",
    "CostCalculator",
    "BudgetManager",
    "CostOptimizer",
    "CostAnalytics",
    "TokenUsage",
    "CostRecord",
    "BudgetAlert",
    "OptimizationSuggestion",
]

__version__ = "1.0.0"
