"""
Configuration Management
Loads and validates environment variables
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """Application configuration."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration from environment variables.
        
        Args:
            env_file: Path to .env file (optional)
        """
        # Load .env file
        if env_file:
            load_dotenv(env_file)
        else:
            # Try to load from default locations
            env_paths = [
                Path.cwd() / ".env",
                Path(__file__).parent.parent / ".env"
            ]
            for path in env_paths:
                if path.exists():
                    load_dotenv(path)
                    logger.info(f"Loaded environment from: {path}")
                    break
        
        # Gemini Configuration
        self.gemini_api_key = self._get_required("GEMINI_API_KEY")
        self.gemini_model = self._get_env("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.gemini_max_retries = self._get_int("GEMINI_MAX_RETRIES", 3)
        self.gemini_timeout = self._get_int("GEMINI_TIMEOUT_SECONDS", 15)
        
        # Database Configuration
        self.db_path = self._get_env("SQLITE_DB_PATH", "./database/loan_collateral.db")
        self.db_pool_size = self._get_int("DB_POOL_SIZE", 5)
        
        # Ensure database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # ChromaDB Configuration
        self.chromadb_path = self._get_env("CHROMADB_PATH", "./data/chromadb")
        self.chromadb_collection = self._get_env("CHROMADB_COLLECTION", "loan_documents")
        
        # Ensure ChromaDB directory exists
        Path(self.chromadb_path).mkdir(parents=True, exist_ok=True)
        
        # Search Configuration
        self.serp_api_key = self._get_env("SERP_API_KEY", "")
        self.enable_web_search = self._get_bool("ENABLE_WEB_SEARCH", False)
        self.max_search_results = self._get_int("MAX_SEARCH_RESULTS", 5)
        
        # RAG Configuration
        self.rag_top_k = self._get_int("RAG_TOP_K", 5)
        self.rag_max_tokens = self._get_int("RAG_MAX_TOKENS", 4000)
        self.enable_search_cache = self._get_bool("ENABLE_SEARCH_CACHE", True)
        self.cache_ttl = self._get_int("CACHE_TTL_SECONDS", 3600)
        
        # Planner-Critique Configuration
        self.max_critique_iterations = self._get_int("MAX_CRITIQUE_ITERATIONS", 2)
        self.critique_threshold = self._get_float("CRITIQUE_ACCEPTANCE_THRESHOLD", 0.85)
        self.enable_critique = self._get_bool("ENABLE_CRITIQUE", True)
        
        # Context Management
        self.max_history_items = self._get_int("MAX_HISTORY_ITEMS", 5)
        self.max_history_tokens = self._get_int("MAX_HISTORY_TOKENS", 2000)
        self.context_prune_days = self._get_int("CONTEXT_PRUNE_DAYS", 30)
        
        # Performance Settings
        self.token_budget_max = self._get_int("TOKEN_BUDGET_MAX", 8000)
        self.target_latency_ms = self._get_int("TARGET_LATENCY_MS", 8000)
        self.enable_async = self._get_bool("ENABLE_ASYNC", True)
        
        # Caching Settings
        self.enable_response_cache = self._get_bool("ENABLE_RESPONSE_CACHE", True)
        self.response_cache_ttl = self._get_int("RESPONSE_CACHE_TTL", 7200)
        self.cache_hit_rate_target = self._get_float("CACHE_HIT_RATE_TARGET", 0.6)
        
        # Logging Configuration
        self.log_level = self._get_env("LOG_LEVEL", "INFO")
        self.log_format = self._get_env("LOG_FORMAT", "json")
        self.log_file = self._get_env("LOG_FILE", "./logs/app.log")
        
        # Ensure log directory exists
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # LangFlow Configuration
        self.langflow_host = self._get_env("LANGFLOW_HOST", "0.0.0.0")
        self.langflow_port = self._get_int("LANGFLOW_PORT", 7860)
        self.langflow_workers = self._get_int("LANGFLOW_WORKERS", 1)
        
        # Security
        self.max_request_size_mb = self._get_int("MAX_REQUEST_SIZE_MB", 10)
        self.rate_limit_per_minute = self._get_int("RATE_LIMIT_PER_MINUTE", 60)
        
        # Monitoring
        self.enable_metrics = self._get_bool("ENABLE_METRICS", True)
        self.metrics_interval = self._get_int("METRICS_INTERVAL_SECONDS", 60)
        
        logger.info("Configuration loaded successfully")
    
    @staticmethod
    def _get_env(key: str, default: str = "") -> str:
        """Get environment variable."""
        return os.getenv(key, default)
    
    @staticmethod
    def _get_required(key: str) -> str:
        """Get required environment variable."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable not set: {key}")
        return value
    
    @staticmethod
    def _get_int(key: str, default: int = 0) -> int:
        """Get integer environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Invalid integer for {key}: {value}, using default: {default}")
            return default
    
    @staticmethod
    def _get_float(key: str, default: float = 0.0) -> float:
        """Get float environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            logger.warning(f"Invalid float for {key}: {value}, using default: {default}")
            return default
    
    @staticmethod
    def _get_bool(key: str, default: bool = False) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")
    
    def validate(self):
        """Validate configuration."""
        errors = []
        
        # Check API key
        if not self.gemini_api_key or self.gemini_api_key == "your_gemini_api_key_here":
            errors.append("GEMINI_API_KEY not configured")
        
        # Check paths
        if not Path(self.db_path).parent.exists():
            errors.append(f"Database directory does not exist: {Path(self.db_path).parent}")
        
        # Check reasonable values
        if self.max_critique_iterations < 1 or self.max_critique_iterations > 5:
            errors.append("MAX_CRITIQUE_ITERATIONS should be between 1 and 5")
        
        if self.critique_threshold < 0.5 or self.critique_threshold > 1.0:
            errors.append("CRITIQUE_ACCEPTANCE_THRESHOLD should be between 0.5 and 1.0")
        
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
        
        logger.info("Configuration validation passed")
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "gemini": {
                "model": self.gemini_model,
                "max_retries": self.gemini_max_retries,
                "timeout": self.gemini_timeout
            },
            "database": {
                "path": self.db_path,
                "pool_size": self.db_pool_size
            },
            "chromadb": {
                "path": self.chromadb_path,
                "collection": self.chromadb_collection
            },
            "rag": {
                "top_k": self.rag_top_k,
                "max_tokens": self.rag_max_tokens,
                "cache_enabled": self.enable_search_cache
            },
            "critique": {
                "max_iterations": self.max_critique_iterations,
                "threshold": self.critique_threshold,
                "enabled": self.enable_critique
            },
            "performance": {
                "token_budget": self.token_budget_max,
                "target_latency_ms": self.target_latency_ms,
                "async_enabled": self.enable_async
            }
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config(env_file: Optional[str] = None) -> Config:
    """
    Get global configuration instance.
    
    Args:
        env_file: Path to .env file (only used on first call)
        
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(env_file)
    return _config


def reload_config(env_file: Optional[str] = None):
    """Reload configuration from environment."""
    global _config
    _config = Config(env_file)
    return _config
