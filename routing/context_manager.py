"""
Context Manager

Manages session context and conversation history for intent routing.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import uuid

from routing.models import Intent, IntentContext

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages session contexts and conversation history
    
    Features:
    - Session creation and retrieval
    - Conversation history tracking
    - Context data management
    - User preferences storage
    - Topic tracking
    - Session expiration
    """
    
    def __init__(self, session_timeout_minutes: int = 30):
        """
        Initialize context manager
        
        Args:
            session_timeout_minutes: Session expiration timeout
        """
        self.contexts: Dict[str, IntentContext] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
    
    def create_session(
        self,
        user_id: str,
        language: str = "en",
        preferences: Optional[Dict] = None
    ) -> IntentContext:
        """
        Create a new session context
        
        Args:
            user_id: User identifier
            language: User's language
            preferences: User preferences
        
        Returns:
            New IntentContext
        """
        session_id = str(uuid.uuid4())
        
        context = IntentContext(
            session_id=session_id,
            user_id=user_id,
            language=language,
            user_preferences=preferences or {}
        )
        
        self.contexts[session_id] = context
        logger.info(f"Created session: {session_id} for user: {user_id}")
        
        return context
    
    def get_session(self, session_id: str) -> Optional[IntentContext]:
        """
        Get session context by ID
        
        Args:
            session_id: Session identifier
        
        Returns:
            IntentContext if found and not expired, None otherwise
        """
        context = self.contexts.get(session_id)
        
        if not context:
            return None
        
        # Check expiration
        if self._is_expired(context):
            logger.info(f"Session {session_id} expired")
            self.end_session(session_id)
            return None
        
        return context
    
    def get_or_create_session(
        self,
        session_id: Optional[str],
        user_id: str,
        language: str = "en",
        preferences: Optional[Dict] = None
    ) -> IntentContext:
        """
        Get existing session or create new one
        
        Args:
            session_id: Optional session identifier
            user_id: User identifier
            language: User's language
            preferences: User preferences
        
        Returns:
            IntentContext
        """
        if session_id:
            context = self.get_session(session_id)
            if context:
                return context
        
        # Create new session
        return self.create_session(user_id, language, preferences)
    
    def update_session(
        self,
        session_id: str,
        intent: Optional[Intent] = None,
        context_data: Optional[Dict] = None,
        preferences: Optional[Dict] = None,
        topic: Optional[str] = None
    ):
        """
        Update session context
        
        Args:
            session_id: Session identifier
            intent: Intent to add to history
            context_data: Context data to update
            preferences: User preferences to update
            topic: Current topic to set
        """
        context = self.get_session(session_id)
        if not context:
            logger.warning(f"Session {session_id} not found")
            return
        
        # Add intent to history
        if intent:
            context.add_intent(intent)
        
        # Update context data
        if context_data:
            context.context_data.update(context_data)
        
        # Update preferences
        if preferences:
            context.user_preferences.update(preferences)
        
        # Update topic
        if topic:
            context.current_topic = topic
        
        # Update last interaction time
        context.last_interaction = datetime.utcnow()
        context.interaction_count += 1
        
        logger.debug(f"Updated session: {session_id}")
    
    def end_session(self, session_id: str):
        """
        End a session
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.contexts:
            del self.contexts[session_id]
            logger.info(f"Ended session: {session_id}")
    
    def get_conversation_history(
        self,
        session_id: str,
        n: Optional[int] = None
    ) -> List[Intent]:
        """
        Get conversation history for session
        
        Args:
            session_id: Session identifier
            n: Number of recent intents to return (None for all)
        
        Returns:
            List of intents
        """
        context = self.get_session(session_id)
        if not context:
            return []
        
        if n:
            return context.get_recent_intents(n)
        
        return context.conversation_history
    
    def get_context_data(
        self,
        session_id: str,
        key: Optional[str] = None
    ) -> Optional[any]:
        """
        Get context data for session
        
        Args:
            session_id: Session identifier
            key: Specific key to retrieve (None for all)
        
        Returns:
            Context data value or dict
        """
        context = self.get_session(session_id)
        if not context:
            return None
        
        if key:
            return context.context_data.get(key)
        
        return context.context_data
    
    def set_context_data(
        self,
        session_id: str,
        key: str,
        value: any
    ):
        """
        Set context data for session
        
        Args:
            session_id: Session identifier
            key: Data key
            value: Data value
        """
        context = self.get_session(session_id)
        if context:
            context.context_data[key] = value
            context.last_interaction = datetime.utcnow()
    
    def get_user_preference(
        self,
        session_id: str,
        key: Optional[str] = None
    ) -> Optional[any]:
        """
        Get user preference for session
        
        Args:
            session_id: Session identifier
            key: Specific preference key (None for all)
        
        Returns:
            Preference value or dict
        """
        context = self.get_session(session_id)
        if not context:
            return None
        
        if key:
            return context.user_preferences.get(key)
        
        return context.user_preferences
    
    def set_user_preference(
        self,
        session_id: str,
        key: str,
        value: any
    ):
        """
        Set user preference for session
        
        Args:
            session_id: Session identifier
            key: Preference key
            value: Preference value
        """
        context = self.get_session(session_id)
        if context:
            context.user_preferences[key] = value
            context.last_interaction = datetime.utcnow()
    
    def get_current_topic(self, session_id: str) -> Optional[str]:
        """Get current topic for session"""
        context = self.get_session(session_id)
        return context.current_topic if context else None
    
    def set_current_topic(self, session_id: str, topic: str):
        """Set current topic for session"""
        context = self.get_session(session_id)
        if context:
            context.current_topic = topic
            context.last_interaction = datetime.utcnow()
    
    def clear_history(self, session_id: str):
        """Clear conversation history for session"""
        context = self.get_session(session_id)
        if context:
            context.conversation_history = []
            logger.info(f"Cleared history for session: {session_id}")
    
    def _is_expired(self, context: IntentContext) -> bool:
        """Check if session is expired"""
        age = datetime.utcnow() - context.last_interaction
        return age > self.session_timeout
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        expired = [
            session_id for session_id, context in self.contexts.items()
            if self._is_expired(context)
        ]
        
        for session_id in expired:
            self.end_session(session_id)
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.contexts.keys())
    
    def get_session_count(self) -> int:
        """Get count of active sessions"""
        return len(self.contexts)
    
    def get_user_sessions(self, user_id: str) -> List[IntentContext]:
        """Get all active sessions for a user"""
        return [
            context for context in self.contexts.values()
            if context.user_id == user_id
        ]
    
    def get_statistics(self) -> Dict[str, any]:
        """Get context manager statistics"""
        total_sessions = len(self.contexts)
        total_interactions = sum(c.interaction_count for c in self.contexts.values())
        
        # Average session age
        if total_sessions > 0:
            avg_age_seconds = sum(
                (datetime.utcnow() - c.created_at).total_seconds()
                for c in self.contexts.values()
            ) / total_sessions
        else:
            avg_age_seconds = 0
        
        # Sessions by language
        by_language = {}
        for context in self.contexts.values():
            lang = context.language
            by_language[lang] = by_language.get(lang, 0) + 1
        
        return {
            "total_sessions": total_sessions,
            "total_interactions": total_interactions,
            "avg_interactions_per_session": total_interactions / total_sessions if total_sessions > 0 else 0,
            "avg_session_age_minutes": avg_age_seconds / 60,
            "sessions_by_language": by_language,
            "session_timeout_minutes": self.session_timeout.total_seconds() / 60,
        }
