# Loan Collateral System - Migration Plan
**Date**: February 12, 2026  
**Strategy**: Hybrid Approach (Keep Infrastructure, Replace Business Logic)  
**Timeline**: 10-12 weeks to production

---

## Executive Summary

### What We're Keeping (80% - Production Ready)
✅ **Security Layer** (`security/`) - 2,500+ lines  
✅ **Monitoring** (`monitoring/`) - 2,650+ lines  
✅ **Deployment** (`k8s/`, `helm/`, `docker-compose.yml`) - Complete  
✅ **Testing Framework** (`tests/integration/`) - 150+ tests  
✅ **CI/CD** (`.github/workflows/`) - Automated pipelines  
✅ **Database Layer** (`database/db_manager.py`) - Connection pooling, transactions  
✅ **Cost Tracking** (`cost_analysis/`) - Complete system  

### What We're Replacing (20% - Domain Specific)
🔄 **Generic Routing** → Loan workflow orchestration  
🔄 **LinkedIn Features** → Collateral valuation  
🔄 **General Agents** → Loan decision engines  
🔄 **Chat Intents** → Loan application processing  

---

## Phase 1: Assessment & Setup (Week 1)

### Files to Keep (No Changes)
```
security/                    # Complete security implementation
monitoring/                  # Metrics, logging, tracing
tests/integration/           # Test framework (update tests only)
.github/workflows/           # CI/CD pipelines
k8s/                        # Kubernetes configs
helm/                       # Helm charts
docker-compose.yml          # Container orchestration
cost_analysis/              # Cost tracking
database/db_manager.py      # Database connection management
app/config.py               # Configuration (update API key only)
app/gemini_client.py        # Gemini API client (reuse)
app/database.py             # Database utilities
requirements.txt            # Dependencies (add loan-specific)
```

### Files to Archive (Move to `archive/v1-generic/`)
```
routing/                    # Generic intent routing
linkedin/                   # LinkedIn features
examples/demo.py            # Generic demo
app/agents/                 # Generic agent implementations
app/orchestrator.py         # Generic orchestrator (replace with loan version)
langflow_flows/             # Generic workflows
```

### Files to Replace/Update
```
app/main.py                 # Update endpoints for loan API
app/orchestrator.py         # Create loan-specific orchestrator
database/schema.sql         # Add loan tables
README.md                   # Update documentation
```

### New Directory Structure
```
loan/                       # NEW: Loan-specific modules
├── __init__.py
├── models.py              # Data models (LoanApplication, Collateral, etc.)
├── valuation/             # Collateral valuation
│   ├── __init__.py
│   ├── zillow_client.py   # Real estate valuation
│   ├── edmunds_client.py  # Vehicle valuation
│   ├── equipment_client.py # Equipment appraisal
│   └── aggregator.py      # Multi-source aggregation
├── risk/                  # Risk assessment
│   ├── __init__.py
│   ├── ltv_calculator.py  # Loan-to-value ratio
│   ├── credit_scorer.py   # Credit risk analysis
│   ├── market_risk.py     # Market conditions
│   └── risk_engine.py     # Combined risk score
├── documents/             # Document processing
│   ├── __init__.py
│   ├── ocr_processor.py   # OCR extraction
│   ├── entity_extractor.py # Extract key data
│   ├── verifier.py        # Verify authenticity
│   └── parsers/           # Document type parsers
│       ├── deed_parser.py
│       ├── title_parser.py
│       └── appraisal_parser.py
├── compliance/            # Regulatory compliance
│   ├── __init__.py
│   ├── regulation_checker.py # State/federal rules
│   ├── audit_trail.py     # Compliance logging
│   └── rules/             # Rule definitions
│       ├── state_rules.py
│       └── federal_rules.py
├── decision/              # Loan decision engine
│   ├── __init__.py
│   ├── engine.py          # Approval/rejection logic
│   ├── explainer.py       # Decision reasoning
│   └── confidence.py      # Confidence scoring
└── orchestrator.py        # Loan workflow orchestrator
```

---

## Phase 2: Core Infrastructure Setup (Week 2)

