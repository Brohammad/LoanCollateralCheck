"""Demo of the complete loan decision pipeline with AI explanations.

Shows end-to-end workflow: Application → Valuation → Risk Assessment → Decision → AI Explanation
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loan.models import (
    LoanApplication, Borrower, CollateralAsset,
    LoanType, CollateralType
)
from loan.valuation.aggregator import ValuationAggregator
from loan.risk.risk_engine import RiskEngine
from loan.decision import DecisionEngine, DecisionExplainer


async def demo_approved_mortgage():
    """Demo: High-quality mortgage - should be approved."""
    print("=" * 80)
    print("DEMO 1: HIGH-QUALITY MORTGAGE APPLICATION")
    print("=" * 80)
    
    # Create borrower with strong profile
    borrower = Borrower(
        id="B001",
        first_name="Sarah",
        last_name="Johnson",
        email="sarah.j@example.com",
        phone="555-0123",
        ssn_hash="hashed-ssn-123",
        date_of_birth=datetime(1985, 6, 15),
        annual_income=120000.0,
        employment_status="employed",
        employer="Tech Corp",
        years_employed=5.0,
        credit_score=780,
        monthly_debt_payments=2000.0
    )
    
    # Create high-value property collateral
    collateral = CollateralAsset(
        type=CollateralType.REAL_ESTATE,
        details={
            "property_type": "single_family",
            "beds": 3,
            "baths": 2,
            "square_feet": 2000
        },
        address="123 Oak Street, Springfield, IL 62701",
        property_type="single_family",
        year_built=2015,
        square_feet=2000,
        condition="good"
    )
    
    # Create loan application for 75% LTV
    application = LoanApplication(
        id="APP001",
        borrower_id="B001",
        loan_type=LoanType.MORTGAGE,
        requested_amount=300000.0,
        collateral=collateral,
        purpose="Purchase primary residence"
    )
    
    print(f"\n📋 Application Details:")
    print(f"   Borrower: {borrower.first_name} {borrower.last_name}")
    print(f"   Credit Score: {borrower.credit_score}")
    print(f"   Annual Income: ${borrower.annual_income:,.0f}")
    print(f"   Requested: ${application.requested_amount:,.0f}")
    print(f"   Property: {collateral.property_type} at {collateral.address}")
    
    # Step 1: Valuation
    print(f"\n🔍 Step 1: Valuing Collateral...")
    valuator = ValuationAggregator()
    valuation = await valuator.valuate_collateral(collateral)
    
    print(f"   Final Value: ${valuation.final_value:,.2f}")
    print(f"   Confidence: {valuation.confidence_score:.1%}")
    print(f"   Sources: {', '.join(valuation.data_sources)}")
    
    # Step 2: Risk Assessment
    print(f"\n⚖️  Step 2: Assessing Risk...")
    risk_engine = RiskEngine()
    risk_assessment = await risk_engine.assess_application_risk(
        application, valuation
    )
    
    print(f"   Risk Level: {risk_assessment.risk_level.value.upper()}")
    print(f"   Overall Score: {risk_assessment.overall_risk_score:.3f}")
    print(f"   LTV Ratio: {risk_assessment.ltv_ratio:.1%}")
    print(f"   DTI Ratio: {risk_assessment.dti_ratio:.1%}")
    
    # Step 3: Decision
    print(f"\n✅ Step 3: Making Decision...")
    decision_engine = DecisionEngine()
    decision = await decision_engine.make_decision(application, risk_assessment)
    
    print(f"   Decision: {decision.decision.value.upper()}")
    if decision.approved_amount:
        print(f"   Approved Amount: ${decision.approved_amount:,.2f}")
    if decision.interest_rate:
        print(f"   Interest Rate: {decision.interest_rate:.2f}% APR")
    if decision.monthly_payment:
        print(f"   Monthly Payment: ${decision.monthly_payment:,.2f}")
    
    print(f"\n   Key Factors:")
    for factor in decision.key_factors[:3]:
        print(f"   • {factor}")
    
    # Step 4: AI Explanation
    print(f"\n🤖 Step 4: Generating AI Explanation...")
    explainer = DecisionExplainer()
    
    if explainer.enabled:
        # Technical explanation
        tech_explanation = await explainer.explain_decision(
            decision, application, risk_assessment
        )
        print(f"\n   Technical Explanation:")
        print(f"   {tech_explanation[:300]}...")
        
        # Borrower-friendly explanation
        borrower_explanation = await explainer.explain_to_borrower(
            decision, application, risk_assessment
        )
        print(f"\n   Borrower Explanation:")
        print(f"   {borrower_explanation[:300]}...")
    else:
        print(f"   ⚠️  AI explanations disabled (no Gemini API key)")
        print(f"   Basic reasoning: {decision.reasoning}")
    
    print("\n" + "=" * 80 + "\n")


async def demo_rejected_auto():
    """Demo: High-risk auto loan - should be rejected."""
    print("=" * 80)
    print("DEMO 2: HIGH-RISK AUTO LOAN APPLICATION")
    print("=" * 80)
    
    # Create borrower with weak profile
    borrower = Borrower(
        borrower_id="B002",
        first_name="Mike",
        last_name="Smith",
        email="mike.s@example.com",
        phone="555-0456",
        ssn="987-65-4321",
        date_of_birth=datetime(1995, 3, 20).date(),
        annual_income=Decimal("35000"),
        employment_status="employed",
        employer_name="Retail Store",
        years_employed=1,
        credit_score=590,
        existing_debt=Decimal("22000")
    )
    
    # Create vehicle collateral
    collateral = CollateralAsset(
        type=CollateralType.VEHICLE,
        details={
            "type": "car",
            "trim": "LX"
        },
        vin="1HGBH41JXMN109186",
        year=2015,
        make="Honda",
        model="Civic",
        mileage=95000,
        condition="fair"
    )
    
    # Create loan application - requesting more than value
    application = LoanApplication(
        application_id="APP002",
        borrower=borrower,
        loan_type=LoanType.AUTO,
        requested_amount=Decimal("18000"),
        collateral=collateral,
        purpose="Purchase used vehicle"
    )
    
    print(f"\n📋 Application Details:")
    print(f"   Borrower: {borrower.first_name} {borrower.last_name}")
    print(f"   Credit Score: {borrower.credit_score}")
    print(f"   Annual Income: ${borrower.annual_income:,.0f}")
    print(f"   Requested: ${application.requested_amount:,.0f}")
    print(f"   Vehicle: {collateral.year} {collateral.make} {collateral.model}, {collateral.mileage:,} miles")
    
    # Step 1: Valuation
    print(f"\n🔍 Step 1: Valuing Collateral...")
    valuator = ValuationAggregator()
    valuation = await valuator.valuate_collateral(collateral)
    
    print(f"   Final Value: ${valuation.final_value:,.2f}")
    print(f"   Confidence: {valuation.confidence_score:.1%}")
    
    # Step 2: Risk Assessment
    print(f"\n⚖️  Step 2: Assessing Risk...")
    risk_engine = RiskEngine()
    risk_assessment = await risk_engine.assess_application_risk(
        application, valuation
    )
    
    print(f"   Risk Level: {risk_assessment.risk_level.value.upper()}")
    print(f"   Overall Score: {risk_assessment.overall_risk_score:.3f}")
    print(f"   LTV Ratio: {risk_assessment.ltv_ratio:.1%}")
    print(f"   DTI Ratio: {risk_assessment.dti_ratio:.1%}")
    
    # Step 3: Decision
    print(f"\n❌ Step 3: Making Decision...")
    decision_engine = DecisionEngine()
    decision = await decision_engine.make_decision(application, risk_assessment)
    
    print(f"   Decision: {decision.decision.value.upper()}")
    print(f"\n   Key Factors:")
    for factor in decision.key_factors[:3]:
        print(f"   • {factor}")
    
    # Step 4: AI Explanation & Suggestions
    print(f"\n🤖 Step 4: Generating Improvement Suggestions...")
    explainer = DecisionExplainer()
    
    if explainer.enabled:
        suggestions = await explainer.suggest_improvements(
            risk_assessment, application
        )
        print(f"\n   Suggestions:")
        print(f"   {suggestions['suggestions'][:400]}...")
        print(f"\n   Priority Areas: {', '.join(suggestions['priority_areas'])}")
    else:
        print(f"   ⚠️  AI suggestions disabled (no Gemini API key)")
        print(f"   Basic reasoning: {decision.reasoning}")
    
    print("\n" + "=" * 80 + "\n")


async def demo_conditional_equipment():
    """Demo: Borderline equipment loan - conditional approval."""
    print("=" * 80)
    print("DEMO 3: BORDERLINE EQUIPMENT LOAN - CONDITIONAL APPROVAL")
    print("=" * 80)
    
    # Create borrower with medium profile
    borrower = Borrower(
        borrower_id="B003",
        first_name="Lisa",
        last_name="Chen",
        email="lisa.c@example.com",
        phone="555-0789",
        ssn="456-78-9012",
        date_of_birth=datetime(1982, 11, 8).date(),
        annual_income=Decimal("75000"),
        employment_status="self_employed",
        employer_name="Chen Landscaping LLC",
        years_employed=3,
        credit_score=680,
        existing_debt=Decimal("32000")
    )
    
    # Create equipment collateral
    collateral = CollateralAsset(
        type=CollateralType.EQUIPMENT,
        details={
            "hours_used": 1200,
            "category": "construction"
        },
        equipment_type="excavator",
        manufacturer="John Deere",
        model_number="350G",
        serial_number="JD350G-2020-1234",
        year_built=2020,
        condition="good"
    )
    
    # Create loan application
    application = LoanApplication(
        application_id="APP003",
        borrower=borrower,
        loan_type=LoanType.EQUIPMENT,
        requested_amount=Decimal("60000"),
        collateral=collateral,
        purpose="Expand landscaping business"
    )
    
    print(f"\n📋 Application Details:")
    print(f"   Borrower: {borrower.first_name} {borrower.last_name}")
    print(f"   Credit Score: {borrower.credit_score}")
    print(f"   Annual Income: ${borrower.annual_income:,.0f}")
    print(f"   Requested: ${application.requested_amount:,.0f}")
    print(f"   Equipment: {collateral.manufacturer} {collateral.model_number} ({collateral.equipment_type})")
    
    # Run full pipeline
    print(f"\n🔄 Running Full Pipeline...")
    
    valuator = ValuationAggregator()
    valuation = await valuator.valuate_collateral(collateral)
    
    risk_engine = RiskEngine()
    risk_assessment = await risk_engine.assess_application_risk(
        application, valuation
    )
    
    decision_engine = DecisionEngine()
    decision = await decision_engine.make_decision(application, risk_assessment)
    
    print(f"\n   Decision: {decision.decision.value.upper()}")
    print(f"   Risk Score: {risk_assessment.overall_risk_score:.3f}")
    
    if decision.conditions:
        print(f"\n   Conditions:")
        for condition in decision.conditions:
            print(f"   • {condition}")
    
    if decision.required_documents:
        print(f"\n   Required Documents:")
        for doc in decision.required_documents[:3]:
            print(f"   • {doc}")
    
    print("\n" + "=" * 80 + "\n")


async def main():
    """Run all demos."""
    print("\n" + "🏦" * 40)
    print("LOAN DECISION ENGINE - COMPLETE DEMO")
    print("🏦" * 40 + "\n")
    
    try:
        # Demo 1: Approved mortgage
        await demo_approved_mortgage()
        await asyncio.sleep(1)
        
        # Demo 2: Rejected auto loan
        await demo_rejected_auto()
        await asyncio.sleep(1)
        
        # Demo 3: Conditional equipment loan
        await demo_conditional_equipment()
        
        print("✅ All demos completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
