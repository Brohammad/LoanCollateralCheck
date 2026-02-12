"""
End-to-End Loan Application Workflow Tests

Tests complete loan application workflow including:
- Intent routing
- Authentication
- Credit history check
- Collateral verification
- Document processing
- Cost tracking
- LinkedIn profile analysis
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import components
from routing import IntentClassifier, IntentRouter, RouteRegistry, ContextManager, FallbackHandler
from routing.models import Route, IntentType
from app.main import app


class TestLoanApplicationWorkflow:
    """Complete loan application workflow tests"""
    
    @pytest.fixture
    async def test_client(self):
        """Create test client"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    def user_data(self):
        """Test user data"""
        return {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "name": "Test User",
            "phone": "+1234567890"
        }
    
    @pytest.fixture
    def loan_application_data(self):
        """Test loan application data"""
        return {
            "loan_type": "business",
            "amount": 50000,
            "purpose": "equipment_purchase",
            "term_months": 36,
            "collateral_type": "equipment",
            "collateral_value": 75000
        }
    
    @pytest.mark.asyncio
    async def test_complete_loan_workflow(
        self,
        test_client: AsyncClient,
        user_data: Dict,
        loan_application_data: Dict
    ):
        """
        Test complete loan application workflow from start to finish
        
        Steps:
        1. User authentication
        2. Intent classification (loan application)
        3. Credit history check
        4. Profile analysis (LinkedIn)
        5. Collateral verification
        6. Document upload
        7. Application submission
        8. Cost tracking verification
        """
        
        # Step 1: Authenticate user
        auth_response = await test_client.post("/auth/login", json={
            "email": user_data["email"],
            "password": "test_password"
        })
        assert auth_response.status_code == 200
        token = auth_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Create session
        session_response = await test_client.post(
            "/routing/sessions",
            params={"user_id": user_data["user_id"]},
            headers=headers
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]
        
        # Step 3: Intent classification - loan application
        classify_response = await test_client.post(
            "/routing/classify",
            json={
                "user_input": f"I want to apply for a {loan_application_data['loan_type']} loan of ${loan_application_data['amount']}",
                "session_id": session_id,
                "user_id": user_data["user_id"]
            },
            headers=headers
        )
        assert classify_response.status_code == 200
        intent_data = classify_response.json()
        assert intent_data["intent_type"] == "LOAN_APPLICATION"
        assert intent_data["confidence"] > 0.7
        assert "loan_type" in intent_data["entities"]
        assert "amount" in intent_data["entities"]
        
        # Step 4: Check credit history
        credit_response = await test_client.get(
            f"/credit/history/{user_data['user_id']}",
            headers=headers
        )
        assert credit_response.status_code == 200
        credit_data = credit_response.json()
        assert "credit_score" in credit_data
        assert "payment_history" in credit_data
        
        # Step 5: LinkedIn profile analysis
        linkedin_response = await test_client.post(
            "/linkedin/analyze-profile",
            json={
                "user_id": user_data["user_id"],
                "profile_url": "https://linkedin.com/in/testuser"
            },
            headers=headers
        )
        assert linkedin_response.status_code == 200
        profile_data = linkedin_response.json()
        assert "skills" in profile_data
        assert "employment_stability" in profile_data
        
        # Step 6: Collateral verification
        collateral_response = await test_client.post(
            "/collateral/verify",
            json={
                "user_id": user_data["user_id"],
                "asset_type": loan_application_data["collateral_type"],
                "asset_value": loan_application_data["collateral_value"],
                "description": "Manufacturing equipment"
            },
            headers=headers
        )
        assert collateral_response.status_code == 200
        collateral_data = collateral_response.json()
        assert collateral_data["verified"]
        assert collateral_data["ltv_ratio"] <= 0.8  # Loan-to-value ratio
        
        # Step 7: Document upload
        documents = [
            {"type": "tax_return", "year": 2025},
            {"type": "bank_statement", "months": 3},
            {"type": "business_license", "valid": True}
        ]
        
        for doc in documents:
            doc_response = await test_client.post(
                "/documents/upload",
                json={
                    "user_id": user_data["user_id"],
                    "document_type": doc["type"],
                    "metadata": doc
                },
                headers=headers
            )
            assert doc_response.status_code == 200
        
        # Step 8: Submit loan application
        application_response = await test_client.post(
            "/loans/apply",
            json={
                "user_id": user_data["user_id"],
                "loan_type": loan_application_data["loan_type"],
                "amount": loan_application_data["amount"],
                "purpose": loan_application_data["purpose"],
                "term_months": loan_application_data["term_months"],
                "collateral_id": collateral_data["collateral_id"],
                "credit_check_id": credit_data["check_id"],
                "profile_analysis_id": profile_data["analysis_id"]
            },
            headers=headers
        )
        assert application_response.status_code == 200
        application_data = application_response.json()
        assert application_data["status"] == "pending_review"
        assert "application_id" in application_data
        assert "estimated_decision_time" in application_data
        
        # Step 9: Verify cost tracking
        cost_response = await test_client.get(
            f"/cost-analysis/usage/{user_data['user_id']}",
            params={"session_id": session_id},
            headers=headers
        )
        assert cost_response.status_code == 200
        cost_data = cost_response.json()
        assert cost_data["total_cost"] > 0
        assert "classification_cost" in cost_data
        assert "credit_check_cost" in cost_data
        assert "profile_analysis_cost" in cost_data
        
        # Step 10: Verify intent history
        history_response = await test_client.get(
            "/routing/history",
            params={
                "user_id": user_data["user_id"],
                "session_id": session_id
            },
            headers=headers
        )
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert len(history_data["history"]) > 0
        
        # Verify workflow completed successfully
        assert application_data["status"] in ["pending_review", "approved", "needs_info"]
    
    @pytest.mark.asyncio
    async def test_multi_intent_workflow(
        self,
        test_client: AsyncClient,
        user_data: Dict
    ):
        """
        Test multi-intent handling in workflow
        
        Example: "Check my credit score and help me apply for a loan"
        """
        
        # Authenticate
        auth_response = await test_client.post("/auth/login", json={
            "email": user_data["email"],
            "password": "test_password"
        })
        token = auth_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create session
        session_response = await test_client.post(
            "/routing/sessions",
            params={"user_id": user_data["user_id"]},
            headers=headers
        )
        session_id = session_response.json()["session_id"]
        
        # Classify multi-intent
        classify_response = await test_client.post(
            "/routing/classify-multi",
            json={
                "user_input": "Check my credit score and help me apply for a business loan",
                "session_id": session_id,
                "user_id": user_data["user_id"]
            },
            headers=headers
        )
        assert classify_response.status_code == 200
        multi_intent = classify_response.json()
        
        # Verify multi-intent detection
        assert multi_intent["primary_intent"]["intent_type"] == "CREDIT_HISTORY"
        assert len(multi_intent["secondary_intents"]) > 0
        assert any(
            intent["intent_type"] == "LOAN_APPLICATION"
            for intent in multi_intent["secondary_intents"]
        )
        
        # Execute both intents in order
        for intent_id in multi_intent["execution_order"]:
            # Find intent
            if multi_intent["primary_intent"]["intent_id"] == intent_id:
                intent = multi_intent["primary_intent"]
            else:
                intent = next(
                    i for i in multi_intent["secondary_intents"]
                    if i["intent_id"] == intent_id
                )
            
            # Route intent
            route_response = await test_client.post(
                "/routing/route",
                json={
                    "user_input": intent["user_input"],
                    "session_id": session_id,
                    "user_id": user_data["user_id"],
                    "user_authenticated": True
                },
                headers=headers
            )
            assert route_response.status_code == 200
            assert route_response.json()["success"]
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling(
        self,
        test_client: AsyncClient,
        user_data: Dict
    ):
        """
        Test error handling in workflow
        
        Scenarios:
        - Insufficient credit score
        - Missing documents
        - Invalid collateral
        - Authentication failure
        """
        
        # Test 1: Authentication failure
        with pytest.raises(Exception):
            await test_client.post("/loans/apply", json={
                "user_id": user_data["user_id"],
                "loan_type": "business",
                "amount": 50000
            })  # No auth header
        
        # Authenticate for other tests
        auth_response = await test_client.post("/auth/login", json={
            "email": user_data["email"],
            "password": "test_password"
        })
        token = auth_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 2: Insufficient credit score
        # Mock low credit score
        credit_response = await test_client.get(
            f"/credit/history/{user_data['user_id']}",
            headers=headers
        )
        if credit_response.json().get("credit_score", 700) < 600:
            application_response = await test_client.post(
                "/loans/apply",
                json={
                    "user_id": user_data["user_id"],
                    "loan_type": "business",
                    "amount": 50000
                },
                headers=headers
            )
            assert application_response.status_code in [400, 422]
            assert "credit" in application_response.json()["detail"].lower()
        
        # Test 3: Missing required documents
        incomplete_app_response = await test_client.post(
            "/loans/apply",
            json={
                "user_id": user_data["user_id"],
                "loan_type": "business",
                "amount": 50000,
                # Missing collateral, credit check, documents
            },
            headers=headers
        )
        assert incomplete_app_response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_workflow_with_fallback(
        self,
        test_client: AsyncClient,
        user_data: Dict
    ):
        """
        Test fallback handling in workflow when intent is unclear
        """
        
        # Authenticate
        auth_response = await test_client.post("/auth/login", json={
            "email": user_data["email"],
            "password": "test_password"
        })
        token = auth_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create session
        session_response = await test_client.post(
            "/routing/sessions",
            params={"user_id": user_data["user_id"]},
            headers=headers
        )
        session_id = session_response.json()["session_id"]
        
        # Send unclear intent
        unclear_inputs = [
            "I need help",
            "What can you do?",
            "Tell me more"
        ]
        
        for unclear_input in unclear_inputs:
            route_response = await test_client.post(
                "/routing/route",
                json={
                    "user_input": unclear_input,
                    "session_id": session_id,
                    "user_id": user_data["user_id"],
                    "user_authenticated": True
                },
                headers=headers
            )
            assert route_response.status_code == 200
            result = route_response.json()
            
            # Verify fallback was used
            assert result["success"]
            assert "response" in result
            # Should provide clarification or options
            assert any(keyword in result["response"].lower() for keyword in [
                "help", "clarification", "option", "can", "would you like"
            ])
    
    @pytest.mark.asyncio
    async def test_concurrent_applications(
        self,
        test_client: AsyncClient
    ):
        """
        Test handling multiple concurrent loan applications
        """
        
        async def apply_for_loan(user_id: str):
            # Authenticate
            auth_response = await test_client.post("/auth/login", json={
                "email": f"user{user_id}@example.com",
                "password": "test_password"
            })
            token = auth_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Apply for loan
            response = await test_client.post(
                "/loans/apply",
                json={
                    "user_id": user_id,
                    "loan_type": "personal",
                    "amount": 10000,
                    "purpose": "debt_consolidation",
                    "term_months": 24
                },
                headers=headers
            )
            return response
        
        # Submit 10 concurrent applications
        tasks = [apply_for_loan(f"user_{i}") for i in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all succeeded or failed gracefully
        for response in responses:
            if isinstance(response, Exception):
                # Should be handled gracefully
                assert "rate limit" in str(response).lower() or "concurrent" in str(response).lower()
            else:
                assert response.status_code in [200, 429]  # Success or rate limited
