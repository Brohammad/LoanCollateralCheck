"""
LangFlow Custom Component: Intent Classifier
Classifies user messages into intents using Gemini API
"""

from typing import Optional
from langflow.custom import Component
from langflow.io import MessageTextInput, Output, StrInput, FloatOutput
from langflow.schema import Data
import asyncio
import logging

logger = logging.getLogger(__name__)


class IntentClassifierComponent(Component):
    """
    Custom LangFlow component for intent classification.
    
    Classifies user messages into predefined intents using Gemini API.
    Returns the detected intent and confidence score.
    """
    
    display_name = "Intent Classifier"
    description = "Classifies user messages into intents (greeting, question, command, etc.)"
    icon = "brain"
    
    inputs = [
        MessageTextInput(
            name="user_message",
            display_name="User Message",
            info="The user's input message to classify",
            required=True
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
        StrInput(
            name="intents",
            display_name="Possible Intents",
            info="Comma-separated list of intents",
            value="greeting,question,command,clarification,other",
            advanced=True
        ),
        FloatOutput(
            name="confidence_threshold",
            display_name="Confidence Threshold",
            info="Minimum confidence to accept classification",
            value=0.5,
            advanced=True
        )
    ]
    
    outputs = [
        Output(
            name="intent",
            display_name="Intent",
            method="classify_intent"
        ),
        Output(
            name="confidence",
            display_name="Confidence",
            method="get_confidence"
        ),
        Output(
            name="classification_data",
            display_name="Classification Data",
            method="get_classification_data"
        )
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._intent = "other"
        self._confidence = 0.0
        self._reasoning = ""
    
    async def classify_intent_async(self) -> str:
        """Perform intent classification asynchronously."""
        try:
            # Import here to avoid circular dependencies
            from app.gemini_enhanced import GeminiClient
            
            # Parse intents list
            intents_list = [i.strip() for i in self.intents.split(",")]
            
            # Create Gemini client
            client = GeminiClient(
                api_key=self.gemini_api_key,
                model_name=self.model_name,
                enable_cache=True
            )
            
            # Classify intent
            intent, confidence = await client.classify_intent(
                user_message=self.user_message,
                intents=intents_list
            )
            
            # Store results
            self._intent = intent
            self._confidence = confidence
            
            # Check confidence threshold
            if confidence < self.confidence_threshold:
                logger.warning(
                    f"Low confidence classification: {intent} ({confidence:.2f})"
                )
                self._intent = "other"
            
            logger.info(
                f"Intent classified: {self._intent} "
                f"(confidence: {self._confidence:.2f})"
            )
            
            return self._intent
            
        except Exception as e:
            logger.error(f"Intent classification error: {e}")
            self._intent = "other"
            self._confidence = 0.0
            return self._intent
    
    def classify_intent(self) -> str:
        """Main output: classified intent."""
        return asyncio.run(self.classify_intent_async())
    
    def get_confidence(self) -> float:
        """Output: confidence score."""
        return self._confidence
    
    def get_classification_data(self) -> Data:
        """Output: complete classification data."""
        return Data(
            data={
                "intent": self._intent,
                "confidence": self._confidence,
                "user_message": self.user_message,
                "intents_list": self.intents.split(","),
                "threshold": self.confidence_threshold
            }
        )