### Task 2.1: Configure API Keys
**File**: `app/config.py`
```python
# Add loan-specific configuration
GOOGLE_API_KEY = "AIzaSyCG1HOOoMKUtY1IBltfYUfoPpdgAwC5-m8"

# Collateral valuation APIs
ZILLOW_API_KEY: str = os.environ.get("ZILLOW_API_KEY", "")
EDMUNDS_API_KEY: str = os.environ.get("EDMUNDS_API_KEY", "")
CARFAX_API_KEY: str = os.environ.get("CARFAX_API_KEY", "")

# Document processing
GOOGLE_VISION_API_KEY: str = os.environ.get("GOOGLE_VISION_API_KEY", "")

# Credit data
EXPERIAN_API_KEY: str = os.environ.get("EXPERIAN_API_KEY", "")
EQUIFAX_API_KEY: str = os.environ.get("EQUIFAX_API_KEY", "")

# Loan-specific settings
LTV_MAX_RATIO: float = float(os.environ.get("LTV_MAX_RATIO", "0.80"))
MIN_CREDIT_SCORE: int = int(os.environ.get("MIN_CREDIT_SCORE", "620"))
MAX_DTI_RATIO: float = float(os.environ.get("MAX_DTI_RATIO", "0.43"))
```

### Task 2.2: Create Base Data Models
**File**: `loan/models.py`
```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

class LoanType(Enum):
    MORTGAGE = "mortgage"
    AUTO = "auto"
    EQUIPMENT = "equipment"
    PERSONAL = "personal"

class CollateralType(Enum):
    REAL_ESTATE = "real_estate"
    VEHICLE = "vehicle"
    EQUIPMENT = "equipment"
    SECURITIES = "securities"

class LoanStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MORE_INFO_NEEDED = "more_info_needed"

@dataclass
class LoanApplication:
    id: str
    borrower_id: str
    loan_type: LoanType
    requested_amount: float
    collateral_type: CollateralType
    collateral_details: Dict[str, Any]
    status: LoanStatus
    created_at: datetime
    updated_at: datetime

@dataclass
class CollateralValuation:
    id: str
    application_id: str
    asset_type: CollateralType
    source: str  # 'zillow', 'edmunds', 'manual'
    estimated_value: float
    confidence_score: float
    valuation_date: datetime
    details: Dict[str, Any]

@dataclass
class RiskAssessment:
    id: str
    application_id: str
    ltv_ratio: float
    credit_score: int
    dti_ratio: float
    market_risk_score: float
    overall_risk_score: float
    risk_level: str  # 'low', 'medium', 'high'
    created_at: datetime

@dataclass
class LoanDecision:
    id: str
    application_id: str
    decision: str  # 'approved', 'rejected', 'manual_review'
    confidence: float
    reasoning: str
    conditions: List[str]
    created_at: datetime
```

