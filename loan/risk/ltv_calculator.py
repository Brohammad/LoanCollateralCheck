"""Loan-to-Value (LTV) ratio calculator and risk assessment.

LTV is a key metric in lending that compares the loan amount to the value of the collateral.
Lower LTV = Lower risk for lender.
"""

import logging
from typing import Dict, Any, List
from ..models import LoanType, CollateralType

logger = logging.getLogger(__name__)


class LTVCalculator:
    """Calculate and assess Loan-to-Value ratios."""
    
    # Maximum LTV ratios by loan type (industry standards)
    MAX_LTV_RATIOS = {
        LoanType.MORTGAGE: 0.80,  # 80% for conventional mortgages
        LoanType.AUTO: 1.00,      # 100% for auto loans
        LoanType.EQUIPMENT: 0.80,  # 80% for equipment financing
        LoanType.PERSONAL: 0.90,   # 90% for secured personal loans
        LoanType.BUSINESS: 0.75    # 75% for business loans
    }
    
    # LTV risk thresholds
    RISK_THRESHOLDS = {
        "low": 0.70,     # < 70% = Low risk
        "medium": 0.85,  # 70-85% = Medium risk
        "high": 0.95     # 85-95% = High risk
                         # > 95% = Very high risk
    }
    
    def calculate_ltv(
        self,
        loan_amount: float,
        collateral_value: float
    ) -> float:
        """Calculate basic LTV ratio.
        
        Args:
            loan_amount: Requested loan amount
            collateral_value: Appraised collateral value
            
        Returns:
            LTV ratio (0.0 - 1.0+)
        """
        if collateral_value <= 0:
            logger.error(f"Invalid collateral value: {collateral_value}")
            return 999.99  # Invalid/max risk
        
        ltv = loan_amount / collateral_value
        logger.info(f"LTV calculated: {ltv:.2%} (${loan_amount:,.2f} / ${collateral_value:,.2f})")
        
        return ltv
    
    def assess_ltv_risk(
        self,
        ltv_ratio: float,
        loan_type: LoanType
    ) -> Dict[str, Any]:
        """Assess risk level based on LTV ratio.
        
        Args:
            ltv_ratio: Calculated LTV ratio
            loan_type: Type of loan
            
        Returns:
            Dict with risk assessment details
        """
        max_ltv = self.MAX_LTV_RATIOS.get(loan_type, 0.80)
        
        # Determine risk level
        if ltv_ratio <= self.RISK_THRESHOLDS["low"]:
            risk_level = "low"
            risk_score = ltv_ratio / self.RISK_THRESHOLDS["low"]  # 0.0 - 1.0
        elif ltv_ratio <= self.RISK_THRESHOLDS["medium"]:
            risk_level = "medium"
            risk_score = 0.3 + (ltv_ratio - self.RISK_THRESHOLDS["low"]) / (
                self.RISK_THRESHOLDS["medium"] - self.RISK_THRESHOLDS["low"]
            ) * 0.4  # 0.3 - 0.7
        elif ltv_ratio <= self.RISK_THRESHOLDS["high"]:
            risk_level = "high"
            risk_score = 0.7 + (ltv_ratio - self.RISK_THRESHOLDS["medium"]) / (
                self.RISK_THRESHOLDS["high"] - self.RISK_THRESHOLDS["medium"]
            ) * 0.2  # 0.7 - 0.9
        else:
            risk_level = "very_high"
            risk_score = min(0.9 + (ltv_ratio - self.RISK_THRESHOLDS["high"]) * 0.5, 1.0)
        
        # Check if LTV exceeds maximum for loan type
        exceeds_max = ltv_ratio > max_ltv
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            ltv_ratio=ltv_ratio,
            max_ltv=max_ltv,
            risk_level=risk_level,
            exceeds_max=exceeds_max
        )
        
        assessment = {
            "ltv_ratio": round(ltv_ratio, 4),
            "ltv_percentage": round(ltv_ratio * 100, 2),
            "risk_level": risk_level,
            "risk_score": round(risk_score, 3),
            "max_ltv_for_type": max_ltv,
            "exceeds_max_ltv": exceeds_max,
            "within_guidelines": not exceeds_max,
            "recommendations": recommendations
        }
        
        logger.info(f"LTV risk assessment: {risk_level} (score: {risk_score:.3f})")
        
        return assessment
    
    def calculate_required_down_payment(
        self,
        loan_amount: float,
        collateral_value: float,
        target_ltv: float = 0.80
    ) -> Dict[str, Any]:
        """Calculate required down payment to achieve target LTV.
        
        Args:
            loan_amount: Requested loan amount
            collateral_value: Collateral value
            target_ltv: Desired LTV ratio
            
        Returns:
            Dict with down payment calculations
        """
        current_ltv = self.calculate_ltv(loan_amount, collateral_value)
        
        # Maximum loan at target LTV
        max_loan_at_target = collateral_value * target_ltv
        
        # Required down payment
        if loan_amount > max_loan_at_target:
            required_down_payment = loan_amount - max_loan_at_target
        else:
            required_down_payment = 0.0
        
        return {
            "current_ltv": round(current_ltv, 4),
            "target_ltv": target_ltv,
            "max_loan_at_target_ltv": round(max_loan_at_target, 2),
            "required_down_payment": round(required_down_payment, 2),
            "down_payment_percentage": round(
                (required_down_payment / loan_amount * 100) if loan_amount > 0 else 0, 2
            )
        }
    
    def calculate_equity_position(
        self,
        collateral_value: float,
        loan_amount: float
    ) -> Dict[str, Any]:
        """Calculate borrower's equity position.
        
        Args:
            collateral_value: Current collateral value
            loan_amount: Loan amount
            
        Returns:
            Equity position details
        """
        equity = collateral_value - loan_amount
        equity_percentage = (equity / collateral_value * 100) if collateral_value > 0 else 0
        
        return {
            "equity_amount": round(equity, 2),
            "equity_percentage": round(equity_percentage, 2),
            "underwater": equity < 0,
            "cushion": "excellent" if equity_percentage > 30 else
                      "good" if equity_percentage > 20 else
                      "adequate" if equity_percentage > 10 else
                      "minimal"
        }
    
    def _generate_recommendations(
        self,
        ltv_ratio: float,
        max_ltv: float,
        risk_level: str,
        exceeds_max: bool
    ) -> List[str]:
        """Generate recommendations based on LTV assessment.
        
        Args:
            ltv_ratio: Current LTV ratio
            max_ltv: Maximum allowed LTV
            risk_level: Assessed risk level
            exceeds_max: Whether LTV exceeds maximum
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if exceeds_max:
            recommendations.append(
                f"LTV exceeds maximum allowed ratio of {max_ltv:.0%}. "
                f"Reduce loan amount or require higher down payment."
            )
        
        if risk_level == "very_high":
            recommendations.append(
                "Very high LTV ratio. Consider requiring mortgage insurance or co-signer."
            )
        elif risk_level == "high":
            recommendations.append(
                "High LTV ratio. Consider requiring additional collateral or higher interest rate."
            )
        elif risk_level == "low":
            recommendations.append(
                "Excellent LTV ratio. Borrower has strong equity position."
            )
        
        if ltv_ratio > 0.90:
            recommendations.append(
                "Consider ordering updated appraisal to verify current market value."
            )
        
        return recommendations
