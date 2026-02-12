"""Credit risk scoring and assessment.

Analyzes borrower creditworthiness based on credit score, payment history, 
and other credit factors.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class CreditScorer:
    """Assess credit risk for loan applications."""
    
    # Credit score ranges (FICO)
    CREDIT_RANGES = {
        "excellent": (750, 850),
        "good": (670, 749),
        "fair": (580, 669),
        "poor": (300, 579)
    }
    
    # Minimum scores by loan type
    MIN_CREDIT_SCORES = {
        "mortgage": 620,
        "auto": 580,
        "equipment": 650,
        "personal": 600,
        "business": 680
    }
    
    def assess_credit_risk(
        self,
        credit_score: int,
        loan_type: str = "personal",
        payment_history: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Assess credit risk based on credit score and history.
        
        Args:
            credit_score: FICO credit score (300-850)
            loan_type: Type of loan
            payment_history: Optional payment history data
            
        Returns:
            Credit risk assessment
        """
        logger.info(f"Assessing credit risk for score: {credit_score}, loan type: {loan_type}")
        
        # Validate credit score
        if not (300 <= credit_score <= 850):
            logger.error(f"Invalid credit score: {credit_score}")
            return self._create_error_assessment("Invalid credit score")
        
        # Determine credit tier
        credit_tier = self._get_credit_tier(credit_score)
        
        # Calculate risk score (0-1, higher = more risk)
        risk_score = self._calculate_credit_risk_score(credit_score)
        
        # Check minimum requirement
        min_score = self.MIN_CREDIT_SCORES.get(loan_type, 600)
        meets_minimum = credit_score >= min_score
        
        # Analyze payment history if provided
        payment_risk = self._analyze_payment_history(payment_history) if payment_history else {}
        
        # Generate risk factors
        risk_factors = self._identify_risk_factors(credit_score, credit_tier, payment_history)
        mitigating_factors = self._identify_mitigating_factors(credit_score, credit_tier)
        
        assessment = {
            "credit_score": credit_score,
            "credit_tier": credit_tier,
            "risk_score": round(risk_score, 3),
            "risk_level": self._score_to_risk_level(risk_score),
            "meets_minimum": meets_minimum,
            "minimum_required": min_score,
            "score_difference": credit_score - min_score,
            "payment_history_assessment": payment_risk,
            "risk_factors": risk_factors,
            "mitigating_factors": mitigating_factors,
            "recommended_interest_rate_adjustment": self._suggest_rate_adjustment(credit_tier)
        }
        
        logger.info(f"Credit assessment complete: {credit_tier}, risk score: {risk_score:.3f}")
        
        return assessment
    
    def _get_credit_tier(self, credit_score: int) -> str:
        """Determine credit tier from score.
        
        Args:
            credit_score: FICO score
            
        Returns:
            Credit tier name
        """
        for tier, (min_score, max_score) in self.CREDIT_RANGES.items():
            if min_score <= credit_score <= max_score:
                return tier
        return "poor"
    
    def _calculate_credit_risk_score(self, credit_score: int) -> float:
        """Calculate normalized credit risk score.
        
        Args:
            credit_score: FICO score
            
        Returns:
            Risk score (0-1, higher = more risk)
        """
        # Excellent (750+): 0.0 - 0.2
        if credit_score >= 750:
            return 0.2 - ((credit_score - 750) / 100) * 0.2
        # Good (670-749): 0.2 - 0.4
        elif credit_score >= 670:
            return 0.2 + ((750 - credit_score) / 80) * 0.2
        # Fair (580-669): 0.4 - 0.7
        elif credit_score >= 580:
            return 0.4 + ((670 - credit_score) / 90) * 0.3
        # Poor (300-579): 0.7 - 1.0
        else:
            return 0.7 + ((580 - credit_score) / 280) * 0.3
    
    def _score_to_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level.
        
        Args:
            risk_score: Numerical risk score
            
        Returns:
            Risk level string
        """
        if risk_score < 0.3:
            return "low"
        elif risk_score < 0.5:
            return "medium"
        elif risk_score < 0.75:
            return "high"
        else:
            return "very_high"
    
    def _analyze_payment_history(self, payment_history: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze payment history for additional risk factors.
        
        Args:
            payment_history: Payment history data
            
        Returns:
            Payment history risk assessment
        """
        late_payments_30 = payment_history.get("late_30_days", 0)
        late_payments_60 = payment_history.get("late_60_days", 0)
        late_payments_90 = payment_history.get("late_90_days", 0)
        collections = payment_history.get("collections", 0)
        bankruptcies = payment_history.get("bankruptcies", 0)
        
        # Calculate payment history score
        total_late = late_payments_30 + (late_payments_60 * 2) + (late_payments_90 * 3)
        
        if total_late == 0 and collections == 0 and bankruptcies == 0:
            history_risk = "low"
        elif total_late <= 2 and collections == 0 and bankruptcies == 0:
            history_risk = "medium"
        else:
            history_risk = "high"
        
        return {
            "risk_level": history_risk,
            "late_payments_30_days": late_payments_30,
            "late_payments_60_days": late_payments_60,
            "late_payments_90_days": late_payments_90,
            "collections": collections,
            "bankruptcies": bankruptcies,
            "concerns": total_late > 3 or collections > 0 or bankruptcies > 0
        }
    
    def _identify_risk_factors(
        self,
        credit_score: int,
        credit_tier: str,
        payment_history: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Identify specific credit risk factors.
        
        Args:
            credit_score: Credit score
            credit_tier: Credit tier
            payment_history: Payment history
            
        Returns:
            List of risk factors
        """
        factors = []
        
        if credit_score < 620:
            factors.append("Credit score below conventional lending standards")
        
        if credit_tier == "poor":
            factors.append("Poor credit history indicates high default risk")
        elif credit_tier == "fair":
            factors.append("Fair credit requires additional scrutiny")
        
        if payment_history:
            if payment_history.get("late_90_days", 0) > 0:
                factors.append("Recent 90+ day late payments")
            if payment_history.get("collections", 0) > 0:
                factors.append("Active collection accounts")
            if payment_history.get("bankruptcies", 0) > 0:
                factors.append("Bankruptcy on record")
        
        return factors
    
    def _identify_mitigating_factors(
        self,
        credit_score: int,
        credit_tier: str
    ) -> List[str]:
        """Identify factors that mitigate credit risk.
        
        Args:
            credit_score: Credit score
            credit_tier: Credit tier
            
        Returns:
            List of mitigating factors
        """
        factors = []
        
        if credit_score >= 750:
            factors.append("Excellent credit score demonstrates strong creditworthiness")
        elif credit_score >= 700:
            factors.append("Good credit score shows responsible credit management")
        
        if credit_tier in ["excellent", "good"]:
            factors.append(f"{credit_tier.capitalize()} credit tier reduces default probability")
        
        return factors
    
    def _suggest_rate_adjustment(self, credit_tier: str) -> float:
        """Suggest interest rate adjustment based on credit tier.
        
        Args:
            credit_tier: Credit tier
            
        Returns:
            Rate adjustment in percentage points
        """
        adjustments = {
            "excellent": -0.5,  # 0.5% rate reduction
            "good": 0.0,        # Base rate
            "fair": 1.5,        # 1.5% increase
            "poor": 3.0         # 3.0% increase
        }
        return adjustments.get(credit_tier, 2.0)
    
    def _create_error_assessment(self, error_message: str) -> Dict[str, Any]:
        """Create error assessment response.
        
        Args:
            error_message: Error description
            
        Returns:
            Error assessment dict
        """
        return {
            "error": error_message,
            "risk_score": 1.0,
            "risk_level": "very_high",
            "meets_minimum": False
        }
