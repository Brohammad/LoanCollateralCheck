"""Quick test of decision engine functionality."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loan.models import (
    RiskLevel, RiskAssessment, LoanApplication, Borrower, 
    LoanType, CollateralType, CollateralAsset, CollateralValuation
)
from loan.decision import DecisionEngine


async def test_decision():
    """Test decision engine with mock data."""
    print("Testing Decision Engine...")
    
    # Create simple borrower
    borrower = Borrower(
        first_name="Test",
        last_name="User",
        credit_score=750,
        annual_income=80000,
        monthly_debt_payments=2000
    )
    
    # Create simple collateral
    collateral = CollateralAsset(
        type=CollateralType.VEHICLE,
        year=2020,
        make="Honda",
        model="Accord",
        details={}
    )
    
    # Create application
    application = LoanApplication(
        borrower_id=borrower.id,
        borrower=borrower,
        loan_type=LoanType.AUTO,
        requested_amount=20000,
        collateral_type=CollateralType.VEHICLE,
        collateral=collateral
    )
    
    # Create mock valuation
    valuation = CollateralValuation(
        application_id=application.id,
        asset_type=CollateralType.VEHICLE,
        source="mock",
        estimated_value=30000.0,  # Vehicle worth $30K
        confidence_score=0.90
    )
    
    # Create mock risk assessment (LOW RISK - should approve)
    risk_assessment = RiskAssessment(
        application_id=application.id,
        overall_risk_score=0.25,  # Low risk
        risk_level=RiskLevel.LOW,
        ltv_ratio=0.67,  # 67% LTV ($20K/$30K)
        dti_ratio=0.30,  # 30% DTI
        credit_risk_score=0.15,
        collateral_risk_score=0.20,
        market_risk_score=0.30,
        risk_factors=["Minor market volatility"],
        red_flags=[]
    )
    
    # Make decision
    print(f"\n📊 Risk Assessment:")
    print(f"   Overall Risk: {risk_assessment.overall_risk_score:.3f}")
    print(f"   Risk Level: {risk_assessment.risk_level.value}")
    print(f"   LTV: {risk_assessment.ltv_ratio:.1%}")
    print(f"   DTI: {risk_assessment.dti_ratio:.1%}")
    
    print(f"\n💵 Valuation:")
    print(f"   Estimated Value: ${valuation.estimated_value:,.2f}")
    print(f"   Confidence: {valuation.confidence_score:.1%}")
    
    decision_engine = DecisionEngine()
    decision = decision_engine.make_decision(application, risk_assessment, valuation)
    
    print(f"\n✅ Decision: {decision.decision.value.upper()}")
    print(f"   Approved Amount: ${decision.approved_amount:,.2f}")
    print(f"   Interest Rate: {decision.interest_rate:.2f}%")
    if hasattr(decision, 'monthly_payment') and decision.monthly_payment:
        print(f"   Monthly Payment: ${decision.monthly_payment:.2f}")
    if hasattr(decision, 'term_months') and decision.term_months:
        print(f"   Loan Term: {decision.term_months} months")
    
    print(f"\n📝 Key Factors:")
    for factor in decision.key_factors[:3]:
        print(f"   • {factor}")
    
    print(f"\n🔍 Reasoning:")
    print(f"   {decision.reasoning[:200]}...")
    
    print("\n✅ Decision engine test completed!")


if __name__ == "__main__":
    asyncio.run(test_decision())