### Task 2.3: Update Database Schema
**File**: `database/schema.sql`
Add these tables:
```sql
-- Loan applications
CREATE TABLE IF NOT EXISTS loan_applications (
    id TEXT PRIMARY KEY,
    borrower_id TEXT NOT NULL,
    loan_type TEXT NOT NULL,
    requested_amount REAL NOT NULL,
    collateral_type TEXT NOT NULL,
    collateral_details TEXT NOT NULL, -- JSON
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (borrower_id) REFERENCES borrowers(id)
);

-- Borrower information
CREATE TABLE IF NOT EXISTS borrowers (
    id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    ssn_hash TEXT, -- Encrypted/hashed
    credit_score INTEGER,
    annual_income REAL,
    employment_status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Collateral valuations
CREATE TABLE IF NOT EXISTS collateral_valuations (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    source TEXT NOT NULL,
    estimated_value REAL NOT NULL,
    confidence_score REAL NOT NULL,
    valuation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT, -- JSON
    FOREIGN KEY (application_id) REFERENCES loan_applications(id)
);

-- Risk assessments
CREATE TABLE IF NOT EXISTS risk_assessments (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    ltv_ratio REAL NOT NULL,
    credit_score INTEGER NOT NULL,
    dti_ratio REAL NOT NULL,
    market_risk_score REAL NOT NULL,
    overall_risk_score REAL NOT NULL,
    risk_level TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES loan_applications(id)
);

-- Loan decisions
CREATE TABLE IF NOT EXISTS loan_decisions (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    confidence REAL NOT NULL,
    reasoning TEXT NOT NULL,
    conditions TEXT, -- JSON array
    approved_amount REAL,
    interest_rate REAL,
    term_months INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT, -- 'system' or user_id
    FOREIGN KEY (application_id) REFERENCES loan_applications(id)
);

-- Document uploads
CREATE TABLE IF NOT EXISTS loan_documents (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    document_type TEXT NOT NULL, -- 'deed', 'title', 'appraisal', 'paystub', etc.
    file_path TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    extracted_data TEXT, -- JSON
    verified BOOLEAN DEFAULT FALSE,
    verification_notes TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES loan_applications(id)
);

-- Compliance checks
CREATE TABLE IF NOT EXISTS compliance_checks (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    check_type TEXT NOT NULL, -- 'state_regulation', 'federal_regulation', 'lending_limit'
    passed BOOLEAN NOT NULL,
    details TEXT, -- JSON
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES loan_applications(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_loan_app_borrower ON loan_applications(borrower_id);
CREATE INDEX IF NOT EXISTS idx_loan_app_status ON loan_applications(status);
CREATE INDEX IF NOT EXISTS idx_loan_app_created ON loan_applications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_valuation_app ON collateral_valuations(application_id);
CREATE INDEX IF NOT EXISTS idx_risk_app ON risk_assessments(application_id);
CREATE INDEX IF NOT EXISTS idx_decision_app ON loan_decisions(application_id);
CREATE INDEX IF NOT EXISTS idx_documents_app ON loan_documents(application_id);
```

---

## Phase 3: Collateral Valuation Module (Weeks 3-4)

### Task 3.1: Real Estate Valuation (Zillow)
**File**: `loan/valuation/zillow_client.py`
Features:
- Property address lookup
- Zestimate retrieval
- Comparable sales (comps)
- Market trends
- Confidence scoring

### Task 3.2: Vehicle Valuation (Edmunds)
**File**: `loan/valuation/edmunds_client.py`
Features:
- VIN lookup
- True Market Value (TMV)
- Condition assessment
- Mileage adjustment
- Market demand

### Task 3.3: Equipment Valuation
**File**: `loan/valuation/equipment_client.py`
Features:
- Equipment category databases
- Depreciation calculation
- Market research
- Manufacturer data

### Task 3.4: Valuation Aggregator
**File**: `loan/valuation/aggregator.py`
Features:
- Multi-source aggregation
- Weighted averaging
- Confidence scoring
- Fallback logic

---

## Phase 4: Risk Assessment Engine (Weeks 5-6)

### Task 4.1: LTV Calculator
**File**: `loan/risk/ltv_calculator.py`
```python
def calculate_ltv(loan_amount: float, collateral_value: float) -> float:
    """Calculate loan-to-value ratio"""
    return loan_amount / collateral_value

def assess_ltv_risk(ltv_ratio: float, loan_type: LoanType) -> str:
    """Assess risk level based on LTV"""
    # Mortgage: <80% = low, 80-90% = medium, >90% = high
    # Auto: <100% = low, 100-120% = medium, >120% = high
```

### Task 4.2: Credit Risk Scorer
**File**: `loan/risk/credit_scorer.py`
Features:
- FICO score analysis
- Payment history
- Credit utilization
- Recent inquiries
- Risk categorization

### Task 4.3: Market Risk Analyzer
**File**: `loan/risk/market_risk.py`
Features:
- Local market conditions
- Asset type trends
- Economic indicators
- Volatility assessment

### Task 4.4: Combined Risk Engine
**File**: `loan/risk/risk_engine.py`
```python
def calculate_overall_risk(
    ltv_ratio: float,
    credit_score: int,
    dti_ratio: float,
    market_risk: float
) -> RiskAssessment:
    """Combine all risk factors into overall score"""
    # Weighted scoring:
    # LTV: 35%, Credit: 30%, DTI: 20%, Market: 15%
```

