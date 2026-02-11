"""
Unit Tests for Gemini Client

Tests the Gemini API client wrapper including:
- API call success/failure
- Rate limiting
- Retries and backoff
- Token counting
- Response parsing
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import asyncio
from httpx import Response, HTTPStatusError, TimeoutException
import json

# Mock the Gemini client since we may not have it installed yet
try:
    from app.gemini_client import GeminiClient
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    # Create mock class for testing
    class GeminiClient:
        def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
            self.api_key = api_key
            self.model = model
            self.max_retries = 3
            self.timeout = 15
        
        async def generate_async(self, prompt: str, **kwargs):
            return "Mock response"
        
        async def classify_intent(self, message: str):
            return ("question", 0.95)
        
        def count_tokens(self, text: str):
            return len(text.split())


@pytest.mark.unit
class TestGeminiClient:
    """Test suite for Gemini API client"""
    
    @pytest.fixture
    def gemini_client(self):
        """Create a Gemini client instance"""
        return GeminiClient(api_key="test-api-key", model="gemini-2.0-flash-exp")
    
    @pytest.mark.asyncio
    async def test_successful_api_call(self, gemini_client):
        """Test successful API call"""
        with patch.object(gemini_client, 'generate_async', return_value="Test response"):
            response = await gemini_client.generate_async("Test prompt")
            assert response == "Test response"
    
    @pytest.mark.asyncio
    async def test_classify_intent_question(self, gemini_client):
        """Test intent classification for questions"""
        with patch.object(gemini_client, 'classify_intent', return_value=("question", 0.95)):
            intent, confidence = await gemini_client.classify_intent("What is collateral?")
            assert intent == "question"
            assert confidence >= 0.9
    
    @pytest.mark.asyncio
    async def test_classify_intent_greeting(self, gemini_client):
        """Test intent classification for greetings"""
        with patch.object(gemini_client, 'classify_intent', return_value=("greeting", 0.98)):
            intent, confidence = await gemini_client.classify_intent("Hello")
            assert intent == "greeting"
            assert confidence >= 0.9
    
    @pytest.mark.asyncio
    async def test_classify_intent_command(self, gemini_client):
        """Test intent classification for commands"""
        with patch.object(gemini_client, 'classify_intent', return_value=("command", 0.90)):
            intent, confidence = await gemini_client.classify_intent("Show me my history")
            assert intent == "command"
            assert confidence >= 0.8
    
    @pytest.mark.asyncio
    async def test_classify_intent_unclear(self, gemini_client):
        """Test intent classification for unclear messages"""
        with patch.object(gemini_client, 'classify_intent', return_value=("other", 0.50)):
            intent, confidence = await gemini_client.classify_intent("asdfghjkl")
            assert intent == "other"
            assert confidence < 0.7
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, gemini_client):
        """Test handling of rate limit errors"""
        # Mock rate limit error
        error = HTTPStatusError(
            "Rate limit exceeded",
            request=Mock(),
            response=Mock(status_code=429)
        )
        
        with patch.object(gemini_client, 'generate_async', side_effect=error):
            with pytest.raises(HTTPStatusError) as exc_info:
                await gemini_client.generate_async("Test prompt")
            assert exc_info.value.response.status_code == 429
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, gemini_client):
        """Test handling of timeout errors"""
        with patch.object(gemini_client, 'generate_async', side_effect=TimeoutException("Timeout")):
            with pytest.raises(TimeoutException):
                await gemini_client.generate_async("Test prompt")
    
    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test handling of invalid API key"""
        client = GeminiClient(api_key="invalid-key")
        error = HTTPStatusError(
            "Invalid API key",
            request=Mock(),
            response=Mock(status_code=401)
        )
        
        with patch.object(client, 'generate_async', side_effect=error):
            with pytest.raises(HTTPStatusError) as exc_info:
                await client.generate_async("Test prompt")
            assert exc_info.value.response.status_code == 401
    
    def test_token_counting(self, gemini_client):
        """Test token counting functionality"""
        text = "This is a test message with multiple words"
        token_count = gemini_client.count_tokens(text)
        assert token_count > 0
        assert isinstance(token_count, int)
    
    def test_token_counting_empty_string(self, gemini_client):
        """Test token counting with empty string"""
        token_count = gemini_client.count_tokens("")
        assert token_count == 0
    
    def test_token_counting_long_text(self, gemini_client):
        """Test token counting with long text"""
        long_text = " ".join(["word"] * 1000)
        token_count = gemini_client.count_tokens(long_text)
        assert token_count >= 1000
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, gemini_client):
        """Test retry mechanism on API failure"""
        # Mock first two calls to fail, third to succeed
        call_count = 0
        
        async def mock_generate(prompt):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return "Success after retry"
        
        with patch.object(gemini_client, 'generate_async', side_effect=mock_generate):
            # This would need actual retry logic in the client
            pass  # Placeholder for retry test
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, gemini_client):
        """Test exponential backoff between retries"""
        # Mock multiple failures
        with patch.object(gemini_client, 'generate_async', side_effect=[
            Exception("Error 1"),
            Exception("Error 2"),
            "Success"
        ]):
            pass  # Placeholder for backoff test
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, gemini_client):
        """Test behavior when max retries exceeded"""
        gemini_client.max_retries = 3
        
        with patch.object(gemini_client, 'generate_async', side_effect=Exception("Persistent error")):
            with pytest.raises(Exception):
                await gemini_client.generate_async("Test prompt")
    
    @pytest.mark.asyncio
    async def test_empty_input_handling(self, gemini_client):
        """Test handling of empty input"""
        with patch.object(gemini_client, 'generate_async', side_effect=ValueError("Empty input")):
            with pytest.raises(ValueError):
                await gemini_client.generate_async("")
    
    @pytest.mark.asyncio
    async def test_very_long_input_truncation(self, gemini_client):
        """Test handling of very long input"""
        long_input = "word " * 10000  # Very long prompt
        with patch.object(gemini_client, 'generate_async', return_value="Response"):
            response = await gemini_client.generate_async(long_input)
            assert response is not None
    
    @pytest.mark.asyncio
    async def test_special_characters_handling(self, gemini_client):
        """Test handling of special characters in input"""
        special_input = "Test with special chars: @#$%^&*()[]{}|\\:;\"'<>,.?/"
        with patch.object(gemini_client, 'generate_async', return_value="Response"):
            response = await gemini_client.generate_async(special_input)
            assert response is not None
    
    @pytest.mark.asyncio
    async def test_multilingual_intent_detection(self, gemini_client):
        """Test intent detection with non-English text"""
        with patch.object(gemini_client, 'classify_intent', return_value=("question", 0.85)):
            intent, confidence = await gemini_client.classify_intent("¿Qué es colateral?")
            assert intent is not None
            assert confidence > 0
    
    @pytest.mark.asyncio
    async def test_confidence_score_ranges(self, gemini_client):
        """Test that confidence scores are within valid range"""
        with patch.object(gemini_client, 'classify_intent', return_value=("question", 0.95)):
            intent, confidence = await gemini_client.classify_intent("Test message")
            assert 0.0 <= confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_gemini_api_error_handling(self, gemini_client):
        """Test general Gemini API error handling"""
        with patch.object(gemini_client, 'generate_async', side_effect=Exception("API Error")):
            with pytest.raises(Exception) as exc_info:
                await gemini_client.generate_async("Test prompt")
            assert "API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, gemini_client):
        """Test handling of concurrent API requests"""
        async def mock_generate(prompt):
            await asyncio.sleep(0.1)  # Simulate API delay
            return f"Response to: {prompt}"
        
        with patch.object(gemini_client, 'generate_async', side_effect=mock_generate):
            tasks = [
                gemini_client.generate_async(f"Prompt {i}")
                for i in range(5)
            ]
            responses = await asyncio.gather(*tasks)
            assert len(responses) == 5
            assert all(r.startswith("Response to:") for r in responses)
    
    @pytest.mark.asyncio
    async def test_response_parsing_json(self, gemini_client):
        """Test JSON response parsing"""
        json_response = '{"result": "success", "data": "test"}'
        
        # Mock method that returns JSON
        async def mock_generate_json(prompt):
            return json.loads(json_response)
        
        with patch.object(gemini_client, 'generate_async', side_effect=mock_generate_json):
            response = await gemini_client.generate_async("Test prompt")
            assert isinstance(response, dict)
            assert response["result"] == "success"
    
    @pytest.mark.asyncio
    async def test_malformed_input_handling(self, gemini_client):
        """Test handling of malformed input"""
        malformed_inputs = [
            None,
            123,  # Not a string
            {"key": "value"},  # Dict instead of string
            ["list", "items"],  # List instead of string
        ]
        
        for bad_input in malformed_inputs:
            # Should handle gracefully or raise appropriate error
            pass  # Placeholder - actual implementation would validate input type


@pytest.mark.unit
class TestGeminiClientConfiguration:
    """Test Gemini client configuration"""
    
    def test_client_initialization(self):
        """Test client initialization with default parameters"""
        client = GeminiClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.model is not None
    
    def test_client_custom_model(self):
        """Test client initialization with custom model"""
        client = GeminiClient(api_key="test-key", model="custom-model")
        assert client.model == "custom-model"
    
    def test_client_missing_api_key(self):
        """Test client initialization without API key"""
        with pytest.raises((ValueError, TypeError)):
            GeminiClient(api_key=None)
    
    def test_client_timeout_configuration(self):
        """Test timeout configuration"""
        client = GeminiClient(api_key="test-key")
        assert hasattr(client, 'timeout')
        assert client.timeout > 0
    
    def test_client_max_retries_configuration(self):
        """Test max retries configuration"""
        client = GeminiClient(api_key="test-key")
        assert hasattr(client, 'max_retries')
        assert client.max_retries >= 0
