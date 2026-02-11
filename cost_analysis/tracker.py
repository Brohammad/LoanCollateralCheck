"""
Cost tracker for monitoring LLM API usage and costs in real-time.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uuid
from collections import defaultdict

from cost_analysis.models import (
    TokenUsage,
    CostRecord,
    ModelType,
    OperationType,
    CostCategory,
)
from cost_analysis.calculator import CostCalculator


class CostTracker:
    """
    Tracks token usage and costs for LLM operations.
    
    Features:
    - Real-time cost tracking
    - Per-user, per-session tracking
    - Aggregated metrics
    - In-memory and persistent storage
    """
    
    def __init__(
        self,
        calculator: Optional[CostCalculator] = None,
        enable_persistence: bool = True,
        persistence_interval: int = 60,  # seconds
    ):
        """
        Initialize cost tracker.
        
        Args:
            calculator: Cost calculator instance
            enable_persistence: Whether to persist data to database
            persistence_interval: How often to persist data (seconds)
        """
        self.calculator = calculator or CostCalculator()
        self.enable_persistence = enable_persistence
        self.persistence_interval = persistence_interval
        
        # In-memory storage
        self._token_usages: List[TokenUsage] = []
        self._cost_records: List[CostRecord] = []
        
        # Aggregated metrics
        self._metrics = {
            "total_tokens": 0,
            "total_cost": 0.0,
            "total_requests": 0,
            "by_user": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0}),
            "by_model": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0}),
            "by_operation": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0}),
            "cache_hits": 0,
            "cache_misses": 0,
        }
        
        # Background persistence task
        self._persistence_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the cost tracker."""
        if self._running:
            return
        
        self._running = True
        
        if self.enable_persistence:
            self._persistence_task = asyncio.create_task(self._persistence_loop())
    
    async def stop(self):
        """Stop the cost tracker and persist remaining data."""
        self._running = False
        
        if self._persistence_task:
            self._persistence_task.cancel()
            try:
                await self._persistence_task
            except asyncio.CancelledError:
                pass
        
        # Final persistence
        if self.enable_persistence:
            await self._persist_data()
    
    async def track_usage(
        self,
        model_type: ModelType,
        operation_type: OperationType,
        prompt_tokens: int,
        completion_tokens: int = 0,
        cached_tokens: int = 0,
        duration_ms: float = 0.0,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> tuple[TokenUsage, CostRecord]:
        """
        Track token usage and calculate cost.
        
        Args:
            model_type: Model used
            operation_type: Type of operation
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            cached_tokens: Tokens served from cache
            duration_ms: Operation duration
            user_id: User identifier
            session_id: Session identifier
            api_key_id: API key used
            metadata: Additional metadata
        
        Returns:
            Tuple of (TokenUsage, CostRecord)
        """
        operation_id = str(uuid.uuid4())
        
        # Create token usage record
        token_usage = TokenUsage(
            operation_id=operation_id,
            model_type=model_type,
            operation_type=operation_type,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cached_tokens=cached_tokens,
            timestamp=datetime.utcnow(),
            duration_ms=duration_ms,
            user_id=user_id,
            session_id=session_id,
            api_key_id=api_key_id,
            metadata=metadata or {},
        )
        
        # Calculate cost
        cost_record = await self.calculator.calculate_cost(token_usage)
        
        # Store in memory
        self._token_usages.append(token_usage)
        self._cost_records.append(cost_record)
        
        # Update metrics
        await self._update_metrics(token_usage, cost_record)
        
        return token_usage, cost_record
    
    async def _update_metrics(self, token_usage: TokenUsage, cost_record: CostRecord):
        """Update aggregated metrics."""
        # Total metrics
        self._metrics["total_tokens"] += token_usage.total_tokens
        self._metrics["total_cost"] += cost_record.total_cost
        self._metrics["total_requests"] += 1
        
        # By user
        if token_usage.user_id:
            user_metrics = self._metrics["by_user"][token_usage.user_id]
            user_metrics["tokens"] += token_usage.total_tokens
            user_metrics["cost"] += cost_record.total_cost
            user_metrics["requests"] += 1
        
        # By model
        model_metrics = self._metrics["by_model"][token_usage.model_type.value]
        model_metrics["tokens"] += token_usage.total_tokens
        model_metrics["cost"] += cost_record.total_cost
        model_metrics["requests"] += 1
        
        # By operation
        op_metrics = self._metrics["by_operation"][token_usage.operation_type.value]
        op_metrics["tokens"] += token_usage.total_tokens
        op_metrics["cost"] += cost_record.total_cost
        op_metrics["requests"] += 1
        
        # Cache metrics
        if token_usage.cached_tokens > 0:
            self._metrics["cache_hits"] += 1
        else:
            self._metrics["cache_misses"] += 1
    
    def get_metrics(
        self,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics.
        
        Args:
            period_start: Start of period (None for all time)
            period_end: End of period (None for now)
        
        Returns:
            Dictionary of metrics
        """
        if period_start is None and period_end is None:
            # Return current metrics
            return {
                "total_tokens": self._metrics["total_tokens"],
                "total_cost": self._metrics["total_cost"],
                "total_requests": self._metrics["total_requests"],
                "avg_cost_per_request": (
                    self._metrics["total_cost"] / self._metrics["total_requests"]
                    if self._metrics["total_requests"] > 0
                    else 0.0
                ),
                "avg_tokens_per_request": (
                    self._metrics["total_tokens"] / self._metrics["total_requests"]
                    if self._metrics["total_requests"] > 0
                    else 0.0
                ),
                "cache_hit_rate": (
                    self._metrics["cache_hits"]
                    / (self._metrics["cache_hits"] + self._metrics["cache_misses"])
                    if (self._metrics["cache_hits"] + self._metrics["cache_misses"]) > 0
                    else 0.0
                ),
                "by_user": dict(self._metrics["by_user"]),
                "by_model": dict(self._metrics["by_model"]),
                "by_operation": dict(self._metrics["by_operation"]),
            }
        
        # Filter by period
        filtered_usages = [
            usage
            for usage in self._token_usages
            if (period_start is None or usage.timestamp >= period_start)
            and (period_end is None or usage.timestamp <= period_end)
        ]
        
        filtered_costs = [
            cost
            for cost in self._cost_records
            if (period_start is None or cost.timestamp >= period_start)
            and (period_end is None or cost.timestamp <= period_end)
        ]
        
        # Calculate metrics for period
        total_tokens = sum(usage.total_tokens for usage in filtered_usages)
        total_cost = sum(cost.total_cost for cost in filtered_costs)
        total_requests = len(filtered_usages)
        
        cache_hits = sum(1 for usage in filtered_usages if usage.cached_tokens > 0)
        cache_misses = total_requests - cache_hits
        
        return {
            "period_start": period_start,
            "period_end": period_end,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "total_requests": total_requests,
            "avg_cost_per_request": total_cost / total_requests if total_requests > 0 else 0.0,
            "avg_tokens_per_request": total_tokens / total_requests if total_requests > 0 else 0.0,
            "cache_hit_rate": cache_hits / total_requests if total_requests > 0 else 0.0,
        }
    
    def get_user_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get metrics for a specific user."""
        return self._metrics["by_user"].get(user_id, {
            "tokens": 0,
            "cost": 0.0,
            "requests": 0,
        })
    
    def get_recent_operations(
        self,
        limit: int = 100,
        user_id: Optional[str] = None,
    ) -> List[tuple[TokenUsage, CostRecord]]:
        """
        Get recent operations.
        
        Args:
            limit: Maximum number of operations to return
            user_id: Filter by user ID
        
        Returns:
            List of (TokenUsage, CostRecord) tuples
        """
        # Combine token usage and cost records
        operations = list(zip(self._token_usages, self._cost_records))
        
        # Filter by user if specified
        if user_id:
            operations = [
                (usage, cost)
                for usage, cost in operations
                if usage.user_id == user_id
            ]
        
        # Sort by timestamp (most recent first)
        operations.sort(key=lambda x: x[0].timestamp, reverse=True)
        
        return operations[:limit]
    
    async def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        self._token_usages.clear()
        self._cost_records.clear()
        self._metrics = {
            "total_tokens": 0,
            "total_cost": 0.0,
            "total_requests": 0,
            "by_user": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0}),
            "by_model": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0}),
            "by_operation": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0}),
            "cache_hits": 0,
            "cache_misses": 0,
        }
    
    async def _persistence_loop(self):
        """Background loop for persisting data."""
        while self._running:
            try:
                await asyncio.sleep(self.persistence_interval)
                await self._persist_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in persistence loop: {e}")
    
    async def _persist_data(self):
        """Persist data to database."""
        # TODO: Implement database persistence
        # This would save token_usages and cost_records to a database
        pass
    
    def export_data(
        self,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Export data for analysis.
        
        Args:
            period_start: Start of period
            period_end: End of period
        
        Returns:
            Dictionary with token usages and cost records
        """
        # Filter by period
        filtered_usages = [
            usage
            for usage in self._token_usages
            if (period_start is None or usage.timestamp >= period_start)
            and (period_end is None or usage.timestamp <= period_end)
        ]
        
        filtered_costs = [
            cost
            for cost in self._cost_records
            if (period_start is None or cost.timestamp >= period_start)
            and (period_end is None or cost.timestamp <= period_end)
        ]
        
        return {
            "period_start": period_start.isoformat() if period_start else None,
            "period_end": period_end.isoformat() if period_end else None,
            "token_usages": [usage.dict() for usage in filtered_usages],
            "cost_records": [cost.dict() for cost in filtered_costs],
            "summary": self.get_metrics(period_start, period_end),
        }


# Global cost tracker instance
_global_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = CostTracker()
    return _global_tracker


async def track_operation(
    model_type: ModelType,
    operation_type: OperationType,
    prompt_tokens: int,
    completion_tokens: int = 0,
    **kwargs,
) -> tuple[TokenUsage, CostRecord]:
    """
    Convenience function to track an operation.
    
    Args:
        model_type: Model used
        operation_type: Type of operation
        prompt_tokens: Input tokens
        completion_tokens: Output tokens
        **kwargs: Additional arguments for track_usage
    
    Returns:
        Tuple of (TokenUsage, CostRecord)
    """
    tracker = get_cost_tracker()
    return await tracker.track_usage(
        model_type=model_type,
        operation_type=operation_type,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        **kwargs,
    )
