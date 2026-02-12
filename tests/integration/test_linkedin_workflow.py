"""
LinkedIn Integration Workflow Tests

Tests complete LinkedIn integration workflow including:
- Profile parsing
- Skill extraction
- Job matching
- Skill recommendations
- Intent routing for LinkedIn features
"""

import pytest
from typing import Dict, Any
from httpx import AsyncClient

from app.main import app


class TestLinkedInWorkflow:
    """LinkedIn integration workflow tests"""
    
    @pytest.fixture
    async def test_client(self):
        """Create test client"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    def user_data(self):
        """Test user data"""
        return {
            "user_id": "linkedin_user_123",
            "email": "linkedin@example.com",
            "linkedin_url": "https://linkedin.com/in/testuser"
        }
    
    @pytest.fixture
    def linkedin_profile_data(self):
        """Sample LinkedIn profile data"""
        return {
            "headline": "Senior Software Engineer at Tech Corp",
            "summary": "Experienced software engineer with 5+ years in Python, AWS, and microservices",
            "experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "duration_months": 36,
                    "description": "Led development of microservices architecture using Python and AWS"
                },
                {
                    "title": "Software Engineer",
                    "company": "StartupCo",
                    "duration_months": 24,
                    "description": "Developed REST APIs and worked with PostgreSQL databases"
                }
            ],
            "skills": ["Python", "AWS", "Docker", "Kubernetes", "PostgreSQL", "REST APIs"],
            "education": [
                {
                    "degree": "BS Computer Science",
                    "school": "University of Tech",
                    "graduation_year": 2018
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_complete_linkedin_workflow(
        self,
        test_client: AsyncClient,
        user_data: Dict,
        linkedin_profile_data: Dict
    ):
        """
        Test complete LinkedIn workflow
        
        Steps:
        1. User authentication
        2. Intent classification (profile analysis)
        3. Profile parsing
        4. Skill extraction
        5. Job matching
        6. Skill recommendations
        7. Cost tracking
        """
        
        # Step 1: Authenticate
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
        session_id = session_response.json()["session_id"]
        
        # Step 3: Intent classification - profile analysis
        classify_response = await test_client.post(
            "/routing/classify",
            json={
                "user_input": "Analyze my LinkedIn profile",
                "session_id": session_id,
                "user_id": user_data["user_id"]
            },
            headers=headers
        )
        assert classify_response.status_code == 200
        intent = classify_response.json()
        assert intent["intent_type"] == "PROFILE_ANALYSIS"
        assert intent["confidence"] > 0.7
        
        # Step 4: Parse LinkedIn profile
        parse_response = await test_client.post(
            "/linkedin/parse-profile",
            json={
                "user_id": user_data["user_id"],
                "profile_url": user_data["linkedin_url"],
                "profile_data": linkedin_profile_data
            },
            headers=headers
        )
        assert parse_response.status_code == 200
        parsed_profile = parse_response.json()
        assert "profile_id" in parsed_profile
        assert "headline" in parsed_profile
        assert "experience" in parsed_profile
        
        # Step 5: Extract skills
        skills_response = await test_client.post(
            "/linkedin/extract-skills",
            json={
                "user_id": user_data["user_id"],
                "profile_id": parsed_profile["profile_id"]
            },
            headers=headers
        )
        assert skills_response.status_code == 200
        skills_data = skills_response.json()
        assert "technical_skills" in skills_data
        assert "soft_skills" in skills_data
        assert len(skills_data["technical_skills"]) > 0
        
        # Verify skill categories
        skill_categories = skills_data.get("skill_categories", {})
        assert "programming" in skill_categories or "cloud" in skill_categories
        
        # Step 6: Get job matches
        job_match_response = await test_client.post(
            "/linkedin/match-jobs",
            json={
                "user_id": user_data["user_id"],
                "profile_id": parsed_profile["profile_id"],
                "preferences": {
                    "job_types": ["full_time"],
                    "remote": True,
                    "min_salary": 80000
                }
            },
            headers=headers
        )
        assert job_match_response.status_code == 200
        job_matches = job_match_response.json()
        assert "matches" in job_matches
        assert len(job_matches["matches"]) > 0
        
        # Verify match scores
        for match in job_matches["matches"]:
            assert "job_title" in match
            assert "company" in match
            assert "match_score" in match
            assert 0 <= match["match_score"] <= 100
            assert "match_reasons" in match
        
        # Step 7: Get skill recommendations
        recommendations_response = await test_client.post(
            "/linkedin/recommend-skills",
            json={
                "user_id": user_data["user_id"],
                "profile_id": parsed_profile["profile_id"],
                "target_roles": ["Senior Software Engineer", "Tech Lead"]
            },
            headers=headers
        )
        assert recommendations_response.status_code == 200
        recommendations = recommendations_response.json()
        assert "recommended_skills" in recommendations
        assert len(recommendations["recommended_skills"]) > 0
        
        # Verify recommendations have learning resources
        for rec in recommendations["recommended_skills"]:
            assert "skill_name" in rec
            assert "importance" in rec
            assert "learning_resources" in rec
        
        # Step 8: Verify cost tracking
        cost_response = await test_client.get(
            f"/cost-analysis/usage/{user_data['user_id']}",
            params={"session_id": session_id},
            headers=headers
        )
        assert cost_response.status_code == 200
        cost_data = cost_response.json()
        assert cost_data["total_cost"] > 0
        assert "profile_analysis_cost" in cost_data
        assert "skill_extraction_cost" in cost_data
    
    @pytest.mark.asyncio
    async def test_linkedin_job_matching_accuracy(
        self,
        test_client: AsyncClient,
        user_data: Dict,
        linkedin_profile_data: Dict
    ):
        """
        Test job matching accuracy
        
        Verifies that job matches are relevant based on:
        - Skills alignment
        - Experience level
        - Industry match
        """
        
        # Authenticate
        auth_response = await test_client.post("/auth/login", json={
            "email": user_data["email"],
            "password": "test_password"
        })
        token = auth_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Parse profile
        parse_response = await test_client.post(
            "/linkedin/parse-profile",
            json={
                "user_id": user_data["user_id"],
                "profile_data": linkedin_profile_data
            },
            headers=headers
        )
        profile_id = parse_response.json()["profile_id"]
        
        # Get job matches
        job_response = await test_client.post(
            "/linkedin/match-jobs",
            json={
                "user_id": user_data["user_id"],
                "profile_id": profile_id
            },
            headers=headers
        )
        matches = job_response.json()["matches"]
        
        # Verify matches are relevant
        for match in matches[:5]:  # Check top 5 matches
            match_reasons = match["match_reasons"]
            
            # Should have skills alignment
            assert any("skill" in reason.lower() for reason in match_reasons)
            
            # Should consider experience
            if match["match_score"] > 80:
                assert any("experience" in reason.lower() for reason in match_reasons)
            
            # High match scores should be justified
            if match["match_score"] > 90:
                assert len(match_reasons) >= 3
    
    @pytest.mark.asyncio
    async def test_linkedin_skill_gap_analysis(
        self,
        test_client: AsyncClient,
        user_data: Dict,
        linkedin_profile_data: Dict
    ):
        """
        Test skill gap analysis for career progression
        """
        
        # Authenticate
        auth_response = await test_client.post("/auth/login", json={
            "email": user_data["email"],
            "password": "test_password"
        })
        token = auth_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Parse profile
        parse_response = await test_client.post(
            "/linkedin/parse-profile",
            json={
                "user_id": user_data["user_id"],
                "profile_data": linkedin_profile_data
            },
            headers=headers
        )
        profile_id = parse_response.json()["profile_id"]
        
        # Get skill gap analysis
        gap_response = await test_client.post(
            "/linkedin/analyze-skill-gap",
            json={
                "user_id": user_data["user_id"],
                "profile_id": profile_id,
                "target_role": "Engineering Manager"
            },
            headers=headers
        )
        assert gap_response.status_code == 200
        gap_analysis = gap_response.json()
        
        # Verify gap analysis
        assert "current_skills" in gap_analysis
        assert "required_skills" in gap_analysis
        assert "skill_gaps" in gap_analysis
        assert "development_plan" in gap_analysis
        
        # Verify development plan
        dev_plan = gap_analysis["development_plan"]
        for gap in gap_analysis["skill_gaps"]:
            # Each gap should have action items
            assert gap["skill"] in str(dev_plan)
    
    @pytest.mark.asyncio
    async def test_linkedin_multi_intent(
        self,
        test_client: AsyncClient,
        user_data: Dict
    ):
        """
        Test multi-intent with LinkedIn features
        
        Example: "Analyze my profile and recommend jobs"
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
                "user_input": "Analyze my LinkedIn profile and find me relevant jobs",
                "session_id": session_id,
                "user_id": user_data["user_id"]
            },
            headers=headers
        )
        assert classify_response.status_code == 200
        multi_intent = classify_response.json()
        
        # Should detect both PROFILE_ANALYSIS and JOB_MATCHING
        all_intent_types = [multi_intent["primary_intent"]["intent_type"]]
        all_intent_types.extend([
            intent["intent_type"]
            for intent in multi_intent["secondary_intents"]
        ])
        
        assert "PROFILE_ANALYSIS" in all_intent_types
        assert "JOB_MATCHING" in all_intent_types
    
    @pytest.mark.asyncio
    async def test_linkedin_intent_history(
        self,
        test_client: AsyncClient,
        user_data: Dict
    ):
        """
        Test LinkedIn intent tracking and history
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
        
        # Perform multiple LinkedIn operations
        linkedin_intents = [
            "Analyze my LinkedIn profile",
            "Find me software engineering jobs",
            "What skills should I learn?",
            "Show me my profile strengths"
        ]
        
        for user_input in linkedin_intents:
            await test_client.post(
                "/routing/route",
                json={
                    "user_input": user_input,
                    "session_id": session_id,
                    "user_id": user_data["user_id"],
                    "user_authenticated": True
                },
                headers=headers
            )
        
        # Get intent history
        history_response = await test_client.get(
            "/routing/history",
            params={"user_id": user_data["user_id"]},
            headers=headers
        )
        assert history_response.status_code == 200
        history = history_response.json()["history"]
        
        # Verify LinkedIn intents were tracked
        linkedin_intent_types = [
            "PROFILE_ANALYSIS", "JOB_MATCHING", "SKILL_RECOMMENDATION"
        ]
        tracked_linkedin_intents = [
            intent for intent in history
            if intent["intent_type"] in linkedin_intent_types
        ]
        assert len(tracked_linkedin_intents) >= 3
        
        # Get user patterns
        patterns_response = await test_client.get(
            f"/routing/history/user-patterns/{user_data['user_id']}",
            headers=headers
        )
        assert patterns_response.status_code == 200
        patterns = patterns_response.json()
        
        # Verify LinkedIn is a top intent for this user
        top_intents = [item["type"] for item in patterns["top_intents"]]
        assert any(
            intent_type in top_intents
            for intent_type in linkedin_intent_types
        )
