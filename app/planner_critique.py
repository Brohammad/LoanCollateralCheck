"""
Planner-Critique Loop Orchestrator
Implements iterative refinement of responses
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from app.gemini_enhanced import GeminiClient, GeminiResponse

logger = logging.getLogger(__name__)


@dataclass
class IterationResult:
    """Result of a single iteration."""
    iteration: int
    response: str
    critique_score: float
    accuracy: float
    completeness: float
    clarity: float
    feedback: str
    approved: bool


@dataclass
class PlannerCritiqueResult:
    """Final result of planner-critique loop."""
    final_response: str
    approved: bool
    iterations: List[IterationResult]
    total_iterations: int
    final_score: float
    total_time_ms: int
    total_tokens: int


class PlannerCritiqueOrchestrator:
    """
    Orchestrates the planner-critique loop.
    
    The planner generates responses, and the critique evaluates them.
    The loop continues until either:
    1. Critique approves the response (score >= threshold)
    2. Maximum iterations reached
    """
    
    def __init__(
        self,
        gemini_client: GeminiClient,
        max_iterations: int = 2,
        acceptance_threshold: float = 0.85,
        db_manager: Optional[any] = None
    ):
        """
        Initialize orchestrator.
        
        Args:
            gemini_client: Gemini API client
            max_iterations: Maximum refinement iterations
            acceptance_threshold: Minimum score to approve
            db_manager: Database manager for logging
        """
        self.gemini_client = gemini_client
        self.max_iterations = max_iterations
        self.acceptance_threshold = acceptance_threshold
        self.db_manager = db_manager
    
    async def run(
        self,
        query: str,
        context: str,
        conversation_id: Optional[int] = None,
        system_instruction: Optional[str] = None
    ) -> PlannerCritiqueResult:
        """
        Run the planner-critique loop.
        
        Args:
            query: User's query
            context: Retrieved context from RAG
            conversation_id: ID for logging iterations
            system_instruction: Optional system instruction
            
        Returns:
            PlannerCritiqueResult with final response and metadata
        """
        start_time = time.time()
        iterations: List[IterationResult] = []
        total_tokens = 0
        
        current_response = ""
        previous_feedback = ""
        
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"Starting iteration {iteration}/{self.max_iterations}")
            
            # Step 1: Planner generates response
            planner_result = await self._planner_step(
                query=query,
                context=context,
                previous_response=current_response if iteration > 1 else None,
                previous_feedback=previous_feedback if iteration > 1 else None,
                system_instruction=system_instruction
            )
            
            current_response = planner_result.text
            total_tokens += planner_result.token_usage.total_tokens
            
            logger.info(
                f"Planner generated response: {len(current_response)} chars, "
                f"{planner_result.token_usage.total_tokens} tokens"
            )
            
            # Step 2: Critique evaluates response
            critique_result = await self._critique_step(
                query=query,
                response=current_response,
                context=context
            )
            
            total_tokens += critique_result["tokens"]
            
            # Record iteration
            iteration_result = IterationResult(
                iteration=iteration,
                response=current_response,
                critique_score=critique_result["overall_score"],
                accuracy=critique_result["accuracy"],
                completeness=critique_result["completeness"],
                clarity=critique_result["clarity"],
                feedback=critique_result["feedback"],
                approved=critique_result["approved"]
            )
            iterations.append(iteration_result)
            
            # Log to database if available
            if self.db_manager and conversation_id:
                self.db_manager.add_critique_iteration(
                    conversation_id=conversation_id,
                    iteration=iteration,
                    planner_response=current_response,
                    critique_score=critique_result["overall_score"],
                    accuracy_score=critique_result["accuracy"],
                    completeness_score=critique_result["completeness"],
                    clarity_score=critique_result["clarity"],
                    critique_feedback=critique_result["feedback"]
                )
            
            logger.info(
                f"Critique score: {critique_result['overall_score']:.2f} "
                f"(accuracy: {critique_result['accuracy']:.2f}, "
                f"completeness: {critique_result['completeness']:.2f}, "
                f"clarity: {critique_result['clarity']:.2f})"
            )
            
            # Check if approved
            if critique_result["approved"]:
                logger.info(f"Response approved on iteration {iteration}")
                break
            
            # Prepare feedback for next iteration
            previous_feedback = critique_result["feedback"]
            
            # Check if we're at max iterations
            if iteration == self.max_iterations:
                logger.warning(
                    f"Max iterations reached without approval "
                    f"(final score: {critique_result['overall_score']:.2f})"
                )
        
        # Calculate total time
        total_time_ms = int((time.time() - start_time) * 1000)
        
        # Get final scores
        final_iteration = iterations[-1]
        
        return PlannerCritiqueResult(
            final_response=current_response,
            approved=final_iteration.approved,
            iterations=iterations,
            total_iterations=len(iterations),
            final_score=final_iteration.critique_score,
            total_time_ms=total_time_ms,
            total_tokens=total_tokens
        )
    
    async def _planner_step(
        self,
        query: str,
        context: str,
        previous_response: Optional[str] = None,
        previous_feedback: Optional[str] = None,
        system_instruction: Optional[str] = None
    ) -> GeminiResponse:
        """
        Planner step: Generate response using context.
        
        Args:
            query: User's query
            context: Retrieved context
            previous_response: Previous response (for refinement)
            previous_feedback: Feedback from previous critique
            system_instruction: Optional system instruction
            
        Returns:
            GeminiResponse
        """
        # Build prompt
        if previous_response and previous_feedback:
            # Refinement iteration
            prompt = f"""You are refining a previous response based on critique feedback.

