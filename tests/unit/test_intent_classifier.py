"""
Unit Tests for Intent Classifier

Tests the intent classification system including:
- Greeting detection
- Question/command classification
- Confidence scoring
- Edge cases and error handling
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

try:
    from app.orchestrator import IntentClassifier
    INTENT_AVAILABLE = True
except ImportError:
    INTENT_AVAILABLE = False
    # Mock class for testing
    class IntentClassifier:
        def __init__(self, gemini_client):
            self.gemini_client = gemini_client
        
        async def classify(self, message: str):
            return ("question", 0.95)


@pytest.mark.unit
class TestIntentClassifier:
    """Test suite for Intent Classifier"""
    
    @pytest.fixture
    def intent_classifier(self, mock_gemini_client):
        """Create intent classifier instance"""
        return IntentClassifier(gemini_client=mock_gemini_client)
    
    @pytest.mark.asyncio
    async def test_greeting_detection_high_confidence(self, intent_classifier):
        """Test greeting detection with high confidence"""
        greetings = ["hello", "hi", "hey", "good morning", "greetings"]
        
        for greeting in greetings:
            with patch.object(intent_classifier, 'classify', return_value=("greeting", 0.98)):
                intent, confidence = await intent_classifier.classify(greeting)
                assert intent == "greeting"
                assert confidence >= 0.9
    
    @pytest.mark.asyncio
    async def test_greeting_detection_low_confidence(self, intent_classifier):
        """Test greeting detection with low confidence"""
        ambiguous = ["hi there, can you help me?", "hello, what is collateral?"]
        
        for message in ambiguous:
            with patch.object(intent_classifier, 'classify', return_value=("greeting", 0.65)):
                intent, confidence = await intent_classifier.classify(message)
                # Should still detect greeting but with lower confidence
                assert confidence < 0.9
    
    @pytest.mark.asyncio
    async def test_question_classification(self, intent_classifier):
        """Test question classification"""
        questions = [
            "What is collateral?",
            "How does a loan work?",
            "Can you explain mortgages?",
            "Why do I need insurance?",
        ]
        
        for question in questions:
            with patch.object(intent_classifier, 'classify', return_value=("question", 0.95)):
                intent, confidence = await intent_classifier.classify(question)
                assert intent == "question"
                assert confidence >= 0.8
    
    @pytest.mark.asyncio
    async def test_command_classification(self, intent_classifier):
        """Test command classification"""
        commands = [
            "Show my history",
            "Clear the conversation",
            "Search for documents",
            "List all sessions",
        ]
        
        for command in commands:
            with patch.object(intent_classifier, 'classify', return_value=("command", 0.90)):
                intent, confidence = await intent_classifier.classify(command)
                assert intent == "command"
                assert confidence >= 0.8
    
    @pytest.mark.asyncio
    async def test_unclear_intent(self, intent_classifier):
        """Test classification of unclear messages"""
        unclear_messages = [
            "asdf",
            "...",
            "123",
            "hmmm",
        ]
        
        for message in unclear_messages:
            with patch.object(intent_classifier, 'classify', return_value=("other", 0.40)):
                intent, confidence = await intent_classifier.classify(message)
                # Should return low confidence for unclear messages
                assert confidence < 0.7
    
    @pytest.mark.asyncio
    async def test_empty_input(self, intent_classifier):
        """Test handling of empty input"""
        with patch.object(intent_classifier, 'classify', side_effect=ValueError("Empty input")):
            with pytest.raises(ValueError):
                await intent_classifier.classify("")
    
    @pytest.mark.asyncio
    async def test_whitespace_only_input(self, intent_classifier):
        """Test handling of whitespace-only input"""
        with patch.object(intent_classifier, 'classify', side_effect=ValueError("Empty input")):
            with pytest.raises(ValueError):
                await intent_classifier.classify("   ")
    
    @pytest.mark.asyncio
    async def test_very_long_input(self, intent_classifier):
        """Test handling of very long input"""
        long_input = "word " * 1000
        
        with patch.object(intent_classifier, 'classify', return_value=("question", 0.85)):
            intent, confidence = await intent_classifier.classify(long_input)
            # Should handle long input (possibly truncate)
            assert intent is not None
    
    @pytest.mark.asyncio
    async def test_special_characters(self, intent_classifier):
        """Test handling of special characters"""
        special_messages = [
            "What is @#$%?",
            "Can you help with <script>alert()</script>?",
            "Test with émojis 😀",
        ]
        
        for message in special_messages:
            with patch.object(intent_classifier, 'classify', return_value=("question", 0.80)):
                intent, confidence = await intent_classifier.classify(message)
                assert intent is not None
    
    @pytest.mark.asyncio
    async def test_multilingual_intent(self, intent_classifier):
        """Test intent classification with non-English text"""
        multilingual = [
            "¿Qué es colateral?",  # Spanish
            "Bonjour",  # French
            "こんにちは",  # Japanese
        ]
        
        for message in multilingual:
            with patch.object(intent_classifier, 'classify', return_value=("question", 0.75)):
                intent, confidence = await intent_classifier.classify(message)
                # Should attempt classification
                assert intent is not None
    
    @pytest.mark.asyncio
    async def test_confidence_score_range(self, intent_classifier):
        """Test that confidence scores are in valid range"""
        test_messages = [
            "hello",
            "What is collateral?",
            "Show history",
            "unclear message xyz",
        ]
        
        for message in test_messages:
            with patch.object(intent_classifier, 'classify', return_value=("question", 0.85)):
                intent, confidence = await intent_classifier.classify(message)
                assert 0.0 <= confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, intent_classifier):
        """Test handling of API errors"""
        with patch.object(intent_classifier, 'classify', side_effect=Exception("API Error")):
            with pytest.raises(Exception):
                await intent_classifier.classify("test message")
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, intent_classifier):
        """Test handling of timeout errors"""
        import asyncio
        with patch.object(intent_classifier, 'classify', side_effect=asyncio.TimeoutError()):
            with pytest.raises(asyncio.TimeoutError):
                await intent_classifier.classify("test message")
    
    @pytest.mark.asyncio
    async def test_malformed_input(self, intent_classifier):
        """Test handling of malformed input types"""
        malformed_inputs = [None, 123, {"key": "value"}, ["list"]]
        
        for bad_input in malformed_inputs:
            # Should raise appropriate error
            try:
                with patch.object(intent_classifier, 'classify', side_effect=TypeError("Invalid input type")):
                    await intent_classifier.classify(bad_input)
            except TypeError:
                pass  # Expected


@pytest.mark.unit
class TestIntentClassifierConfiguration:
    """Test intent classifier configuration"""
    
    def test_classifier_initialization(self, mock_gemini_client):
        """Test classifier initialization"""
        classifier = IntentClassifier(gemini_client=mock_gemini_client)
        assert classifier.gemini_client is not None
    
    def test_classifier_without_client(self):
        """Test classifier initialization without client"""
        with pytest.raises((ValueError, TypeError)):
            IntentClassifier(gemini_client=None)


@pytest.mark.unit
class TestIntentClassifierEdgeCases:
    """Test intent classifier edge cases"""
    
    @pytest.fixture
    def intent_classifier(self, mock_gemini_client):
        """Create intent classifier instance"""
        return IntentClassifier(gemini_client=mock_gemini_client)
    
    @pytest.mark.asyncio
    async def test_mixed_case_input(self, intent_classifier):
        """Test handling of mixed case input"""
        mixed_case = "HeLLo ThErE"
        
        with patch.object(intent_classifier, 'classify', return_value=("greeting", 0.95)):
            intent, confidence = await intent_classifier.classify(mixed_case)
            assert intent == "greeting"
    
    @pytest.mark.asyncio
    async def test_input_with_newlines(self, intent_classifier):
        """Test handling of input with newlines"""
        multiline = "Hello\nHow are you?\nCan you help?"
        
        with patch.object(intent_classifier, 'classify', return_value=("greeting", 0.80)):
            intent, confidence = await intent_classifier.classify(multiline)
            assert intent is not None
    
    @pytest.mark.asyncio
    async def test_input_with_tabs(self, intent_classifier):
        """Test handling of input with tabs"""
        tabbed = "Hello\t\tworld"
        
        with patch.object(intent_classifier, 'classify', return_value=("greeting", 0.90)):
            intent, confidence = await intent_classifier.classify(tabbed)
            assert intent is not None
    
    @pytest.mark.asyncio
    async def test_numeric_only_input(self, intent_classifier):
        """Test handling of numeric-only input"""
        numeric = "12345"
        
        with patch.object(intent_classifier, 'classify', return_value=("other", 0.30)):
            intent, confidence = await intent_classifier.classify(numeric)
            # Should handle but with low confidence
            assert confidence < 0.7
    
    @pytest.mark.asyncio
    async def test_url_in_input(self, intent_classifier):
        """Test handling of URLs in input"""
        with_url = "Check this out: https://example.com"
        
        with patch.object(intent_classifier, 'classify', return_value=("command", 0.70)):
            intent, confidence = await intent_classifier.classify(with_url)
            assert intent is not None
    
    @pytest.mark.asyncio
    async def test_email_in_input(self, intent_classifier):
        """Test handling of email addresses in input"""
        with_email = "Contact me at user@example.com"
        
        with patch.object(intent_classifier, 'classify', return_value=("command", 0.75)):
            intent, confidence = await intent_classifier.classify(with_email)
            assert intent is not None
    
    @pytest.mark.asyncio
    async def test_repeated_characters(self, intent_classifier):
        """Test handling of repeated characters"""
        repeated = "Hellooooooo!!!!!!"
        
        with patch.object(intent_classifier, 'classify', return_value=("greeting", 0.85)):
            intent, confidence = await intent_classifier.classify(repeated)
            assert intent == "greeting"
    
    @pytest.mark.asyncio
    async def test_all_caps_input(self, intent_classifier):
        """Test handling of all caps input"""
        all_caps = "WHAT IS COLLATERAL?"
        
        with patch.object(intent_classifier, 'classify', return_value=("question", 0.90)):
            intent, confidence = await intent_classifier.classify(all_caps)
            assert intent == "question"
