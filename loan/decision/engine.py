"""Loan decision engine with AI-powered reasoning.

Makes final loan decisions based on risk assessment and business rules,
with explainable AI reasoning powered by Google Gemini.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models import (
    LoanApplication,
    LoanDecision,
    RiskAssessment,
    CollateralValuation,
    DecisionType,
    LoanType
)

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Make loan approval/rejection decisions with business logic."""
    
    # Auto-approval thresholds
    AUTO_APPROVE_THRESHOLD = 0.40  # Risk score must be < 0.40
    AUTO_REJECT_THRESHOLD = 0.70    # Risk score >= 0.70 = auto-reject
    
    # Interest rate adjustments by risk level
    RATE_ADJUSTMENTS = {
        "low": -0.25,      # 0.25% discount
        "medium": 0.0,     # Base rate
        "high": 1.5,       # 1.5% premium
        "very_high": 3.0   # 3.0% premium
    }
    
    # Base interest rates by loan type
    BASE_RATES = {
        LoanType.MORTGAGE: 6.50,
        LoanType.AUTO: 7.00,
        LoanType.EQUIPMENT: 7.50,
        LoanType.PERSONAL: 9.00,
        LoanType.BUSINESS: 8.00
    }
    
    # Standard loan terms (months)
    STANDARD_TERMS = {
        LoanType.MORTGAGE: 360,    # 30 years
        LoanType.AUTO: 60,          # 5 years
        LoanType.EQUIPMENT: 84,     # 7 years
        LoanType.PERSONAL: 48,      # 4 years
        LoanType.BUSINESS: 120      # 10 years
    }
    
    def make_decision(
        self,
        application: LoanApplication,
        risk_assessment: RiskAssessment,
        valuation: CollateralValuation
    ) -> LoanDecision:
        """Make loan decision based on risk assessment.
        
        Args:
            application: Loan application
            risk_assessment: Risk assessment result
            valuation: Collateral valuation
            
        Returns:
            LoanDecision with reasoning
        """
        logger.info(f"Making loan decision for application: {application.id}")
        
        # Check for red flags (automatic rejection)
        if risk_assessment.red_flags:
            return self._create_rejection(
                application=application,
                risk_assessment=risk_assessment,
                reason="Critical red flags identified",
                confidence=0.95
            )
        
        overall_risk = risk_assessment.overall_risk_score
        risk_level = risk_assessment.risk_level.value
        
        # Auto-approve: Low risk
        if overall_risk < self.AUTO_APPROVE_THRESHOLD and risk_level == "low":
            return self._create_approval(
                application=application,
                risk_assessment=risk_assessment,
                valuation=valuation,
                conditions=[]
            )
        
        # Auto-reject: Very high risk
        elif overall_risk >= self.AUTO_REJECT_THRESHOLD or risk_level == "very_high":
            return self._create_rejection(
                application=application,
                risk_assessment=risk_assessment,
                reason="Risk level exceeds acceptable thresholds",
                confidence=0.90
            )
        
        # Conditional approval: Medium risk
        elif overall_risk < 0.50 and risk_level in ["low", "medium"]:
            conditions = self._generate_conditions(risk_assessment)
            return self._create_approval(
                application=application,
                risk_assessment=risk_assessment,
                valuation=valuation,
                conditions=conditions
            )
        
        # High risk: Conditional or manual review
        elif risk_level == "high":
            # Check if we can offer conditional approval
            if self._can_conditionally_approve(risk_assessment):
                conditions = self._generate_strict_conditions(risk_assessment)
                return self._create_conditional_approval(
                    application=application,
                    risk_assessment=risk_assessment,
                    valuation=valuation,
                    conditions=conditions
                )
            else:
                return self._create_manual_review(
                    application=application,
                    risk_assessment=risk_assessment
                )
        
        # Default: Manual review
        else:
            return self._create_manual_review(
                application=application,
                risk_assessment=risk_assessment
            )
    
    def _create_approval(
        self,
        application: LoanApplication,
        risk_assessment: RiskAssessment,
        valuation: CollateralValuation,
        conditions: List[str]
    ) -> LoanDecision:
        """Create approved loan decision.
        
        Args:
            application: Loan application
            risk_assessment: Risk assessment
            valuation: Collateral valuation
            conditions: Approval conditions
            
        Returns:
            Approved LoanDecision
        """
        # Calculate interest rate
        base_rate = self.BASE_RATES.get(application.loan_type, 8.0)
        rate_adjustment = self.RATE_ADJUSTMENTS.get(risk_assessment.risk_level.value, 0.0)
        interest_rate = base_rate + rate_adjustment
        
        # Determine loan term
        term_months = self.STANDARD_TERMS.get(application.loan_type, 60)
        
        # Calculate monthly payment
        monthly_payment = self._calculate_monthly_payment(
            principal=application.requested_amount,
            annual_rate=interest_rate / 100,
            term_months=term_months
        )
        
        # Generate key decision factors
        key_factors = [
            f"Risk score {risk_assessment.overall_risk_score:.3f} within acceptable range",
            f"LTV ratio {risk_assessment.ltv_ratio:.1%} meets guidelines",
            f"Credit score {risk_assessment.credit_score} is {self._credit_tier(risk_assessment.credit_score)}",
            f"DTI ratio {risk_assessment.dti_ratio:.1%} indicates strong payment capacity"
        ]
        
        # Add mitigating factors
        key_factors.extend(risk_assessment.mitigating_factors[:2])
        
        # Generate reasoning
        reasoning = f"""Loan approved based on comprehensive risk analysis. 
        
Overall Risk Assessment: {risk_assessment.risk_level.value.upper()}
- Risk Score: {risk_assessment.overall_risk_score:.3f} (threshold: {self.AUTO_APPROVE_THRESHOLD})
- Credit Quality: {self._credit_tier(risk_assessment.credit_score)} ({risk_assessment.credit_score})
- Collateral Coverage: LTV {risk_assessment.ltv_ratio:.1%}
- Debt Capacity: DTI {risk_assessment.dti_ratio:.1%}

The borrower demonstrates strong creditworthiness and the collateral provides adequate security.
Approved at favorable terms with {len(conditions)} condition(s)."""
        
        return LoanDecision(
            application_id=application.id,
            decision=DecisionType.APPROVED,
            confidence=0.90 if not conditions else 0.85,
            reasoning=reasoning,
            key_factors=key_factors,
            conditions=conditions,
            approved_amount=application.requested_amount,
            interest_rate=round(interest_rate, 2),
            term_months=term_months,
            monthly_payment=round(monthly_payment, 2),
            required_documents=self._get_standard_documents(application.loan_type),
            created_by="system"
        )
    
    def _create_conditional_approval(
        self,
        application: LoanApplication,
        risk_assessment: RiskAssessment,
        valuation: CollateralValuation,
        conditions: List[str]
    ) -> LoanDecision:
        """Create conditional approval decision.
        
        Args:
            application: Loan application
            risk_assessment: Risk assessment
            valuation: Collateral valuation
            conditions: Approval conditions
            
        Returns:
            Conditional approval LoanDecision
        """
        # Higher interest rate for conditional approval
        base_rate = self.BASE_RATES.get(application.loan_type, 8.0)
        rate_adjustment = self.RATE_ADJUSTMENTS.get(risk_assessment.risk_level.value, 0.0)
        interest_rate = base_rate + rate_adjustment + 0.5  # Additional 0.5% for conditional
        
        # May reduce approved amount
        approved_amount = application.requested_amount * 0.90  # 90% of requested
        
        term_months = self.STANDARD_TERMS.get(application.loan_type, 60)
        monthly_payment = self._calculate_monthly_payment(
            principal=approved_amount,
            annual_rate=interest_rate / 100,
            term_months=term_months
        )
        
        key_factors = [
            f"Risk score {risk_assessment.overall_risk_score:.3f} requires conditional approval",
            f"Multiple risk factors identified, but mitigable",
            f"Reduced loan amount to improve LTV ratio"
        ]
        
        reasoning = f"""Conditional approval granted with enhanced requirements.

Overall Risk Assessment: {risk_assessment.risk_level.value.upper()}
- Risk Score: {risk_assessment.overall_risk_score:.3f}
- Approved Amount: ${approved_amount:,.2f} (90% of requested)
- Interest Rate: {interest_rate:.2f}% APR (includes risk premium)

Risk Factors Requiring Mitigation:
{chr(10).join(f'- {factor}' for factor in risk_assessment.risk_factors[:3])}

Approval is conditional upon meeting all specified requirements."""
        
        return LoanDecision(
            application_id=application.id,
            decision=DecisionType.CONDITIONAL,
            confidence=0.75,
            reasoning=reasoning,
            key_factors=key_factors,
            conditions=conditions,
            approved_amount=round(approved_amount, 2),
            interest_rate=round(interest_rate, 2),
            term_months=term_months,
            monthly_payment=round(monthly_payment, 2),
            required_documents=self._get_enhanced_documents(application.loan_type),
            required_actions=conditions,
            created_by="system"
        )
    
    def _create_rejection(
        self,
        application: LoanApplication,
        risk_assessment: RiskAssessment,
        reason: str,
        confidence: float
    ) -> LoanDecision:
        """Create rejected loan decision.
        
        Args:
            application: Loan application
            risk_assessment: Risk assessment
            reason: Rejection reason
            confidence: Decision confidence
            
        Returns:
            Rejected LoanDecision
        """
        key_factors = [
            f"Overall risk score: {risk_assessment.overall_risk_score:.3f}",
            f"Risk level: {risk_assessment.risk_level.value.upper()}"
        ]
        
        # Add red flags
        if risk_assessment.red_flags:
            key_factors.extend(risk_assessment.red_flags[:3])
        else:
            key_factors.extend(risk_assessment.risk_factors[:3])
        
        # Generate recommendations
        recommendations = self._generate_rejection_recommendations(risk_assessment)
        
        reasoning = f"""Application declined due to elevated risk factors.

Primary Reason: {reason}

Risk Assessment Summary:
- Overall Risk Score: {risk_assessment.overall_risk_score:.3f}
- Risk Level: {risk_assessment.risk_level.value.upper()}
- LTV Ratio: {risk_assessment.ltv_ratio:.1%}
- Credit Score: {risk_assessment.credit_score}
- DTI Ratio: {risk_assessment.dti_ratio:.1%}

Critical Issues:
{chr(10).join(f'- {factor}' for factor in (risk_assessment.red_flags or risk_assessment.risk_factors)[:3])}

Recommendations for Future Application:
{chr(10).join(f'- {rec}' for rec in recommendations)}"""
        
        return LoanDecision(
            application_id=application.id,
            decision=DecisionType.REJECTED,
            confidence=confidence,
            reasoning=reasoning,
            key_factors=key_factors,
            conditions=recommendations,
            created_by="system"
        )
    
    def _create_manual_review(
        self,
        application: LoanApplication,
        risk_assessment: RiskAssessment
    ) -> LoanDecision:
        """Create manual review decision.
        
        Args:
            application: Loan application
            risk_assessment: Risk assessment
            
        Returns:
            Manual review LoanDecision
        """
        key_factors = [
            f"Risk score {risk_assessment.overall_risk_score:.3f} requires human review",
            f"Multiple complex factors need underwriter assessment",
            "Application does not meet auto-decision criteria"
        ]
        
        reasoning = f"""Application requires manual underwriter review.

Risk Profile: {risk_assessment.risk_level.value.upper()}
- Overall Risk Score: {risk_assessment.overall_risk_score:.3f}
- LTV: {risk_assessment.ltv_ratio:.1%}
- Credit: {risk_assessment.credit_score}
- DTI: {risk_assessment.dti_ratio:.1%}

Factors Requiring Review:
{chr(10).join(f'- {factor}' for factor in risk_assessment.risk_factors[:4])}

A qualified underwriter will review this application within 2 business days."""
        
        return LoanDecision(
            application_id=application.id,
            decision=DecisionType.MANUAL_REVIEW,
            confidence=0.60,
            reasoning=reasoning,
            key_factors=key_factors,
            conditions=["Pending underwriter review"],
            required_documents=self._get_standard_documents(application.loan_type),
            created_by="system"
        )
    
    def _calculate_monthly_payment(
        self,
        principal: float,
        annual_rate: float,
        term_months: int
    ) -> float:
        """Calculate monthly loan payment.
        
        Args:
            principal: Loan amount
            annual_rate: Annual interest rate (e.g., 0.07 for 7%)
            term_months: Loan term in months
            
        Returns:
            Monthly payment amount
        """
        if term_months == 0 or annual_rate == 0:
            return principal / term_months if term_months > 0 else 0
        
        monthly_rate = annual_rate / 12
        payment = principal * (
            monthly_rate * (1 + monthly_rate) ** term_months
        ) / (
            (1 + monthly_rate) ** term_months - 1
        )
        
        return payment
    
    def _credit_tier(self, credit_score: int) -> str:
        """Get credit tier description."""
        if credit_score >= 750:
            return "Excellent"
        elif credit_score >= 700:
            return "Very Good"
        elif credit_score >= 670:
            return "Good"
        elif credit_score >= 580:
            return "Fair"
        else:
            return "Poor"
    
    def _generate_conditions(self, risk_assessment: RiskAssessment) -> List[str]:
        """Generate standard approval conditions."""
        conditions = []
        
        if risk_assessment.ltv_ratio > 0.75:
            conditions.append("Collateral insurance required")
        
        if risk_assessment.dti_ratio > 0.38:
            conditions.append("Income verification documentation required")
        
        return conditions
    
    def _generate_strict_conditions(self, risk_assessment: RiskAssessment) -> List[str]:
        """Generate strict conditions for high-risk approvals."""
        conditions = [
            "Co-signer or guarantor required",
            "Enhanced documentation package required",
            "Collateral inspection and appraisal required",
            "Proof of employment and income (last 2 years)",
            "Additional down payment of 15% recommended"
        ]
        
        if risk_assessment.ltv_ratio > 0.80:
            conditions.append("Private mortgage insurance (PMI) required")
        
        if risk_assessment.credit_score < 650:
            conditions.append("Credit counseling completion recommended")
        
        return conditions
    
    def _can_conditionally_approve(self, risk_assessment: RiskAssessment) -> bool:
        """Check if conditional approval is possible."""
        # Can't conditionally approve if there are red flags
        if risk_assessment.red_flags:
            return False
        
        # Need at least some mitigating factors
        if not risk_assessment.mitigating_factors:
            return False
        
        # Risk score must be below 0.65
        if risk_assessment.overall_risk_score >= 0.65:
            return False
        
        return True
    
    def _generate_rejection_recommendations(self, risk_assessment: RiskAssessment) -> List[str]:
        """Generate recommendations for rejected applications."""
        recommendations = []
        
        if risk_assessment.credit_score < 650:
            recommendations.append("Improve credit score to at least 650")
        
        if risk_assessment.ltv_ratio > 0.90:
            recommendations.append("Increase down payment to achieve LTV below 80%")
        
        if risk_assessment.dti_ratio > 0.43:
            recommendations.append("Reduce monthly debt obligations")
        
        recommendations.append("Consider applying for a smaller loan amount")
        recommendations.append("Wait 6-12 months and reapply with improved financial profile")
        
        return recommendations
    
    def _get_standard_documents(self, loan_type: LoanType) -> List[str]:
        """Get standard required documents by loan type."""
        base_docs = [
            "Government-issued photo ID",
            "Proof of income (last 2 paystubs)",
            "Bank statements (last 3 months)",
            "Tax returns (last 2 years)"
        ]
        
        if loan_type == LoanType.MORTGAGE:
            base_docs.extend([
                "Property appraisal report",
                "Homeowners insurance quote",
                "Property deed or title"
            ])
        elif loan_type == LoanType.AUTO:
            base_docs.extend([
                "Vehicle title",
                "Auto insurance proof",
                "Vehicle inspection report"
            ])
        elif loan_type == LoanType.EQUIPMENT:
            base_docs.extend([
                "Equipment invoice or purchase agreement",
                "Equipment appraisal",
                "Business financial statements"
            ])
        
        return base_docs
    
    def _get_enhanced_documents(self, loan_type: LoanType) -> List[str]:
        """Get enhanced document requirements for conditional approvals."""
        docs = self._get_standard_documents(loan_type)
        docs.extend([
            "Employment verification letter",
            "Full credit report with explanations",
            "Additional references (3 minimum)",
            "Proof of down payment source"
        ])
        return docs