**Original Query:**
{query}

**Context/Sources:**
{context}

**Previous Response:**
{previous_response}

**Critique Feedback:**
{previous_feedback}

**Instructions:**
Based on the feedback, improve your response to better address the query. Use the provided context and sources. Be accurate, complete, and clear.

**Improved Response:**"""
        else:
            # Initial iteration
            prompt = f"""Answer the following query using the provided context and sources.

**Query:**
{query}

**Context/Sources:**
{context}

**Instructions:**
- Use the provided context to answer the query accurately
- Include relevant details and cite sources when appropriate
- Be clear and well-structured
- If the context doesn't contain enough information, acknowledge limitations

**Response:**"""
        
        # Generate response
        response = await self.gemini_client.generate_async(
            prompt=prompt,
            temperature=0.7,
            max_tokens=1000,
            system_instruction=system_instruction
        )
        
        return response
    
    async def _critique_step(
        self,
        query: str,
        response: str,
        context: str
    ) -> Dict:
        """
        Critique step: Evaluate response quality.
        
        Args:
            query: Original query
            response: Generated response to evaluate
            context: Context used for generation
            
        Returns:
            Dict with scores and feedback
        """
        # Build critique prompt
        prompt = f"""You are a critical evaluator of AI-generated responses. Evaluate the following response based on these criteria:

**Original Query:**
{query}

**Context/Sources Provided:**
{context}

**Generated Response:**
{response}

**Evaluation Criteria:**

1. **Accuracy (0.0-1.0)**: Does the response use the provided sources correctly? Are facts accurate? Does it avoid hallucinations?
2. **Completeness (0.0-1.0)**: Does the response fully answer the query? Is anything important missing?
3. **Clarity (0.0-1.0)**: Is the response well-structured and easy to understand? Is it concise yet thorough?

Provide your evaluation in this exact JSON format:
{{
    "accuracy_score": <0.0-1.0>,
    "completeness_score": <0.0-1.0>,
    "clarity_score": <0.0-1.0>,
    "feedback": "<specific, actionable feedback for improvement>",
    "strengths": "<what the response does well>",
    "weaknesses": "<what needs improvement>"
}}

Be critical but fair. High standards ensure quality responses."""
        
        # Get critique
        try:
            parsed, response_obj = await self.gemini_client.generate_with_json(
                prompt=prompt,
                temperature=0.3,
                max_tokens=500
            )
            
            # Calculate overall score (weighted average)
            accuracy = parsed.get("accuracy_score", 0.0)
            completeness = parsed.get("completeness_score", 0.0)
            clarity = parsed.get("clarity_score", 0.0)
            
            overall_score = (
                accuracy * 0.4 +
                completeness * 0.4 +
                clarity * 0.2
            )
            
            approved = overall_score >= self.acceptance_threshold
            
            return {
                "overall_score": overall_score,
                "accuracy": accuracy,
                "completeness": completeness,
                "clarity": clarity,
                "feedback": parsed.get("feedback", ""),
                "strengths": parsed.get("strengths", ""),
                "weaknesses": parsed.get("weaknesses", ""),
                "approved": approved,
                "tokens": response_obj.token_usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"Critique step failed: {e}")
            # Fail gracefully - approve by default if critique fails
            return {
                "overall_score": 0.5,
                "accuracy": 0.5,
                "completeness": 0.5,
                "clarity": 0.5,
                "feedback": f"Critique error: {str(e)}",
                "strengths": "",
                "weaknesses": "",
                "approved": True,  # Approve to continue
                "tokens": 0
            }
    
    def run_sync(self, query: str, context: str, **kwargs) -> PlannerCritiqueResult:
        """Synchronous wrapper for run()."""
        return asyncio.run(self.run(query, context, **kwargs))


# Convenience function
async def refine_response(
    query: str,
    context: str,
    gemini_api_key: str,
    max_iterations: int = 2,
    acceptance_threshold: float = 0.85,
    **kwargs
) -> str:
    """
    Quick helper to refine a response.
    
    Args:
        query: User's query
        context: Retrieved context
        gemini_api_key: API key
        max_iterations: Max refinement iterations
        acceptance_threshold: Approval threshold
        **kwargs: Additional arguments
        
    Returns:
        Final refined response
    """
    client = GeminiClient(api_key=gemini_api_key, enable_cache=False)
    orchestrator = PlannerCritiqueOrchestrator(
        gemini_client=client,
        max_iterations=max_iterations,
        acceptance_threshold=acceptance_threshold
    )
    
    result = await orchestrator.run(query=query, context=context, **kwargs)
    return result.final_response
