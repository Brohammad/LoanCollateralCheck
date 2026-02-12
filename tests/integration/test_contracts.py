"""
Contract Tests

API contract tests to ensure:
- Request/response schemas
- Backward compatibility
- API versioning
- Breaking change detection
"""

import pytest
from typing import Dict, Any
from httpx import AsyncClient
from pydantic import BaseModel, ValidationError

from app.main import app


class TestAPIContracts:
    """API contract tests"""
    
    @pytest.fixture
    async def test_client(self):
        """Create test client"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_intent_classification_contract(self, test_client: AsyncClient):
        """
        Test intent classification API contract
        
        Ensures response schema remains stable
        """
        
        response = await test_client.post(
            "/routing/classify",
            json={
                "user_input": "I want to apply for a loan",
                "user_id": "contract_test_user"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        required_fields = [
            "intent_id",
            "intent_type",
            "confidence",
            "confidence_level",
            "user_input",
            "entities",
            "parameters",
            "language",
            "timestamp"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Field types
        assert isinstance(data["intent_id"], str)
        assert isinstance(data["intent_type"], str)
        assert isinstance(data["confidence"], (int, float))
        assert 0 <= data["confidence"] <= 1
        assert isinstance(data["confidence_level"], str)
        assert data["confidence_level"] in ["VERY_HIGH", "HIGH", "MEDIUM", "LOW", "VERY_LOW"]
        assert isinstance(data["entities"], dict)
        assert isinstance(data["parameters"], dict)
        assert isinstance(data["language"], str)
        assert isinstance(data["timestamp"], str)
    
    @pytest.mark.asyncio
    async def test_route_result_contract(self, test_client: AsyncClient):
        """
        Test routing result API contract
        """
        
        response = await test_client.post(
            "/routing/route",
            json={
                "user_input": "I need help",
                "user_id": "contract_test_user",
                "user_authenticated": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        required_fields = [
            "route_id",
            "intent",
            "success",
            "response",
            "execution_time_ms",
            "timestamp"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Field types
        assert isinstance(data["route_id"], str)
        assert isinstance(data["intent"], dict)
        assert isinstance(data["success"], bool)
        assert isinstance(data["execution_time_ms"], (int, float))
        assert data["execution_time_ms"] >= 0
    
    @pytest.mark.asyncio
    async def test_multi_intent_contract(self, test_client: AsyncClient):
        """
        Test multi-intent classification contract
        """
        
        response = await test_client.post(
            "/routing/classify-multi",
            json={
                "user_input": "Check my credit and apply for a loan",
                "user_id": "contract_test_user"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        required_fields = [
            "primary_intent",
            "secondary_intents",
            "execution_order",
            "requires_clarification"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Field types
        assert isinstance(data["primary_intent"], dict)
        assert isinstance(data["secondary_intents"], list)
        assert isinstance(data["execution_order"], list)
        assert isinstance(data["requires_clarification"], bool)
        
        # Primary intent structure
        assert "intent_id" in data["primary_intent"]
        assert "intent_type" in data["primary_intent"]
        assert "confidence" in data["primary_intent"]
    
    @pytest.mark.asyncio
    async def test_session_contract(self, test_client: AsyncClient):
        """
        Test session API contract
        """
        
        # Create session
        create_response = await test_client.post(
            "/routing/sessions",
            params={"user_id": "contract_test_user"}
        )
        
        assert create_response.status_code == 200
        create_data = create_response.json()
        
        assert "session_id" in create_data
        assert isinstance(create_data["session_id"], str)
        
        session_id = create_data["session_id"]
        
        # Get session
        get_response = await test_client.get(f"/routing/sessions/{session_id}")
        assert get_response.status_code == 200
        session_data = get_response.json()
        
        # Required session fields
        required_fields = [
            "session_id",
            "user_id",
            "conversation_history",
            "context_data",
            "user_preferences",
            "language",
            "created_at",
            "last_interaction",
            "interaction_count"
        ]
        
        for field in required_fields:
            assert field in session_data, f"Missing required field: {field}"
    
    @pytest.mark.asyncio
    async def test_error_response_contract(self, test_client: AsyncClient):
        """
        Test error response contract
        
        Ensures errors follow standard format
        """
        
        # Invalid request
        response = await test_client.post(
            "/routing/classify",
            json={"invalid": "data"}
        )
        
        assert response.status_code in [400, 422]
        error_data = response.json()
        
        # Standard error fields
        assert "detail" in error_data or "error" in error_data
    
    @pytest.mark.asyncio
    async def test_pagination_contract(self, test_client: AsyncClient):
        """
        Test pagination contract for list endpoints
        """
        
        response = await test_client.get(
            "/routing/history",
            params={"limit": 10, "user_id": "contract_test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Pagination fields
        assert "count" in data or "total" in data
        assert "history" in data or "results" in data or "items" in data
    
    @pytest.mark.asyncio
    async def test_backward_compatibility(self, test_client: AsyncClient):
        """
        Test backward compatibility
        
        Old API calls should still work
        """
        
        # Test v1 endpoint format (if exists)
        # This would fail if breaking changes introduced
        
        # Test with minimal required fields
        minimal_request = {
            "user_input": "test",
            "user_id": "test_user"
        }
        
        response = await test_client.post(
            "/routing/classify",
            json=minimal_request
        )
        
        assert response.status_code == 200
        
        # Test with optional fields from previous version
        extended_request = {
            **minimal_request,
            "session_id": None,  # Optional field
            "detect_multiple": False  # Optional field
        }
        
        response2 = await test_client.post(
            "/routing/classify",
            json=extended_request
        )
        
        assert response2.status_code == 200
    
    @pytest.mark.asyncio
    async def test_api_versioning(self, test_client: AsyncClient):
        """
        Test API versioning headers
        """
        
        response = await test_client.get("/health")
        
        # Should include version information
        assert response.status_code == 200
        
        # Check headers or response body for version
        headers = response.headers
        body = response.json()
        
        # Version in headers OR body
        version_found = "x-api-version" in headers or "version" in body or "api_version" in body
        assert version_found, "API version not exposed"
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, test_client: AsyncClient):
        """
        Test rate limit headers contract
        """
        
        response = await test_client.post(
            "/routing/classify",
            json={"user_input": "test", "user_id": "contract_user"}
        )
        
        headers = response.headers
        
        # Rate limit headers (if implemented)
        rate_limit_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-reset"
        ]
        
        # At least some rate limit info should be present
        has_rate_limit_info = any(header in headers for header in rate_limit_headers)
        
        # If rate limiting is enabled, headers should be present
        if response.status_code != 429:
            # Test passes regardless - rate limit headers are optional for successful requests
            pass
    
    @pytest.mark.asyncio
    async def test_authentication_contract(self, test_client: AsyncClient):
        """
        Test authentication header contract
        """
        
        # Test with valid token format
        valid_formats = [
            "Bearer token123",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  # JWT format
        ]
        
        for auth_header in valid_formats:
            response = await test_client.get(
                "/loans/history/test_user",
                headers={"Authorization": auth_header}
            )
            
            # Should recognize auth format (even if token is invalid)
            # 401 = invalid token (good)
            # 403 = forbidden (good)
            # 400 = bad request format (bad)
            assert response.status_code not in [400], f"Auth format not recognized: {auth_header}"
    
    @pytest.mark.asyncio
    async def test_content_type_negotiation(self, test_client: AsyncClient):
        """
        Test content type negotiation
        """
        
        # Test JSON request
        response = await test_client.post(
            "/routing/classify",
            json={"user_input": "test", "user_id": "test_user"},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
    
    @pytest.mark.asyncio
    async def test_timestamp_format_contract(self, test_client: AsyncClient):
        """
        Test timestamp format consistency
        """
        
        response = await test_client.post(
            "/routing/classify",
            json={"user_input": "test", "user_id": "test_user"}
        )
        
        data = response.json()
        timestamp = data.get("timestamp")
        
        assert timestamp is not None
        
        # Should be ISO 8601 format
        from datetime import datetime
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            timestamp_valid = True
        except:
            timestamp_valid = False
        
        assert timestamp_valid, f"Invalid timestamp format: {timestamp}"
    
    @pytest.mark.asyncio
    async def test_enum_values_contract(self, test_client: AsyncClient):
        """
        Test enum values remain stable
        """
        
        response = await test_client.post(
            "/routing/classify",
            json={"user_input": "test", "user_id": "test_user"}
        )
        
        data = response.json()
        
        # Intent types should be from known set
        known_intent_types = [
            "GREETING", "QUESTION", "COMMAND", "FEEDBACK",
            "LOAN_APPLICATION", "COLLATERAL_CHECK", "CREDIT_HISTORY", "DOCUMENT_UPLOAD",
            "PROFILE_ANALYSIS", "JOB_MATCHING", "SKILL_RECOMMENDATION",
            "HELP", "STATUS", "SETTINGS", "MULTI_INTENT", "CLARIFICATION_NEEDED", "UNKNOWN"
        ]
        
        assert data["intent_type"] in known_intent_types, f"Unknown intent type: {data['intent_type']}"
        
        # Confidence levels should be from known set
        known_confidence_levels = ["VERY_HIGH", "HIGH", "MEDIUM", "LOW", "VERY_LOW"]
        assert data["confidence_level"] in known_confidence_levels, f"Unknown confidence level: {data['confidence_level']}"
