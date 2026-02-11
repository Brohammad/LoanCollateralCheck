"""Wrapper for Google Gemini generative and embedding calls.

This file implements:
- text generation (gemini-2.0-flash-exp model)
- embeddings (text-embedding-004)
- configurable temperature and max tokens
- safety settings
"""
from typing import Dict, Any, List, Optional
import os
import json
import requests

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1"


class GeminiClientError(RuntimeError):
    pass


class GeminiClient:
    """Client for Google Gemini API with support for generation and embeddings."""

    def __init__(
        self,
        api_key: str | None = None,
        generation_model: str = "gemini-2.0-flash",
        embedding_model: str = "text-embedding-004",
    ):
        self.api_key = api_key or GOOGLE_API_KEY
        self.generation_model = generation_model
        self.embedding_model = embedding_model
        self._configured = bool(self.api_key)

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        safety_settings: str = "medium",
        **kwargs,
    ) -> str:
        """Generate text using Gemini Flash 2.0 experimental.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            safety_settings: Safety level (low, medium, high)
            **kwargs: Additional parameters

        Returns:
            Generated text string
        """
        if not self._configured:
            raise GeminiClientError("Google API key not configured. Set GOOGLE_API_KEY or pass api_key.")

        # Map safety settings
        safety_map = {
            "low": "BLOCK_ONLY_HIGH",
            "medium": "BLOCK_MEDIUM_AND_ABOVE",
            "high": "BLOCK_LOW_AND_ABOVE",
        }
        safety_threshold = safety_map.get(safety_settings, "BLOCK_MEDIUM_AND_ABOVE")

        url = f"{GEMINI_BASE_URL}/models/{self.generation_model}:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topK": kwargs.get("top_k", 40),
                "topP": kwargs.get("top_p", 0.95),
            },
            "safetySettings": [
                {
                    "category": cat,
                    "threshold": safety_threshold,
                }
                for cat in [
                    "HARM_CATEGORY_HARASSMENT",
                    "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "HARM_CATEGORY_DANGEROUS_CONTENT",
                ]
            ],
        }

        try:
            response = requests.post(url, headers=headers, params=params, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extract text from response
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]

            # Fallback if response format is unexpected
            return f"[Gemini response parsing issue: {data}]"

        except requests.RequestException as e:
            raise GeminiClientError(f"Gemini API request failed: {e}")

    def classify_intent(
        self,
        text: str,
        intents: List[str] = ["greeting", "question", "command", "unclear"],
    ) -> Dict[str, Any]:
        """Classify user intent with confidence scoring.

        Args:
            text: Input text to classify
            intents: List of possible intent categories

        Returns:
            Dict with 'intent' (str) and 'confidence' (float)
        """
        prompt = f"""Classify the following user input into one of these categories: {', '.join(intents)}.
Respond with ONLY a JSON object in this exact format: {{"intent": "<category>", "confidence": <0.0-1.0>}}

User input: "{text}"

JSON response:"""

        try:
            response = self.generate(prompt, temperature=0.3, max_tokens=100)
            # Try to parse JSON from response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            result = json.loads(response)
            return {
                "intent": result.get("intent", "unclear"),
                "confidence": float(result.get("confidence", 0.5)),
            }
        except Exception as e:
            # Fallback: simple keyword matching for ANY error (API, JSON parsing, etc.)
            text_lower = text.lower().strip()
            if any(kw in text_lower for kw in ["hi", "hello", "hey", "good morning"]):
                return {"intent": "greeting", "confidence": 0.8}
            elif "?" in text or any(kw in text_lower for kw in ["what", "how", "why", "when", "where"]):
                return {"intent": "question", "confidence": 0.7}
            elif any(kw in text_lower for kw in ["do", "create", "make", "build", "run", "execute"]):
                return {"intent": "command", "confidence": 0.6}
            else:
                return {"intent": "unclear", "confidence": 0.4}

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Return embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (floats)
        """
        if not self._configured:
            raise GeminiClientError("Google API key not configured. Set GOOGLE_API_KEY or pass api_key.")

        url = f"{GEMINI_BASE_URL}/models/{self.embedding_model}:embedContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        embeddings = []
        for text in texts:
            payload = {
                "model": f"models/{self.embedding_model}",
                "content": {"parts": [{"text": text}]},
            }

            try:
                response = requests.post(url, headers=headers, params=params, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()

                if "embedding" in data and "values" in data["embedding"]:
                    embeddings.append(data["embedding"]["values"])
                else:
                    # Fallback: return zero vector
                    embeddings.append([0.0] * 768)

            except requests.RequestException as e:
                # Fallback for failed requests
                embeddings.append([0.0] * 768)

        return embeddings


# Helper factory
def get_gemini_client(
    generation_model: str = "gemini-2.0-flash-exp",
    embedding_model: str = "text-embedding-004",
) -> GeminiClient:
    """Factory function to create a configured GeminiClient."""
    return GeminiClient(generation_model=generation_model, embedding_model=embedding_model)