---

## Phase 5: Document Verification (Weeks 7-8)

### Task 5.1: OCR Processor
**File**: `loan/documents/ocr_processor.py`
Uses: Google Cloud Vision API
Features:
- PDF/image text extraction
- Form field detection
- Signature detection
- Quality assessment

### Task 5.2: Entity Extractor
**File**: `loan/documents/entity_extractor.py`
Uses: Gemini API for intelligent extraction
Features:
- Name extraction
- Address parsing
- Date recognition
- Amount extraction
- Legal entity identification

### Task 5.3: Document Verifiers
**File**: `loan/documents/verifier.py`
Features:
- Cross-reference validation
- Consistency checks
- Date verification
- Amount matching
- Fraud detection

---

## Phase 6: Decision Engine (Week 9)

### Task 6.1: Approval Logic
**File**: `loan/decision/engine.py`
```python
class LoanDecisionEngine:
    def evaluate_application(
        self,
        application: LoanApplication,
        valuation: CollateralValuation,
        risk: RiskAssessment,
        compliance: List[ComplianceCheck]
    ) -> LoanDecision:
        """Make loan decision based on all factors"""
        
        # Decision rules:
        # 1. All compliance checks must pass
        # 2. Risk score < threshold
        # 3. LTV within limits
        # 4. Credit score meets minimum
        # 5. DTI within acceptable range
```

### Task 6.2: Explainable AI
**File**: `loan/decision/explainer.py`
Uses: Gemini API to generate human-readable explanations
Features:
- Decision reasoning
- Factor analysis
- Improvement suggestions
- Regulatory compliance notes

---

## Phase 7: API Transformation (Week 10)

### Task 7.1: New Loan Endpoints
**File**: `app/main.py`
```python
from fastapi import FastAPI, HTTPException, Depends
from loan.orchestrator import LoanOrchestrator
from loan.models import *

app = FastAPI(title="Loan Collateral Assessment API")

# NEW ENDPOINTS

@app.post("/api/v1/loans/apply")
async def submit_loan_application(
    application: LoanApplication,
    orchestrator: LoanOrchestrator = Depends()
) -> Dict[str, Any]:
    """Submit new loan application"""
    result = await orchestrator.process_application(application)
    return result

@app.post("/api/v1/collateral/valuate")
async def valuate_collateral(
    asset: CollateralAsset,
    orchestrator: LoanOrchestrator = Depends()
) -> CollateralValuation:
    """Get real-time collateral valuation"""
    valuation = await orchestrator.valuate_collateral(asset)
    return valuation

@app.post("/api/v1/documents/upload")
async def upload_document(
    application_id: str,
    document: UploadFile,
    orchestrator: LoanOrchestrator = Depends()
) -> Dict[str, Any]:
    """Upload and verify loan document"""
    result = await orchestrator.process_document(application_id, document)
    return result

@app.get("/api/v1/loans/{loan_id}")
async def get_loan_status(
    loan_id: str,
    orchestrator: LoanOrchestrator = Depends()
) -> LoanApplication:
    """Get loan application status"""
    application = await orchestrator.get_application(loan_id)
    return application

@app.get("/api/v1/loans/{loan_id}/decision")
async def get_loan_decision(
    loan_id: str,
    orchestrator: LoanOrchestrator = Depends()
) -> LoanDecision:
    """Get loan decision with reasoning"""
    decision = await orchestrator.get_decision(loan_id)
    return decision

@app.post("/api/v1/loans/{loan_id}/appeal")
async def appeal_decision(
    loan_id: str,
    appeal: AppealRequest,
    orchestrator: LoanOrchestrator = Depends()
) -> Dict[str, Any]:
    """Appeal a loan decision"""
    result = await orchestrator.process_appeal(loan_id, appeal)
    return result

# KEEP EXISTING INFRASTRUCTURE ENDPOINTS
@app.get("/health")
async def health_check():
    """Health check endpoint (from monitoring)"""
    # Keep existing implementation

@app.get("/metrics")
async def metrics():
    """Prometheus metrics (from monitoring)"""
    # Keep existing implementation

@app.get("/api/v1/cost/summary")
async def cost_summary():
    """Cost tracking (from cost_analysis)"""
    # Keep existing implementation
```

