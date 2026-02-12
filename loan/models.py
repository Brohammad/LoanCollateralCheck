"""Data models for loan collateral assessment system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import uuid


class LoanType(str, Enum):
    """Types of loans supported."""
    MORTGAGE = "mortgage"
    AUTO = "auto"
    EQUIPMENT = "equipment"
    PERSONAL = "personal"
    BUSINESS = "business"


class CollateralType(str, Enum):
    """Types of collateral assets."""
    REAL_ESTATE = "real_estate"
    VEHICLE = "vehicle"
    EQUIPMENT = "equipment"
    SECURITIES = "securities"
    INVENTORY = "inventory"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"


class LoanStatus(str, Enum):
    """Loan application status."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    VALUATION_PENDING = "valuation_pending"
    RISK_ASSESSMENT = "risk_assessment"
    APPROVED = "approved"
    REJECTED = "rejected"
    MORE_INFO_NEEDED = "more_info_needed"
    MANUAL_REVIEW = "manual_review"
    CLOSED = "closed"


class RiskLevel(str, Enum):
    """Risk level categories."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class DecisionType(str, Enum):
    """Loan decision types."""
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    CONDITIONAL = "conditional"


@dataclass
class Borrower:
    """Borrower information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    ssn_hash: str = ""  # Encrypted/hashed for security
    date_of_birth: Optional[datetime] = None
    credit_score: Optional[int] = None
    annual_income: Optional[float] = None
    employment_status: str = ""
    employer: str = ""
    years_employed: Optional[float] = None
    monthly_debt_payments: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "credit_score": self.credit_score,
            "annual_income": self.annual_income,
            "employment_status": self.employment_status,
            "employer": self.employer,
            "years_employed": self.years_employed
        }


@dataclass
class CollateralAsset:
    """Collateral asset details."""
    type: CollateralType
    details: Dict[str, Any]
    
    # Real estate specific
    address: Optional[str] = None
    property_type: Optional[str] = None  # 'single_family', 'condo', 'multi_family'
    square_feet: Optional[int] = None
    year_built: Optional[int] = None
    
    # Vehicle specific
    vin: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    mileage: Optional[int] = None
    condition: Optional[str] = None  # 'excellent', 'good', 'fair', 'poor'
    
    # Equipment specific
    equipment_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = {
            "type": self.type.value,
            "details": self.details
        }
        
        if self.type == CollateralType.REAL_ESTATE:
            base.update({
                "address": self.address,
                "property_type": self.property_type,
                "square_feet": self.square_feet,
                "year_built": self.year_built
            })
        elif self.type == CollateralType.VEHICLE:
            base.update({
                "vin": self.vin,
                "year": self.year,
                "make": self.make,
                "model": self.model,
                "mileage": self.mileage,
                "condition": self.condition
            })
        elif self.type == CollateralType.EQUIPMENT:
            base.update({
                "equipment_type": self.equipment_type,
                "manufacturer": self.manufacturer,
                "model_number": self.model_number,
                "serial_number": self.serial_number
            })
        
        return base


@dataclass
class LoanApplication:
    """Loan application with collateral."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    borrower_id: str = ""
    borrower: Optional[Borrower] = None
    loan_type: LoanType = LoanType.PERSONAL
    requested_amount: float = 0.0
    loan_purpose: str = ""
    collateral_type: CollateralType = CollateralType.VEHICLE
    collateral: Optional[CollateralAsset] = None
    status: LoanStatus = LoanStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "borrower_id": self.borrower_id,
            "borrower": self.borrower.to_dict() if self.borrower else None,
            "loan_type": self.loan_type.value,
            "requested_amount": self.requested_amount,
            "loan_purpose": self.loan_purpose,
            "collateral_type": self.collateral_type.value,
            "collateral": self.collateral.to_dict() if self.collateral else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class CollateralValuation:
    """Collateral valuation result."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    application_id: str = ""
    asset_type: CollateralType = CollateralType.VEHICLE
    source: str = ""  # 'zillow', 'edmunds', 'manual', 'aggregated'
    estimated_value: float = 0.0
    low_estimate: Optional[float] = None
    high_estimate: Optional[float] = None
    confidence_score: float = 0.0  # 0-1
    valuation_date: datetime = field(default_factory=datetime.now)
    comparable_sales: List[Dict[str, Any]] = field(default_factory=list)
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "application_id": self.application_id,
            "asset_type": self.asset_type.value,
            "source": self.source,
            "estimated_value": self.estimated_value,
            "low_estimate": self.low_estimate,
            "high_estimate": self.high_estimate,
            "confidence_score": self.confidence_score,
            "valuation_date": self.valuation_date.isoformat(),
            "comparable_sales": self.comparable_sales,
            "market_conditions": self.market_conditions,
            "details": self.details
        }


@dataclass
class RiskAssessment:
    """Risk assessment for loan application."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    application_id: str = ""
    
    # Key ratios
    ltv_ratio: float = 0.0  # Loan-to-Value
    dti_ratio: float = 0.0  # Debt-to-Income
    credit_score: int = 0
    
    # Risk scores (0-1, higher = more risk)
    credit_risk_score: float = 0.0
    collateral_risk_score: float = 0.0
    market_risk_score: float = 0.0
    overall_risk_score: float = 0.0
    
    # Risk level
    risk_level: RiskLevel = RiskLevel.MEDIUM
    
    # Analysis details
    risk_factors: List[str] = field(default_factory=list)
    mitigating_factors: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "application_id": self.application_id,
            "ltv_ratio": self.ltv_ratio,
            "dti_ratio": self.dti_ratio,
            "credit_score": self.credit_score,
            "credit_risk_score": self.credit_risk_score,
            "collateral_risk_score": self.collateral_risk_score,
            "market_risk_score": self.market_risk_score,
            "overall_risk_score": self.overall_risk_score,
            "risk_level": self.risk_level.value,
            "risk_factors": self.risk_factors,
            "mitigating_factors": self.mitigating_factors,
            "red_flags": self.red_flags,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class LoanDecision:
    """Loan approval/rejection decision."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    application_id: str = ""
    decision: DecisionType = DecisionType.MANUAL_REVIEW
    confidence: float = 0.0  # 0-1
    
    # Decision details
    reasoning: str = ""
    key_factors: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    
    # Approved loan terms (if approved)
    approved_amount: Optional[float] = None
    interest_rate: Optional[float] = None
    term_months: Optional[int] = None
    monthly_payment: Optional[float] = None
    
    # Additional requirements
    required_documents: List[str] = field(default_factory=list)
    required_actions: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"  # 'system' or user_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "application_id": self.application_id,
            "decision": self.decision.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "key_factors": self.key_factors,
            "conditions": self.conditions,
            "approved_amount": self.approved_amount,
            "interest_rate": self.interest_rate,
            "term_months": self.term_months,
            "monthly_payment": self.monthly_payment,
            "required_documents": self.required_documents,
            "required_actions": self.required_actions,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by
        }


@dataclass
class DocumentUpload:
    """Loan document upload."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    application_id: str = ""
    document_type: str = ""  # 'deed', 'title', 'paystub', 'tax_return', 'appraisal'
    file_path: str = ""
    file_name: str = ""
    file_size: int = 0
    mime_type: str = ""
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    verified: bool = False
    verification_notes: str = ""
    uploaded_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None


@dataclass
class ComplianceCheck:
    """Regulatory compliance check."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    application_id: str = ""
    check_type: str = ""  # 'state_regulation', 'federal_regulation', 'lending_limit'
    regulation_name: str = ""
    passed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    checked_at: datetime = field(default_factory=datetime.now)
