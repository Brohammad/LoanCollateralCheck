"""AI-powered loan decision explainer using Google Gemini.

Generates human-readable explanations for loan decisions using
advanced language models.
"""

import logging
from typing import Dict, Any, Optional, List
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.gemini_client import GeminiClient
from app.config import Config
from ..models import LoanDecision, RiskAssessment, LoanApplication

logger = logging.getLogger(__name__)


class DecisionExplainer:
    """Generate AI-powered explanations for loan decisions."""
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """Initialize explainer with Gemini client.
        
        Args:
            gemini_api_key: Optional Gemini API key (uses config if not provided)
        """
        api_key = gemini_api_key or Config.GOOGLE_API_KEY
        self.gemini_client = GeminiClient(api_key=api_key)
        self.enabled = bool(api_key)
        
        if not self.enabled:
            logger.warning("Gemini API key not configured - explanations will be basic")
    
    async def explain_decision(
        self,
        decision: LoanDecision,
        application: LoanApplication,
        risk_assessment: RiskAssessment
    ) -> str:
        """Generate detailed explanation for loan decision.
        
        Args:
            decision: Loan decision
            application: Loan application
            risk_assessment: Risk assessment
            
        Returns:
            Human-readable explanation
        """
        if not self.enabled:
            return self._generate_basic_explanation(decision, risk_assessment)
        
        try:
            prompt = self._build_explanation_prompt(decision, application, risk_assessment)
            
            explanation = await self.gemini_client.generate_async(
                prompt=prompt,
                temperature=0.3,  # Lower temperature for more factual
                max_tokens=800
            )
            
            return explanation
            
        except Exception as e:
            logger.error(f"AI explanation failed: {e}", exc_info=True)
            return self._generate_basic_explanation(decision, risk_assessment)
    
    async def explain_to_borrower(
        self,
        decision: LoanDecision,
        application: LoanApplication,
        risk_assessment: RiskAssessment
    ) -> str:
        """Generate borrower-friendly explanation (non-technical).
        
        Args:
            decision: Loan decision
            application: Loan application
            risk_assessment: Risk assessment
            
        Returns:
            Simple, borrower-friendly explanation
        """
        if not self.enabled:
            return self._generate_borrower_explanation(decision, risk_assessment)
        
        try:
            prompt = f"""You are a friendly loan officer explaining a loan decision to a borrower.

Loan Application:
- Loan Type: {application.loan_type.value}
- Requested Amount: ${application.requested_amount:,.2f}
- Decision: {decision.decision.value}

Risk Assessment:
- Credit Score: {risk_assessment.credit_score}
- LTV Ratio: {risk_assessment.ltv_ratio:.1%}
- DTI Ratio: {risk_assessment.dti_ratio:.1%}
- Risk Level: {risk_assessment.risk_level.value}

Decision Details:
- Reasoning: {decision.reasoning}
- Key Factors: {', '.join(decision.key_factors[:3])}

Write a warm, supportive explanation (2-3 paragraphs) that:
1. Explains the decision in simple terms (avoid jargon)
2. If approved: Congratulates and explains next steps
3. If rejected: Is empathetic and offers constructive advice
4. Focuses on what the borrower can control

Keep it positive, professional, and encouraging."""

            explanation = await self.gemini_client.generate_async(
                prompt=prompt,
                temperature=0.5,
                max_tokens=600
            )
            
            return explanation
            
        except Exception as e:
            logger.error(f"Borrower explanation failed: {e}", exc_info=True)
            return self._generate_borrower_explanation(decision, risk_assessment)
    
    async def suggest_improvements(
        self,
        risk_assessment: RiskAssessment,
        application: LoanApplication
    ) -> Dict[str, Any]:
        """Suggest specific improvements for rejected/conditional applications.
        
        Args:
            risk_assessment: Risk assessment
            application: Loan application
            
        Returns:
            Dict with improvement suggestions
        """
        if not self.enabled:
            return self._generate_basic_suggestions(risk_assessment)
        
        try:
            prompt = f"""As a financial advisor, analyze this loan application and provide specific, actionable improvement suggestions.

Application Details:
- Loan Type: {application.loan_type.value}
- Requested: ${application.requested_amount:,.2f}
- Credit Score: {risk_assessment.credit_score}
- LTV Ratio: {risk_assessment.ltv_ratio:.1%}
- DTI Ratio: {risk_assessment.dti_ratio:.1%}
- Risk Score: {risk_assessment.overall_risk_score:.3f}

Risk Factors:
{chr(10).join(f'- {factor}' for factor in risk_assessment.risk_factors[:5])}

Provide 3-5 specific, actionable suggestions with:
1. What to improve
2. Target goal (specific number)
3. Estimated timeline
4. How it will help

Format as a bulleted list. Be specific with numbers and timelines."""

            suggestions = await self.gemini_client.generate_async(
                prompt=prompt,
                temperature=0.4,
                max_tokens=500
            )
            
            return {
                "suggestions": suggestions,
                "priority_areas": self._identify_priority_areas(risk_assessment),
                "estimated_timeline": "6-12 months"
            }
            
        except Exception as e:
            logger.error(f"Suggestion generation failed: {e}", exc_info=True)
            return self._generate_basic_suggestions(risk_assessment)
    
    def _build_explanation_prompt(
        self,
        decision: LoanDecision,
        application: LoanApplication,
        risk_assessment: RiskAssessment
    ) -> str:
        """Build prompt for AI explanation generation."""
        return f"""You are an expert loan underwriter explaining a loan decision. Provide a clear, professional explanation.

Application Summary:
- Loan Type: {application.loan_type.value}
- Requested Amount: ${application.requested_amount:,.2f}
- Borrower Credit Score: {risk_assessment.credit_score}

Risk Assessment Results:
- Overall Risk Score: {risk_assessment.overall_risk_score:.3f}
- Risk Level: {risk_assessment.risk_level.value}
- LTV Ratio: {risk_assessment.ltv_ratio:.1%}
- DTI Ratio: {risk_assessment.dti_ratio:.1%}
- Credit Risk: {risk_assessment.credit_risk_score:.3f}
- Market Risk: {risk_assessment.market_risk_score:.3f}

Decision: {decision.decision.value.upper()}
{f"Approved Amount: ${decision.approved_amount:,.2f}" if decision.approved_amount else ""}
{f"Interest Rate: {decision.interest_rate}% APR" if decision.interest_rate else ""}

Key Factors:
{chr(10).join(f'- {factor}' for factor in decision.key_factors)}

Provide a detailed 3-paragraph explanation:
1. Summary of the decision and primary reasoning
2. Analysis of key financial metrics and their impact
3. Next steps or recommendations

Use professional but accessible language. Include specific numbers and metrics."""
    
    def _generate_basic_explanation(
        self,
        decision: LoanDecision,
        risk_assessment: RiskAssessment
    ) -> str:
        """Generate basic explanation without AI."""
        return decision.reasoning
    
    def _generate_borrower_explanation(
        self,
        decision: LoanDecision,
        risk_assessment: RiskAssessment
    ) -> str:
        """Generate simple borrower explanation without AI."""
        if decision.decision.value == "approved":
            return f"""Congratulations! Your loan application has been approved.

We've reviewed your application and financial profile, and we're pleased to offer you a loan. Your credit score of {risk_assessment.credit_score} and strong financial position make you a qualified borrower.

Next steps: Please review the loan terms and submit the required documentation. We'll be in touch within 2 business days to finalize the details."""
        
        elif decision.decision.value == "rejected":
            return f"""Thank you for your loan application. After careful review, we're unable to approve your application at this time.

Our decision was based on several factors, including your current credit profile and the loan-to-collateral ratio. We encourage you to work on improving your credit score and reducing existing debt.

We'd be happy to reconsider your application in 6-12 months. Please contact us if you have any questions."""
        
        else:
            return f"""We've reviewed your loan application and it requires additional review by our underwriting team.

Your application shows both strengths and areas that need closer evaluation. We'll have a decision for you within 2-3 business days.

Thank you for your patience as we complete our review."""
    
    def _generate_basic_suggestions(
        self,
        risk_assessment: RiskAssessment
    ) -> Dict[str, Any]:
        """Generate basic improvement suggestions without AI."""
        suggestions = []
        
        if risk_assessment.credit_score < 680:
            suggestions.append(
                f"Improve credit score from {risk_assessment.credit_score} to 680+ "
                "(6-12 months by paying bills on time)"
            )
        
        if risk_assessment.ltv_ratio > 0.80:
            suggestions.append(
                f"Reduce LTV ratio from {risk_assessment.ltv_ratio:.1%} to below 80% "
                "by increasing down payment"
            )
        
        if risk_assessment.dti_ratio > 0.40:
            suggestions.append(
                f"Reduce DTI ratio from {risk_assessment.dti_ratio:.1%} to below 40% "
                "by paying down existing debt"
            )
        
        return {
            "suggestions": "\n".join(f"• {s}" for s in suggestions),
            "priority_areas": self._identify_priority_areas(risk_assessment),
            "estimated_timeline": "6-12 months"
        }
    
    def _identify_priority_areas(
        self,
        risk_assessment: RiskAssessment
    ) -> List[str]:
        """Identify priority improvement areas."""
        priorities = []
        
        if risk_assessment.credit_risk_score > 0.5:
            priorities.append("Credit improvement")
        
        if risk_assessment.collateral_risk_score > 0.6:
            priorities.append("Down payment increase")
        
        if risk_assessment.dti_ratio > 0.43:
            priorities.append("Debt reduction")
        
        return priorities or ["General financial profile improvement"]
