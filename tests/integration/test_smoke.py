"""
Smoke Tests

Quick smoke tests to verify basic functionality:
- System is up
- Critical paths work
- Core services respond
- Fast execution (<1 minute)
"""

import pytest
from httpx import AsyncClient
from app.main import app


class TestSmokeSuite:
    """Smoke test suite for quick verification"""
    
    @pytest.fixture
    async def test_client(self):
        """Create test client"""
        async with AsyncClient(app=app, base_url="http://test", timeout=10.0) as client:
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_health_endpoint(self, test_client: AsyncClient):
        """Test health endpoint responds"""
        response = await test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_routing_health(self, test_client: AsyncClient):
        """Test routing system health"""
        response = await test_client.get("/routing/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["components"]["classifier"] == True
        assert data["components"]["router"] == True
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_basic_classification(self, test_client: AsyncClient):
        """Test basic intent classification works"""
        response = await test_client.post(
            "/routing/classify",
            json={
                "user_input": "Hello",
                "user_id": "smoke_test_user"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent_type"] == "GREETING"
        assert data["confidence"] > 0.7
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_loan_intent(self, test_client: AsyncClient):
        """Test loan application intent works"""
        response = await test_client.post(
            "/routing/classify",
            json={
                "user_input": "I want to apply for a business loan",
                "user_id": "smoke_test_user"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent_type"] == "LOAN_APPLICATION"
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_linkedin_intent(self, test_client: AsyncClient):
        """Test LinkedIn intent works"""
        response = await test_client.post(
            "/routing/classify",
            json={
                "user_input": "Analyze my LinkedIn profile",
                "user_id": "smoke_test_user"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent_type"] == "PROFILE_ANALYSIS"
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_session_creation(self, test_client: AsyncClient):
        """Test session can be created"""
        response = await test_client.post(
            "/routing/sessions",
            params={"user_id": "smoke_test_user"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_multi_intent_detection(self, test_client: AsyncClient):
        """Test multi-intent detection works"""
        response = await test_client.post(
            "/routing/classify-multi",
            json={
                "user_input": "Check my credit score and help me apply for a loan",
                "user_id": "smoke_test_user"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "primary_intent" in data
        assert "secondary_intents" in data
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_metrics_endpoint(self, test_client: AsyncClient):
        """Test metrics endpoint responds"""
        response = await test_client.get("/routing/metrics/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_routes" in data
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_history_endpoint(self, test_client: AsyncClient):
        """Test history endpoint responds"""
        response = await test_client.get(
            "/routing/history",
            params={"user_id": "smoke_test_user", "limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data or "history" in data
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_error_handling(self, test_client: AsyncClient):
        """Test error handling works"""
        response = await test_client.post(
            "/routing/classify",
            json={"invalid": "data"}
        )
        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data or "error" in data
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_authentication_check(self, test_client: AsyncClient):
        """Test authentication is enforced"""
        response = await test_client.get("/loans/history/test_user")
        # Should require auth
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_routes_list(self, test_client: AsyncClient):
        """Test routes can be listed"""
        response = await test_client.get("/routing/routes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_classifier_statistics(self, test_client: AsyncClient):
        """Test classifier statistics endpoint"""
        response = await test_client.get("/routing/classifier/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "total_classifications" in data or "classifications" in data
    
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_system_integration(self, test_client: AsyncClient):
        """
        Test basic end-to-end integration
        
        Quick test of main workflow
        """
        # 1. Create session
        session_response = await test_client.post(
            "/routing/sessions",
            params={"user_id": "smoke_integration_user"}
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]
        
        # 2. Classify intent
        classify_response = await test_client.post(
            "/routing/classify",
            json={
                "user_input": "I need help applying for a loan",
                "session_id": session_id,
                "user_id": "smoke_integration_user"
            }
        )
        assert classify_response.status_code == 200
        
        # 3. Check history
        history_response = await test_client.get(
            f"/routing/sessions/{session_id}/history"
        )
        assert history_response.status_code == 200
        
        # 4. End session
        end_response = await test_client.delete(
            f"/routing/sessions/{session_id}"
        )
        assert end_response.status_code == 200
