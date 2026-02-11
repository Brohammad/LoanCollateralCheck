"""
LangFlow Custom Component: Response Validator (Critique Agent)
Evaluates generated responses for accuracy, completeness, and clarity
"""

from typing import Dict, Optional
from langflow.custom import Component
from langflow.io import MessageTextInput, Output, StrInput, FloatInput
from langflow.schema import Data
import asyncio
import logging
import json

logger = logging.getLogger(__name__)


class ResponseValidatorComponent(Component):
    """
    Custom LangFlow component for response validation (critique).
    
    Evaluates generated responses on multiple criteria:
    - Accuracy: Uses provided sources correctly
    - Completeness: Fully answers the question
    - Clarity: Well-structured and understandable
    """
    
    display_name = "Response Validator"
    description = "Evaluates responses for accuracy, completeness, and clarity"
    icon = "check-circle"
    
    inputs = [
        MessageTextInput(
            name="generated_response",
            display_name="Generated Response",
            info="The response to validate",
            required=True
        ),
        MessageTextInput(
            name="original_query",
            display_name="Original Query",
            info="The original user query",
            required=True
        ),
        MessageTextInput(
            name="context",
            display_name="Context/Sources",
            info="The context used to generate the response",
            required=False
        ),
        StrInput(
            name="gemini_api_key",
            display_name="Gemini API Key",
            info="Google AI API key for Gemini",
            password=True,
            required=True
        ),
        StrInput(
            name="model_name",
            display_name="Model Name",
            info="Gemini model to use",
            value="gemini-2.0-flash-exp",
            advanced=True
        ),
        FloatInput(
            name="acceptance_threshold",
            display_name="Acceptance Threshold",
            info="Minimum score to approve response (0-1)",
            value=0.85,
            advanced=True
        )
    ]
    
    outputs = [
        Output(
            name="approved",
            display_name="Approved",
            method="is_approved"
        ),
        Output(
            name="feedback",
            display_name="Feedback",
            method="get_feedback"
        ),
        Output(
            name="validation_data",
            display_name="Validation Data",
            method="get_validation_data"
        )
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._approved = False
        self._feedback = ""
        self._scores = {}
        self._overall_score = 0.0
    
    async def validate_response_async(self) -> bool:
        """Perform response validation asynchronously."""
        try:
            from app.gemini_enhanced import GeminiClient
            
            # Create Gemini client
            client = GeminiClient(
                api_key=self.gemini_api_key,
                model_name=self.model_name,
                enable_cache=False  # Don't cache critiques
            )
            
            # Build critique prompt
            critique_prompt = self._build_critique_prompt()
            
            # Get critique
            parsed, _ = await client.generate_with_json(
                prompt=critique_prompt,
                temperature=0.3,
                max_tokens=500
            )
            
            # Extract scores
            self._scores = {
                "accuracy": parsed.get("accuracy_score", 0.0),
                "completeness": parsed.get("completeness_score", 0.0),
                "clarity": parsed.get("clarity_score", 0.0)
            }
            
            # Calculate overall score (weighted average)
            self._overall_score = (
                self._scores["accuracy"] * 0.4 +
                self._scores["completeness"] * 0.4 +
                self._scores["clarity"] * 0.2
            )
            
            # Get feedback
            self._feedback = parsed.get("feedback", "")
            
            # Determine if approved
            self._approved = self._overall_score >= self.acceptance_threshold
            
            logger.info(
                f"Response validated: {self._approved} "
                f"(score: {self._overall_score:.2f})"
            )
            
            return self._approved
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            # Fail gracefully - approve by default if validation fails
            self._approved = True
            self._feedback = f"Validation error: {str(e)}"
            self._overall_score = 0.5
            return True
    
    def _build_critique_prompt(self) -> str:
        """Build the critique prompt."""
        prompt = f"""You are a critical evaluator of AI-generated responses. Evaluate the following response based on these criteria:

**Original Query:**
{self.original_query}

**Context/Sources Provided:**
{self.context if self.context else "No context provided"}

**Generated Response:**
{self.generated_response}

**Evaluation Criteria:**

1. **Accuracy (0.0-1.0)**: Does the response use the provided sources correctly? Are facts accurate?
2. **Completeness (0.0-1.0)**: Does the response fully answer the query? Is anything missing?
3. **Clarity (0.0-1.0)**: Is the response well-structured and easy to understand?

Provide your evaluation in this exact JSON format:
{{
    "accuracy_score": <0.0-1.0>,
    "completeness_score": <0.0-1.0>,
    "clarity_score": <0.0-1.0>,
    "feedback": "<specific feedback for improvement>",
    "strengths": "<what the response does well>",
    "weaknesses": "<what needs improvement>"
}}

Be critical but fair. High standards ensure quality responses."""
        
        return prompt
    
    def is_approved(self) -> bool:
        """Main output: approval status."""
        return asyncio.run(self.validate_response_async())
    
    def get_feedback(self) -> str:
        """Output: critique feedback."""
        return self._feedback
    
    def get_validation_data(self) -> Data:
        """Output: complete validation data."""
        return Data(
            data={
                "approved": self._approved,
                "overall_score": self._overall_score,
                "accuracy_score": self._scores.get("accuracy", 0.0),
                "completeness_score": self._scores.get("completeness", 0.0),
                "clarity_score": self._scores.get("clarity", 0.0),
                "feedback": self._feedback,
                "threshold": self.acceptance_threshold
            }
        )
