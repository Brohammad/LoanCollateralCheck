"""
Intent History Tracker

Tracks and analyzes intent history for patterns and insights.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from routing.models import Intent, IntentType, IntentConfidence

logger = logging.getLogger(__name__)


class IntentHistoryTracker:
    """
    Tracks and analyzes intent history
    
    Features:
    - Intent history storage
    - Pattern analysis
    - Frequency tracking
    - Confidence trends
    - User behavior insights
    - Time-based analytics
    """
    
    def __init__(self, max_history_size: int = 10000):
        """
        Initialize history tracker
        
        Args:
            max_history_size: Maximum number of intents to keep
        """
        self.max_history_size = max_history_size
        self.history: List[Intent] = []
        self.by_user: Dict[str, List[Intent]] = defaultdict(list)
        self.by_type: Dict[IntentType, List[Intent]] = defaultdict(list)
    
    def track(self, intent: Intent, user_id: Optional[str] = None):
        """
        Track an intent
        
        Args:
            intent: Intent to track
            user_id: Optional user identifier
        """
        # Add to main history
        self.history.append(intent)
        
        # Add to type index
        self.by_type[intent.intent_type].append(intent)
        
        # Add to user index if provided
        if user_id:
            self.by_user[user_id].append(intent)
        
        # Trim history if needed
        if len(self.history) > self.max_history_size:
            removed = self.history.pop(0)
            # Clean up indexes
            self.by_type[removed.intent_type].remove(removed)
            if user_id:
                self.by_user[user_id].remove(removed)
        
        logger.debug(f"Tracked intent: {intent.intent_type} (total: {len(self.history)})")
    
    def get_history(
        self,
        user_id: Optional[str] = None,
        intent_type: Optional[IntentType] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Intent]:
        """
        Get intent history with filters
        
        Args:
            user_id: Filter by user
            intent_type: Filter by intent type
            since: Filter by timestamp
            limit: Maximum number to return
        
        Returns:
            List of intents
        """
        # Start with appropriate base
        if user_id:
            intents = self.by_user.get(user_id, [])
        elif intent_type:
            intents = self.by_type.get(intent_type, [])
        else:
            intents = self.history
        
        # Apply filters
        if since:
            intents = [i for i in intents if i.timestamp >= since]
        
        if intent_type and not user_id:
            intents = [i for i in intents if i.intent_type == intent_type]
        
        # Apply limit
        if limit:
            intents = intents[-limit:]
        
        return intents
    
    def get_frequency(
        self,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[IntentType, int]:
        """
        Get intent frequency counts
        
        Args:
            user_id: Filter by user
            since: Filter by timestamp
        
        Returns:
            Dict mapping intent type to count
        """
        intents = self.get_history(user_id=user_id, since=since)
        
        frequency = defaultdict(int)
        for intent in intents:
            frequency[intent.intent_type] += 1
        
        return dict(frequency)
    
    def get_top_intents(
        self,
        n: int = 10,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[tuple]:
        """
        Get top N most frequent intents
        
        Args:
            n: Number of intents to return
            user_id: Filter by user
            since: Filter by timestamp
        
        Returns:
            List of (intent_type, count) tuples
        """
        frequency = self.get_frequency(user_id=user_id, since=since)
        
        sorted_intents = sorted(
            frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_intents[:n]
    
    def get_confidence_stats(
        self,
        intent_type: Optional[IntentType] = None,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Get confidence statistics
        
        Args:
            intent_type: Filter by intent type
            user_id: Filter by user
            since: Filter by timestamp
        
        Returns:
            Dict with avg, min, max confidence
        """
        intents = self.get_history(
            user_id=user_id,
            intent_type=intent_type,
            since=since
        )
        
        if not intents:
            return {"avg": 0.0, "min": 0.0, "max": 0.0}
        
        confidences = [i.confidence for i in intents]
        
        return {
            "avg": sum(confidences) / len(confidences),
            "min": min(confidences),
            "max": max(confidences),
            "count": len(intents),
        }
    
    def get_confidence_distribution(
        self,
        intent_type: Optional[IntentType] = None,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[IntentConfidence, int]:
        """
        Get confidence level distribution
        
        Args:
            intent_type: Filter by intent type
            user_id: Filter by user
            since: Filter by timestamp
        
        Returns:
            Dict mapping confidence level to count
        """
        intents = self.get_history(
            user_id=user_id,
            intent_type=intent_type,
            since=since
        )
        
        distribution = defaultdict(int)
        for intent in intents:
            distribution[intent.confidence_level] += 1
        
        return dict(distribution)
    
    def get_hourly_volume(
        self,
        hours: int = 24,
        user_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get intent volume by hour
        
        Args:
            hours: Number of hours to analyze
            user_id: Filter by user
        
        Returns:
            List of dicts with hour and count
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        intents = self.get_history(user_id=user_id, since=since)
        
        # Group by hour
        by_hour = defaultdict(int)
        for intent in intents:
            hour = intent.timestamp.replace(minute=0, second=0, microsecond=0)
            by_hour[hour] += 1
        
        # Sort by time
        sorted_hours = sorted(by_hour.items())
        
        return [
            {"hour": hour.isoformat(), "count": count}
            for hour, count in sorted_hours
        ]
    
    def get_sentiment_distribution(
        self,
        intent_type: Optional[IntentType] = None,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Get sentiment distribution
        
        Args:
            intent_type: Filter by intent type
            user_id: Filter by user
            since: Filter by timestamp
        
        Returns:
            Dict mapping sentiment to count
        """
        intents = self.get_history(
            user_id=user_id,
            intent_type=intent_type,
            since=since
        )
        
        distribution = defaultdict(int)
        for intent in intents:
            if intent.sentiment:
                distribution[intent.sentiment] += 1
        
        return dict(distribution)
    
    def get_user_patterns(self, user_id: str) -> Dict[str, any]:
        """
        Get behavior patterns for a user
        
        Args:
            user_id: User identifier
        
        Returns:
            Dict with pattern insights
        """
        intents = self.by_user.get(user_id, [])
        
        if not intents:
            return {"error": "No history for user"}
        
        # Most frequent intents
        top_intents = self.get_top_intents(n=5, user_id=user_id)
        
        # Average confidence
        avg_confidence = sum(i.confidence for i in intents) / len(intents)
        
        # Language preferences
        languages = defaultdict(int)
        for intent in intents:
            languages[intent.language] += 1
        most_common_language = max(languages.items(), key=lambda x: x[1])[0]
        
        # Time patterns
        hours = [i.timestamp.hour for i in intents]
        most_active_hour = max(set(hours), key=hours.count)
        
        # Recent activity
        recent_24h = len([
            i for i in intents
            if i.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ])
        
        return {
            "user_id": user_id,
            "total_intents": len(intents),
            "top_intents": [
                {"type": itype.value, "count": count}
                for itype, count in top_intents
            ],
            "avg_confidence": avg_confidence,
            "preferred_language": most_common_language,
            "most_active_hour": most_active_hour,
            "intents_last_24h": recent_24h,
        }
    
    def get_summary(self) -> Dict[str, any]:
        """
        Get overall tracker summary
        
        Returns:
            Dict with summary statistics
        """
        total_intents = len(self.history)
        unique_users = len(self.by_user)
        
        # Top intents
        top_intents = self.get_top_intents(n=10)
        
        # Confidence stats
        confidence_stats = self.get_confidence_stats()
        confidence_dist = self.get_confidence_distribution()
        
        # Sentiment
        sentiment_dist = self.get_sentiment_distribution()
        
        # Recent activity
        last_hour = len([
            i for i in self.history
            if i.timestamp >= datetime.utcnow() - timedelta(hours=1)
        ])
        
        last_24h = len([
            i for i in self.history
            if i.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ])
        
        return {
            "total_intents": total_intents,
            "unique_users": unique_users,
            "intents_last_hour": last_hour,
            "intents_last_24h": last_24h,
            "top_intents": [
                {"type": itype.value, "count": count}
                for itype, count in top_intents
            ],
            "confidence": confidence_stats,
            "confidence_distribution": {
                level.value: count
                for level, count in confidence_dist.items()
            },
            "sentiment_distribution": sentiment_dist,
        }
    
    def clear_user_history(self, user_id: str):
        """Clear history for a user"""
        if user_id in self.by_user:
            user_intents = self.by_user[user_id]
            
            # Remove from main history
            self.history = [i for i in self.history if i not in user_intents]
            
            # Remove from type index
            for intent in user_intents:
                self.by_type[intent.intent_type].remove(intent)
            
            # Clear user index
            del self.by_user[user_id]
            
            logger.info(f"Cleared history for user: {user_id}")
    
    def clear_all_history(self):
        """Clear all history"""
        self.history = []
        self.by_user = defaultdict(list)
        self.by_type = defaultdict(list)
        
        logger.info("Cleared all intent history")