---

## Phase 8: Integration & Testing (Week 11)

### Task 8.1: Update Integration Tests
**File**: `tests/integration/test_loan_workflow.py`
```python
@pytest.mark.asyncio
async def test_complete_loan_workflow(test_client: AsyncClient):
    """Test end-to-end loan application workflow"""
    
    # Step 1: Submit application
    application = {
        "borrower_id": "test_borrower_123",
        "loan_type": "auto",
        "requested_amount": 25000,
        "collateral": {
            "type": "vehicle",
            "vin": "1HGCM82633A123456",
            "year": 2020,
            "make": "Honda",
            "model": "Accord"
        }
    }
    response = await test_client.post("/api/v1/loans/apply", json=application)
    assert response.status_code == 200
    loan_id = response.json()["loan_id"]
    
    # Step 2: Upload documents
    # Step 3: Check valuation
    # Step 4: Check risk assessment
    # Step 5: Get decision
    # Step 6: Verify audit trail
```

### Task 8.2: Performance Tests
Targets:
- Application processing: <30 seconds
- Valuation: <5 seconds
- Document verification: <10 seconds
- Decision generation: <3 seconds

### Task 8.3: Security Tests
Verify:
- PII encryption
- Authentication
- Authorization
- Rate limiting
- Audit logging

---

## Phase 9: Documentation & Deployment (Week 12)

### Task 9.1: Update Documentation
Files to update:
- `README.md` - Loan system overview
- `docs/API_REFERENCE.md` - New endpoints
- `docs/LOAN_PROCESSING.md` - Workflow guide
- `QUICKSTART.md` - Getting started

### Task 9.2: Deploy to Staging
```bash
# Use existing deployment infrastructure
kubectl apply -f k8s/
helm upgrade loan-system helm/ai-agent/
```

### Task 9.3: Smoke Tests in Staging
Validate:
- All endpoints respond
- Database migrations applied
- External APIs connected
- Monitoring active
- Logs flowing

---

## Risk Mitigation

### Technical Risks
1. **External API Failures** → Fallback to cached/manual valuations
2. **Performance Bottlenecks** → Async processing, caching
3. **Data Migration Issues** → Staged rollout, rollback plan
4. **Integration Bugs** → Comprehensive testing, feature flags

### Business Risks
1. **Regulatory Compliance** → Legal review before production
2. **Accuracy Requirements** → A/B testing, gradual rollout
3. **User Adoption** → Training materials, support docs

---

## Success Metrics

### Technical KPIs
- Processing time: <30 seconds (target)
- API uptime: >99.9%
- Error rate: <0.1%
- Cache hit rate: >70%

### Business KPIs
- Valuation accuracy: >95%
- Auto-approval rate: >60%
- False positive rate: <5%
- Manual review rate: <30%

---

## Rollback Plan

### If Issues Arise
1. **Feature Flags**: Disable new loan endpoints
2. **Database Rollback**: Revert schema changes
3. **Code Rollback**: `git revert` to previous version
4. **Communication**: Notify stakeholders immediately

### Rollback Steps
```bash
# 1. Disable new features
kubectl set env deployment/loan-system FEATURE_LOAN_PROCESSING=false

# 2. Rollback deployment
helm rollback loan-system

# 3. Verify old system operational
curl https://api.example.com/health

# 4. Investigate issues
kubectl logs -f deployment/loan-system
```

---

## Next Steps - Immediate Actions

1. ✅ **Archive current routing/linkedin code**
2. ✅ **Update `app/config.py` with new API key**
3. ✅ **Create `loan/` directory structure**
4. ✅ **Implement base data models**
5. ✅ **Update database schema**
6. 🔄 **Start building collateral valuation module**

---

**Status**: Ready to begin implementation  
**Reviewed By**: [To be filled]  
**Approved Date**: [To be filled]
