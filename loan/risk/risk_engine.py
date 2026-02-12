"""Combined risk assessment engine.

Integrates LTV, credit, and market risk into comprehensive loan risk assessment.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from ..models import LoanApplication, CollateralValuation, RiskAssessment, RiskLevel, LoanType
from .ltv_calculator import LTVCalculator
from .credit_scorer import CreditScorer
from .market_risk import MarketRiskAnalyzer

logger = logging.getLogger(__name__)


class RiskEngine:
    """Comprehensive risk assessment engine for loan applications."""
    
    # Risk component weights
    RISK_WEIGHTS = {
        "ltv": 0.35,        # 35% - Collateral coverage
        "credit": 0.40,     # 40% - Borrower creditworthiness
        "market": 0.15,     # 15% - Market conditions
        "dti": 0.10         # 10% - Debt-to-income
    }
    
    # Maximum DTI ratios
    MAX_DTI_RATIOS = {
        LoanType.MORTGAGE: 0.43,    # 43% for mortgages (QM standard)
        LoanType.AUTO: 0.50,         # 50% for auto loans
        LoanType.EQUIPMENT: 0.40,    # 40% for equipment
        LoanType.PERSONAL: 0.45,     # 45% for personal loans
        LoanType.BUSINESS: 0.35      # 35% for business loans
    }
    
    def __init__(self):
        """Initialize risk engine with component analyzers."""
        self.ltv_calculator = LTVCalculator()
        self.credit_scorer = CreditScorer()
        self.market_analyzer = MarketRiskAnalyzer()
    
    async def assess_application_risk(
        self,
        application: LoanApplication,
        valuation: CollateralValuation,
        borrower_data: Dict[str, Any]
    ) -> RiskAssessment:
        """Perform comprehensive risk assessment.
        
        Args:
            application: Loan application
            valuation: Collateral valuation
            borrower_data: Borrower financial data
            
        Returns:
            Complete RiskAssessment
        """
        logger.info(f"Starting risk assessment for application: {application.id}")
        
        try:
            # 1. Calculate LTV risk
            ltv_ratio = self.ltv_calculator.calculate_ltv(
                loan_amount=application.requested_amount,
                collateral_value=valuation.estimated_value
            )
            
            ltv_assessment = self.ltv_calculator.assess_ltv_risk(
                ltv_ratio=ltv_ratio,
                loan_type=application.loan_type
            )
            ltv_risk_score = ltv_assessment["risk_score"]
            
            # 2. Assess credit risk
            credit_score = borrower_data.get("credit_score", 650)
            credit_assessment = self.credit_scorer.assess_credit_risk(
                credit_score=credit_score,
                loan_type=application.loan_type.value,
                payment_history=borrower_data.get("payment_history")
            )
            credit_risk_score = credit_assessment["risk_score"]
            
            # 3. Analyze market risk
            market_assessment = self.market_analyzer.analyze_market_risk(
                collateral_type=application.collateral_type.value,
                market_data=valuation.market_conditions
            )
            market_risk_score = market_assessment["market_risk_score"]
            
            # 4. Calculate DTI risk
            annual_income = borrower_data.get("annual_income", 50000)
            monthly_debt_payments = borrower_data.get("monthly_debt_payments", 0)
            monthly_income = annual_income / 12
            
            # Estimate new monthly payment (simplified)
            estimated_payment = self._estimate_monthly_payment(
                loan_amount=application.requested_amount,
                annual_rate=0.07,  # 7% estimated
                term_months=60 if application.loan_type == LoanType.AUTO else 360
            )
            
            total_monthly_debt = monthly_debt_payments + estimated_payment
            dti_ratio = total_monthly_debt / monthly_income if monthly_income > 0 else 1.0
            
            dti_assessment = self._assess_dti_risk(dti_ratio, application.loan_type)
            dti_risk_score = dti_assessment["risk_score"]
            
            # 5. Calculate overall risk score (weighted)
            overall_risk_score = (
                (ltv_risk_score * self.RISK_WEIGHTS["ltv"]) +
                (credit_risk_score * self.RISK_WEIGHTS["credit"]) +
                (market_risk_score * self.RISK_WEIGHTS["market"]) +
                (dti_risk_score * self.RISK_WEIGHTS["dti"])
            )
            
            # Determine risk level
            risk_level = self._score_to_risk_level(overall_risk_score)
            
            # Identify risk factors and mitigating factors
            risk_factors = self._compile_risk_factors(
                ltv_assessment, credit_assessment, market_assessment, dti_assessment
            )
            
            mitigating_factors = self._compile_mitigating_factors(
                ltv_assessment, credit_assessment, market_assessment, dti_assessment
            )
            
            # Identify red flags (critical issues)
            red_flags = self._identify_red_flags(
                ltv_assessment, credit_assessment, dti_assessment
            )
            
            # Create risk assessment
            risk_assessment = RiskAssessment(
                application_id=application.id,
                ltv_ratio=round(ltv_ratio, 4),
                dti_ratio=round(dti_ratio, 4),
                credit_score=credit_score,
                credit_risk_score=round(credit_risk_score, 3),
                collateral_risk_score=round(ltv_risk_score, 3),
                market_risk_score=round(market_risk_score, 3),
                overall_risk_score=round(overall_risk_score, 3),
                risk_level=RiskLevel(risk_level),
                risk_factors=risk_factors,
                mitigating_factors=mitigating_factors,
                red_flags=red_flags
            )
            
            logger.info(
                f"Risk assessment complete: {risk_level} "
                f"(overall score: {overall_risk_score:.3f})"
            )
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {e}", exc_info=True)
            # Return high-risk assessment on error
            return self._create_error_assessment(application.id, str(e))
    
    def _estimate_monthly_payment(
        self,
        loan_amount: float,
        annual_rate: float,
        term_months: int
    ) -> float:
        """Estimate monthly loan payment.
        
        Args:
            loan_amount: Principal amount
            annual_rate: Annual interest rate (e.g., 0.07 for 7%)
            term_months: Loan term in months
            
        Returns:
            Estimated monthly payment
        """
        if term_months == 0:
            return 0.0
        
        monthly_rate = annual_rate / 12
        
        if monthly_rate == 0:
            return loan_amount / term_months
        
        # Standard amortization formula
        payment = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** term_months
        ) / (
            (1 + monthly_rate) ** term_months - 1
        )
        
        return payment
    
    def _assess_dti_risk(
        self,
        dti_ratio: float,
        loan_type: LoanType
    ) -> Dict[str, Any]:
        """Assess debt-to-income risk.
        
        Args:
            dti_ratio: DTI ratio
            loan_type: Type of loan
            
        Returns:
            DTI risk assessment
        """
        max_dti = self.MAX_DTI_RATIOS.get(loan_type, 0.43)
        
        # Calculate risk score
        if dti_ratio <= 0.30:
            risk_score = 0.2
            risk_level = "low"
        elif dti_ratio <= 0.36:
            risk_score = 0.4
            risk_level = "medium"
        elif dti_ratio <= max_dti:
            risk_score = 0.6
            risk_level = "high"
        else:
            risk_score = 0.9
            risk_level = "very_high"
        
        return {
            "dti_ratio": round(dti_ratio, 4),
            "dti_percentage": round(dti_ratio * 100, 2),
            "max_dti": max_dti,
            "exceeds_max": dti_ratio > max_dti,
            "risk_score": risk_score,
            "risk_level": risk_level
        }
    
    def _score_to_risk_level(self, score: float) -> str:
        """Convert overall risk score to risk level.
        
        Args:
            score: Risk score (0-1)
            
        Returns:
            Risk level string
        """
        if score < 0.30:
            return "low"
        elif score < 0.50:
            return "medium"
        elif score < 0.70:
            return "high"
        else:
            return "very_high"
    
    def _compile_risk_factors(
        self,
        ltv_assessment: Dict[str, Any],
        credit_assessment: Dict[str, Any],
        market_assessment: Dict[str, Any],
        dti_assessment: Dict[str, Any]
    ) -> list:
        """Compile all risk factors.
        
        Args:
            ltv_assessment: LTV assessment
            credit_assessment: Credit assessment
            market_assessment: Market assessment
            dti_assessment: DTI assessment
            
        Returns:
            List of risk factors
        """
        factors = []
        
        # LTV factors
        if ltv_assessment.get("exceeds_max_ltv"):
            factors.append(f"LTV ratio exceeds maximum allowed")
        elif ltv_assessment["risk_level"] == "high":
            factors.append(f"High LTV ratio: {ltv_assessment['ltv_percentage']:.1f}%")
        
        # Credit factors
        factors.extend(credit_assessment.get("risk_factors", []))
        
        # Market factors
        if market_assessment["risk_level"] in ["high", "very_high"]:
            factors.extend(market_assessment.get("concerns", []))
        
        # DTI factors
        if dti_assessment.get("exceeds_max"):
            factors.append(f"DTI ratio exceeds maximum: {dti_assessment['dti_percentage']:.1f}%")
        elif dti_assessment["risk_level"] in ["high", "very_high"]:
            factors.append(f"High debt-to-income ratio: {dti_assessment['dti_percentage']:.1f}%")
        
        return factors or ["No significant risk factors identified"]
    
    def _compile_mitigating_factors(
        self,
        ltv_assessment: Dict[str, Any],
        credit_assessment: Dict[str, Any],
        market_assessment: Dict[str, Any],
        dti_assessment: Dict[str, Any]
    ) -> list:
        """Compile factors that mitigate risk.
        
        Args:
            ltv_assessment: LTV assessment
            credit_assessment: Credit assessment
            market_assessment: Market assessment
            dti_assessment: DTI assessment
            
        Returns:
            List of mitigating factors
        """
        factors = []
        
        # LTV factors
        if ltv_assessment["risk_level"] == "low":
            factors.append(f"Low LTV provides strong collateral coverage")
        
        # Credit factors
        factors.extend(credit_assessment.get("mitigating_factors", []))
        
        # Market factors
        if market_assessment["risk_level"] == "low":
            factors.append("Favorable market conditions for collateral")
        
        # DTI factors
        if dti_assessment["risk_level"] == "low":
            factors.append("Low DTI indicates strong payment capacity")
        
        return factors or ["No significant mitigating factors identified"]
    
    def _identify_red_flags(
        self,
        ltv_assessment: Dict[str, Any],
        credit_assessment: Dict[str, Any],
        dti_assessment: Dict[str, Any]
    ) -> list:
        """Identify critical red flags.
        
        Args:
            ltv_assessment: LTV assessment
            credit_assessment: Credit assessment
            dti_assessment: DTI assessment
            
        Returns:
            List of red flags
        """
        red_flags = []
        
        # Critical LTV issue
        if ltv_assessment.get("exceeds_max_ltv"):
            red_flags.append("CRITICAL: LTV exceeds lending guidelines")
        
        # Critical credit issues
        if not credit_assessment.get("meets_minimum"):
            red_flags.append("CRITICAL: Credit score below minimum requirement")
        
        payment_history = credit_assessment.get("payment_history_assessment", {})
        if payment_history.get("bankruptcies", 0) > 0:
            red_flags.append("CRITICAL: Recent bankruptcy on record")
        
        # Critical DTI issue
        if dti_assessment.get("exceeds_max"):
            red_flags.append("CRITICAL: Debt-to-income ratio exceeds maximum")
        
        return red_flags
    
    def _create_error_assessment(
        self,
        application_id: str,
        error: str
    ) -> RiskAssessment:
        """Create error risk assessment.
        
        Args:
            application_id: Application ID
            error: Error message
            
        Returns:
            High-risk assessment
        """
        return RiskAssessment(
            application_id=application_id,
            ltv_ratio=0.0,
            dti_ratio=0.0,
            credit_score=0,
            credit_risk_score=1.0,
            collateral_risk_score=1.0,
            market_risk_score=1.0,
            overall_risk_score=1.0,
            risk_level=RiskLevel.VERY_HIGH,
            risk_factors=[f"Risk assessment error: {error}"],
            mitigating_factors=[],
            red_flags=["CRITICAL: Unable to complete risk assessment"]
        )
