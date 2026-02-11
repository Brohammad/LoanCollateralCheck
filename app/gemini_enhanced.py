"""
Enhanced Gemini API Client
Async client with retry logic, caching, token counting, and structured logging
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """API error categories."""
    RATE_LIMIT = "rate_limit"
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    AUTHENTICATION = "authentication"
    UNKNOWN = "unknown"


@dataclass
class TokenUsage:
    """Token usage tracking."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
    @property
    def estimated_cost(self) -> float:
        """Estimate cost based on Gemini pricing (Flash 2.0)."""
        # Flash 2.0 Experimental pricing (as of Feb 2026)
        # Input: $0.10 per 1M tokens, Output: $0.30 per 1M tokens
        input_cost = (self.prompt_tokens / 1_000_000) * 0.10
        output_cost = (self.completion_tokens / 1_000_000) * 0.30
        return input_cost + output_cost


@dataclass
class GeminiResponse:
    """Structured response from Gemini API."""
    text: str
    token_usage: TokenUsage
    model_name: str
    latency_ms: int
    from_cache: bool = False
    finish_reason: Optional[str] = None
    safety_ratings: Optional[List[Dict]] = None


class GeminiClient:
    """Enhanced Gemini API client with advanced features."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        max_retries: int = 3,
        timeout_seconds: int = 15,
        enable_cache: bool = True,
        cache_ttl: int = 7200,
        db_manager: Optional[Any] = None
    ):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google AI API key
            model_name: Model identifier
            max_retries: Maximum retry attempts
            timeout_seconds: Request timeout
            enable_cache: Enable response caching
            cache_ttl: Cache TTL in seconds
            db_manager: Database manager for caching
        """
        self.api_key = api_key
        self.model_name = model_name
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.db_manager = db_manager
        
        # Configure API
        genai.configure(api_key=api_key)
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=model_name,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        
        # Statistics
        self.total_requests = 0
        self.total_tokens = 0
        self.cache_hits = 0
        self.failed_requests = 0
        
        logger.info(f"Gemini client initialized: {model_name}")
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Estimate token count.
        Rough estimation: 1 token ≈ 4 characters for English text.
        """
        return len(text) // 4
    
    def _get_cache_key(self, prompt: str, generation_config: Dict) -> str:
        """Generate cache key for request."""
        content = f"{self.model_name}:{prompt}:{json.dumps(generation_config, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def generate_async(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 0.95,
        top_k: int = 40,
        system_instruction: Optional[str] = None,
        enforce_token_budget: bool = True,
        max_budget: int = 8000
    ) -> GeminiResponse:
        """
        Generate response asynchronously with retry logic.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum output tokens
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            system_instruction: System instruction for the model
            enforce_token_budget: Enforce token budget limits
            max_budget: Maximum total tokens allowed
            
        Returns:
            GeminiResponse object
        """
        start_time = time.time()
        
        # Token budget check
        prompt_tokens = self.count_tokens(prompt)
        if system_instruction:
            prompt_tokens += self.count_tokens(system_instruction)
        
        if enforce_token_budget and prompt_tokens > max_budget * 0.6:
            raise ValueError(
                f"Prompt too long: {prompt_tokens} tokens (limit: {int(max_budget * 0.6)})"
            )
        
        # Check cache first
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "top_p": top_p,
            "top_k": top_k
        }
        
        if self.enable_cache and self.db_manager:
            cache_key = self._get_cache_key(prompt, generation_config)
            cached = self.db_manager.get_cached_response(cache_key, self.model_name)
            
            if cached:
                response_text, token_count = cached
                self.cache_hits += 1
                latency_ms = int((time.time() - start_time) * 1000)
                
                logger.info(f"Cache hit for prompt (length: {len(prompt)})")
                
                return GeminiResponse(
                    text=response_text,
                    token_usage=TokenUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=self.count_tokens(response_text),
                        total_tokens=token_count
                    ),
                    model_name=self.model_name,
                    latency_ms=latency_ms,
                    from_cache=True
                )
        
        # Make API call with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self._make_request(
                    prompt=prompt,
                    generation_config=generation_config,
                    system_instruction=system_instruction
                )
                
                # Process response
                response_text = response.text
                completion_tokens = self.count_tokens(response_text)
                total_tokens = prompt_tokens + completion_tokens
                
                # Update statistics
                self.total_requests += 1
                self.total_tokens += total_tokens
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Cache the response
                if self.enable_cache and self.db_manager:
                    cache_key = self._get_cache_key(prompt, generation_config)
                    self.db_manager.cache_response(
                        input_text=cache_key,
                        model_name=self.model_name,
                        response_text=response_text,
                        token_count=total_tokens,
                        ttl_seconds=self.cache_ttl
                    )
                
                # Log API call
                if self.db_manager:
                    self.db_manager.log_api_call(
                        api_name="gemini",
                        endpoint=self.model_name,
                        request_method="generate",
                        request_params={"prompt_length": len(prompt)},
                        response_status=200,
                        response_time_ms=latency_ms,
                        token_count=total_tokens
                    )
                
                logger.info(
                    f"Gemini API success: {total_tokens} tokens, "
                    f"{latency_ms}ms, attempt {attempt + 1}/{self.max_retries}"
                )
                
                return GeminiResponse(
                    text=response_text,
                    token_usage=TokenUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens
                    ),
                    model_name=self.model_name,
                    latency_ms=latency_ms,
                    from_cache=False,
                    finish_reason=getattr(response, 'finish_reason', None),
                    safety_ratings=getattr(response, 'safety_ratings', None)
                )
                
            except asyncio.TimeoutError:
                last_error = ErrorType.TIMEOUT
                wait_time = 2 ** attempt
                logger.warning(
                    f"Timeout on attempt {attempt + 1}/{self.max_retries}, "
                    f"retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Categorize error
                if "rate limit" in error_str or "quota" in error_str:
                    last_error = ErrorType.RATE_LIMIT
                    wait_time = 5 * (2 ** attempt)  # Longer backoff for rate limits
                elif "authentication" in error_str or "api key" in error_str:
                    last_error = ErrorType.AUTHENTICATION
                    raise  # Don't retry auth errors
                elif "invalid" in error_str or "bad request" in error_str:
                    last_error = ErrorType.INVALID_REQUEST
                    raise  # Don't retry invalid requests
                else:
                    last_error = ErrorType.API_ERROR
                    wait_time = 2 ** attempt
                
                logger.warning(
                    f"API error ({last_error.value}) on attempt {attempt + 1}/{self.max_retries}: {e}"
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    # Log failed request
                    if self.db_manager:
                        self.db_manager.log_api_call(
                            api_name="gemini",
                            endpoint=self.model_name,
                            request_method="generate",
                            request_params={"prompt_length": len(prompt)},
                            response_status=500,
                            response_time_ms=int((time.time() - start_time) * 1000),
                            error_message=str(e)
                        )
        
        # All retries failed
        self.failed_requests += 1
        raise Exception(
            f"Failed after {self.max_retries} attempts. Last error: {last_error.value if last_error else 'unknown'}"
        )
    
    async def _make_request(
        self,
        prompt: str,
        generation_config: Dict,
        system_instruction: Optional[str] = None
    ):
        """Make the actual API request with timeout."""
        # Create model with system instruction if provided
        model = self.model
        if system_instruction:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction,
                safety_settings=self.model._safety_settings
            )
        
        # Generate with timeout
        response = await asyncio.wait_for(
            asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=generation_config
            ),
            timeout=self.timeout_seconds
        )
        
        return response
    
    def generate_sync(self, prompt: str, **kwargs) -> GeminiResponse:
        """Synchronous wrapper for generate_async."""
        return asyncio.run(self.generate_async(prompt, **kwargs))
    
    async def generate_with_json(
        self,
        prompt: str,
        schema: Optional[Dict] = None,
        **kwargs
    ) -> Tuple[Dict, GeminiResponse]:
        """
        Generate response and parse as JSON.
        
        Args:
            prompt: Input prompt (should request JSON output)
            schema: Optional JSON schema for validation
            **kwargs: Additional generation parameters
            
        Returns:
            Tuple of (parsed_json, response)
        """
        # Ensure prompt requests JSON
        if "json" not in prompt.lower():
            prompt += "\n\nProvide your response in valid JSON format."
        
        response = await self.generate_async(prompt, **kwargs)
        
        # Try to extract JSON from response
        text = response.text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        
        try:
            parsed = json.loads(text)
            
            # Validate against schema if provided
            if schema:
                # Basic schema validation (expand as needed)
                if "required" in schema:
                    for field in schema["required"]:
                        if field not in parsed:
                            raise ValueError(f"Missing required field: {field}")
            
            return parsed, response
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}\nResponse: {text[:200]}...")
            raise ValueError(f"Invalid JSON in response: {e}")
    
    async def classify_intent(
        self,
        user_message: str,
        intents: List[str] = None
    ) -> Tuple[str, float]:
        """
        Classify user intent.
        
        Args:
            user_message: User's message
            intents: List of possible intents (default: greeting, question, command)
            
        Returns:
            Tuple of (intent, confidence)
        """
        if intents is None:
            intents = ["greeting", "question", "command", "clarification", "other"]
        
        prompt = f"""Classify the following user message into one of these intents: {', '.join(intents)}

User message: "{user_message}"

Provide your response in this exact JSON format:
{{
    "intent": "<intent>",
    "confidence": <0.0-1.0>,
    "reasoning": "<brief explanation>"
}}"""
        
        try:
            parsed, _ = await self.generate_with_json(
                prompt,
                temperature=0.3,
                max_tokens=100
            )
            
            return parsed.get("intent", "other"), parsed.get("confidence", 0.5)
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return "other", 0.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get client statistics."""
        cache_hit_rate = (
            self.cache_hits / self.total_requests
            if self.total_requests > 0
            else 0.0
        )
        
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": cache_hit_rate,
            "failed_requests": self.failed_requests,
            "avg_tokens_per_request": (
                self.total_tokens / self.total_requests
                if self.total_requests > 0
                else 0
            )
        }
    
    def reset_statistics(self):
        """Reset statistics counters."""
        self.total_requests = 0
        self.total_tokens = 0
        self.cache_hits = 0
        self.failed_requests = 0


# Convenience function for quick usage
async def generate_text(
    prompt: str,
    api_key: str,
    model_name: str = "gemini-2.0-flash-exp",
    **kwargs
) -> str:
    """
    Quick helper to generate text without creating a client.
    
    Args:
        prompt: Input prompt
        api_key: Google AI API key
        model_name: Model identifier
        **kwargs: Additional generation parameters
        
    Returns:
        Generated text
    """
    client = GeminiClient(api_key=api_key, model_name=model_name, enable_cache=False)
    response = await client.generate_async(prompt, **kwargs)
    return response.text
