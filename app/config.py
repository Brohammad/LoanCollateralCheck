"""Configuration management for the AI Agent Workflow system.

Centralizes all configuration including:
- API keys
- Model settings
- Database paths
- Safety and generation parameters
"""
import os
from typing import Dict, Any


class Config:
    """Configuration class for the AI Agent Workflow."""

    # Google Gemini API
    GOOGLE_API_KEY: str = os.environ.get("GOOGLE_API_KEY", "")
    GOOGLE_API_PROJECT: str = os.environ.get("GOOGLE_API_PROJECT", "")

    # Model settings
    GENERATION_MODEL: str = os.environ.get("GENERATION_MODEL", "gemini-2.0-flash-exp")
    EMBEDDING_MODEL: str = os.environ.get("EMBEDDING_MODEL", "text-embedding-004")

    # Generation parameters
    GENERATION_TEMPERATURE: float = float(os.environ.get("GENERATION_TEMPERATURE", "0.7"))
    CLASSIFICATION_TEMPERATURE: float = float(os.environ.get("CLASSIFICATION_TEMPERATURE", "0.3"))
    MAX_TOKENS: int = int(os.environ.get("MAX_TOKENS", "2048"))
    SAFETY_SETTINGS: str = os.environ.get("SAFETY_SETTINGS", "medium")

    # Database
    SQLITE_PATH: str = os.environ.get("SQLITE_PATH", "./data/credit_history.db")

    # Vector stores
    PINECONE_API_KEY: str = os.environ.get("PINECONE_API_KEY", "")
    PINECONE_ENV: str = os.environ.get("PINECONE_ENV", "us-west1-gcp")
    PINECONE_INDEX: str = os.environ.get("PINECONE_INDEX", "ai-agent-workflow")

    CHROMA_PERSIST_DIR: str = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")

    # Server
    HOST: str = os.environ.get("HOST", "127.0.0.1")
    PORT: int = int(os.environ.get("PORT", "8000"))

    # Orchestrator settings
    CONFIDENCE_THRESHOLD: float = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.6"))
    MAX_CRITIQUE_ITERATIONS: int = int(os.environ.get("MAX_CRITIQUE_ITERATIONS", "2"))

    # Cache settings
    CACHE_TTL_SECONDS: int = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert config to dictionary (excluding sensitive keys)."""
        return {
            "generation_model": cls.GENERATION_MODEL,
            "embedding_model": cls.EMBEDDING_MODEL,
            "generation_temperature": cls.GENERATION_TEMPERATURE,
            "classification_temperature": cls.CLASSIFICATION_TEMPERATURE,
            "max_tokens": cls.MAX_TOKENS,
            "safety_settings": cls.SAFETY_SETTINGS,
            "confidence_threshold": cls.CONFIDENCE_THRESHOLD,
            "max_critique_iterations": cls.MAX_CRITIQUE_ITERATIONS,
            "cache_ttl_seconds": cls.CACHE_TTL_SECONDS,
        }

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.GOOGLE_API_KEY:
            return False
        return True


# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass
