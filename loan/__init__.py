"""Loan Collateral Assessment System - Core Module

This module provides intelligent loan processing with:
- Multi-source collateral valuation
- AI-powered risk assessment
- Automated document verification
- Regulatory compliance checking
- Explainable loan decisions
"""

from .models import (
    LoanType,
    CollateralType,
    LoanStatus,
    RiskLevel,
    LoanApplication,
    CollateralAsset,
    CollateralValuation,
    RiskAssessment,
    LoanDecision,
    Borrower
)

__version__ = "1.0.0"
__all__ = [
    "LoanType",
    "CollateralType",
    "LoanStatus",
    "RiskLevel",
    "LoanApplication",
    "CollateralAsset",
    "CollateralValuation",
    "RiskAssessment",
    "LoanDecision",
    "Borrower"
]
