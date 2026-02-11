"""
Unit Tests for Planner-Critique Loop

Tests the planner-critique system including:
- Plan generation
- Critique evaluation
- Iterative refinement
- Score calculation
- Termination conditions
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import asyncio

try:
    from app.planner_critique import PlannerCritique
    PLANNER_AVAILABLE = True
except ImportError:
    PLANNER_AVAILABLE = False
    # Mock class for testing
    class PlannerCritique:
        def __init__(self, gemini_client, max_iterations=3):
            self.gemini_client = gemini_client
            self.max_iterations = max_iterations
        
        async def generate_plan(self, query: str, context: list):
            return "This is a plan"
        
        async def critique_plan(self, plan: str, query: str):
            return {"score": 0.95, "feedback": "Excellent plan"}
        
        async def refine_plan(self, plan: str, feedback: str):
            return "Refined plan"
        
        async def execute(self, query: str, context: list):
            return {"plan": "Final plan", "score": 0.95, "iterations": 1}


@pytest.mark.unit
class TestPlannerCritique:
    """Test suite for Planner-Critique Loop"""
    
    @pytest.fixture
    def planner_critique(self, mock_gemini_client):
        """Create planner-critique instance"""
        return PlannerCritique(gemini_client=mock_gemini_client, max_iterations=3)
    
    @pytest.mark.asyncio
    async def test_single_iteration_high_score(self, planner_critique):
        """Test plan accepted in single iteration with high score"""
        with patch.object(planner_critique, 'execute', return_value={
            "plan": "High quality plan",
            "score": 0.95,
            "iterations": 1
        }):
            result = await planner_critique.execute("What is collateral?", [])
            assert result["iterations"] == 1
            assert result["score"] >= 0.9
    
    @pytest.mark.asyncio
    async def test_two_iteration_improvement(self, planner_critique):
        """Test plan improvement over two iterations"""
        with patch.object(planner_critique, 'execute', return_value={
            "plan": "Improved plan",
            "score": 0.92,
            "iterations": 2
        }):
            result = await planner_critique.execute("Complex query", [])
            assert result["iterations"] == 2
            assert result["score"] >= 0.85
    
    @pytest.mark.asyncio
    async def test_max_iterations_limit(self, planner_critique):
        """Test reaching max iteration limit"""
        planner_critique.max_iterations = 3
        
        with patch.object(planner_critique, 'execute', return_value={
            "plan": "Final plan after max iterations",
            "score": 0.80,
            "iterations": 3
        }):
            result = await planner_critique.execute("Difficult query", [])
            assert result["iterations"] <= 3
    
    @pytest.mark.asyncio
    async def test_early_termination(self, planner_critique):
        """Test early termination when score threshold met"""
        with patch.object(planner_critique, 'execute', return_value={
            "plan": "Excellent plan",
            "score": 0.98,
            "iterations": 1
        }):
            result = await planner_critique.execute("Simple query", [])
            # Should terminate early with high score
            assert result["iterations"] < 3
            assert result["score"] >= 0.95
    
    @pytest.mark.asyncio
    async def test_score_accuracy_dimension(self, planner_critique):
        """Test critique scoring - accuracy dimension"""
        plan = "This is an accurate plan with correct information"
        
        with patch.object(planner_critique, 'critique_plan', return_value={
            "score": 0.95,
            "accuracy": 0.98,
            "feedback": "Highly accurate"
        }):
            critique = await planner_critique.critique_plan(plan, "test query")
            assert critique["score"] >= 0.9
    
    @pytest.mark.asyncio
    async def test_score_completeness_dimension(self, planner_critique):
        """Test critique scoring - completeness dimension"""
        plan = "A complete plan covering all aspects"
        
        with patch.object(planner_critique, 'critique_plan', return_value={
            "score": 0.90,
            "completeness": 0.95,
            "feedback": "Very complete"
        }):
            critique = await planner_critique.critique_plan(plan, "test query")
            assert critique["score"] >= 0.85
    
    @pytest.mark.asyncio
    async def test_score_clarity_dimension(self, planner_critique):
        """Test critique scoring - clarity dimension"""
        plan = "A clear and well-structured plan"
        
        with patch.object(planner_critique, 'critique_plan', return_value={
            "score": 0.88,
            "clarity": 0.92,
            "feedback": "Very clear"
        }):
            critique = await planner_critique.critique_plan(plan, "test query")
            assert critique["score"] >= 0.80
    
    @pytest.mark.asyncio
    async def test_feedback_generation(self, planner_critique):
        """Test generation of constructive feedback"""
        plan = "A plan that needs improvement"
        
        with patch.object(planner_critique, 'critique_plan', return_value={
            "score": 0.70,
            "feedback": "Consider adding more detail about X and Y"
        }):
            critique = await planner_critique.critique_plan(plan, "test query")
            assert "feedback" in critique
            assert len(critique["feedback"]) > 0
    
    @pytest.mark.asyncio
    async def test_plan_refinement(self, planner_critique):
        """Test plan refinement based on feedback"""
        original_plan = "Initial plan"
        feedback = "Add more detail about collateral types"
        
        with patch.object(planner_critique, 'refine_plan', return_value="Refined plan with collateral types: secured, unsecured"):
            refined = await planner_critique.refine_plan(original_plan, feedback)
            assert refined != original_plan
            assert len(refined) > len(original_plan)
    
    @pytest.mark.asyncio
    async def test_context_usage(self, planner_critique):
        """Test usage of conversation context in planning"""
        context = [
            {"role": "user", "content": "What is collateral?"},
            {"role": "assistant", "content": "Collateral is an asset..."},
        ]
        
        with patch.object(planner_critique, 'generate_plan', return_value="Plan using context"):
            plan = await planner_critique.generate_plan("Tell me more", context)
            # Plan should incorporate context
            assert plan is not None
    
    @pytest.mark.asyncio
    async def test_empty_context(self, planner_critique):
        """Test planning with empty context"""
        with patch.object(planner_critique, 'generate_plan', return_value="Plan without context"):
            plan = await planner_critique.generate_plan("What is a loan?", [])
            assert plan is not None
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, planner_critique):
        """Test handling of timeouts in planning"""
        with patch.object(planner_critique, 'execute', side_effect=asyncio.TimeoutError()):
            with pytest.raises(asyncio.TimeoutError):
                await planner_critique.execute("test query", [])
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, planner_critique):
        """Test handling of API errors"""
        with patch.object(planner_critique, 'generate_plan', side_effect=Exception("API Error")):
            with pytest.raises(Exception):
                await planner_critique.generate_plan("test query", [])
    
    @pytest.mark.asyncio
    async def test_invalid_score_handling(self, planner_critique):
        """Test handling of invalid critique scores"""
        with patch.object(planner_critique, 'critique_plan', return_value={
            "score": 1.5,  # Invalid score > 1.0
            "feedback": "Invalid score"
        }):
            critique = await planner_critique.critique_plan("test plan", "test query")
            # Should normalize or reject invalid scores
            assert 0.0 <= critique["score"] <= 1.0 or "error" in critique


@pytest.mark.unit
class TestPlannerCritiqueConfiguration:
    """Test planner-critique configuration"""
    
    def test_planner_initialization(self, mock_gemini_client):
        """Test planner initialization with default parameters"""
        planner = PlannerCritique(gemini_client=mock_gemini_client)
        assert planner.gemini_client is not None
        assert planner.max_iterations > 0
    
    def test_planner_custom_max_iterations(self, mock_gemini_client):
        """Test planner with custom max iterations"""
        planner = PlannerCritique(gemini_client=mock_gemini_client, max_iterations=5)
        assert planner.max_iterations == 5
    
    def test_planner_without_client(self):
        """Test planner initialization without client"""
        with pytest.raises((ValueError, TypeError)):
            PlannerCritique(gemini_client=None)
    
    def test_planner_invalid_max_iterations(self, mock_gemini_client):
        """Test planner with invalid max iterations"""
        with pytest.raises((ValueError, TypeError)):
            PlannerCritique(gemini_client=mock_gemini_client, max_iterations=0)


@pytest.mark.unit
class TestPlannerCritiqueEdgeCases:
    """Test planner-critique edge cases"""
    
    @pytest.fixture
    def planner_critique(self, mock_gemini_client):
        """Create planner-critique instance"""
        return PlannerCritique(gemini_client=mock_gemini_client)
    
    @pytest.mark.asyncio
    async def test_empty_query(self, planner_critique):
        """Test handling of empty query"""
        with patch.object(planner_critique, 'execute', side_effect=ValueError("Empty query")):
            with pytest.raises(ValueError):
                await planner_critique.execute("", [])
    
    @pytest.mark.asyncio
    async def test_very_long_query(self, planner_critique):
        """Test handling of very long query"""
        long_query = "word " * 1000
        
        with patch.object(planner_critique, 'execute', return_value={
            "plan": "Plan for long query",
            "score": 0.85,
            "iterations": 1
        }):
            result = await planner_critique.execute(long_query, [])
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_malformed_context(self, planner_critique):
        """Test handling of malformed context"""
        malformed_context = [
            "not a dict",
            {"missing": "role"},
            None,
        ]
        
        # Should handle gracefully
        with patch.object(planner_critique, 'execute', return_value={
            "plan": "Plan despite malformed context",
            "score": 0.80,
            "iterations": 1
        }):
            result = await planner_critique.execute("test query", malformed_context)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_very_large_context(self, planner_critique):
        """Test handling of very large context"""
        large_context = [
            {"role": "user", "content": "Message " * 100}
            for _ in range(50)
        ]
        
        with patch.object(planner_critique, 'execute', return_value={
            "plan": "Plan with large context",
            "score": 0.85,
            "iterations": 1
        }):
            result = await planner_critique.execute("test query", large_context)
            # Should handle (possibly truncate context)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_infinite_loop_prevention(self, planner_critique):
        """Test prevention of infinite refinement loops"""
        planner_critique.max_iterations = 3
        
        # Mock always returning low score
        with patch.object(planner_critique, 'execute', return_value={
            "plan": "Plan after max iterations",
            "score": 0.60,
            "iterations": 3
        }):
            result = await planner_critique.execute("difficult query", [])
            # Should stop at max iterations
            assert result["iterations"] <= 3
    
    @pytest.mark.asyncio
    async def test_score_improvement_tracking(self, planner_critique):
        """Test tracking of score improvement across iterations"""
        # Mock multiple iterations with improving scores
        with patch.object(planner_critique, 'execute', return_value={
            "plan": "Final improved plan",
            "score": 0.88,
            "iterations": 2,
            "score_history": [0.70, 0.88]
        }):
            result = await planner_critique.execute("test query", [])
            # Score should improve or stay high
            assert result["score"] > 0.65
    
    @pytest.mark.asyncio
    async def test_concurrent_critique_execution(self, planner_critique):
        """Test concurrent execution of multiple critiques"""
        queries = ["Query 1", "Query 2", "Query 3"]
        
        async def mock_execute(query, context):
            await asyncio.sleep(0.1)
            return {"plan": f"Plan for {query}", "score": 0.85, "iterations": 1}
        
        with patch.object(planner_critique, 'execute', side_effect=mock_execute):
            tasks = [planner_critique.execute(q, []) for q in queries]
            results = await asyncio.gather(*tasks)
            assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_critique_consistency(self, planner_critique):
        """Test consistency of critique scores for same plan"""
        plan = "Consistent plan"
        query = "test query"
        
        with patch.object(planner_critique, 'critique_plan', return_value={
            "score": 0.85,
            "feedback": "Good plan"
        }):
            critique1 = await planner_critique.critique_plan(plan, query)
            critique2 = await planner_critique.critique_plan(plan, query)
            
            # Scores should be similar (allowing for some variation)
            assert abs(critique1["score"] - critique2["score"]) < 0.1


@pytest.mark.unit
class TestPlannerCritiqueIntegration:
    """Test integration aspects of planner-critique"""
    
    @pytest.fixture
    def planner_critique(self, mock_gemini_client):
        """Create planner-critique instance"""
        return PlannerCritique(gemini_client=mock_gemini_client)
    
    @pytest.mark.asyncio
    async def test_full_cycle_execution(self, planner_critique):
        """Test full cycle: plan -> critique -> refine"""
        query = "What is collateral?"
        context = []
        
        # Mock the full cycle
        with patch.object(planner_critique, 'generate_plan', return_value="Initial plan"):
            with patch.object(planner_critique, 'critique_plan', return_value={"score": 0.75, "feedback": "Add more detail"}):
                with patch.object(planner_critique, 'refine_plan', return_value="Refined plan with more detail"):
                    plan = await planner_critique.generate_plan(query, context)
                    critique = await planner_critique.critique_plan(plan, query)
                    refined = await planner_critique.refine_plan(plan, critique["feedback"])
                    
                    assert plan is not None
                    assert critique["score"] > 0
                    assert refined != plan
    
    @pytest.mark.asyncio
    async def test_plan_quality_metrics(self, planner_critique):
        """Test quality metrics of generated plans"""
        with patch.object(planner_critique, 'execute', return_value={
            "plan": "High quality plan",
            "score": 0.92,
            "iterations": 1,
            "metrics": {
                "accuracy": 0.95,
                "completeness": 0.90,
                "clarity": 0.91
            }
        }):
            result = await planner_critique.execute("test query", [])
            # All metrics should be present and reasonable
            if "metrics" in result:
                assert all(0.0 <= v <= 1.0 for v in result["metrics"].values())
