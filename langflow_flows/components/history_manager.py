"""
LangFlow Custom Component: History Manager
Manages conversation context and history from SQLite
"""

from typing import List, Dict, Optional
from langflow.custom import Component
from langflow.io import MessageTextInput, Output, StrInput, IntInput
from langflow.schema import Data
import logging

logger = logging.getLogger(__name__)


class HistoryManagerComponent(Component):
    """
    Custom LangFlow component for history management.
    
    Retrieves conversation history from SQLite database,
    manages context, and provides summarization.
    """
    
    display_name = "History Manager"
    description = "Manages conversation history and context from SQLite"
    icon = "database"
    
    inputs = [
        StrInput(
            name="session_id",
            display_name="Session ID",
            info="Unique session identifier",
            required=True
        ),
        StrInput(
            name="db_path",
            display_name="Database Path",
            info="Path to SQLite database",
            required=True
        ),
        IntInput(
            name="history_limit",
            display_name="History Limit",
            info="Number of recent interactions to retrieve",
            value=5,
            advanced=True
        ),
        IntInput(
            name="max_tokens",
            display_name="Max Tokens",
            info="Maximum tokens for history context",
            value=2000,
            advanced=True
        ),
        StrInput(
            name="gemini_api_key",
            display_name="Gemini API Key",
            info="API key for summarization (optional)",
            password=True,
            advanced=True
        ),
        MessageTextInput(
            name="current_message",
            display_name="Current Message",
            info="Current user message to add to history",
            required=False
        ),
        MessageTextInput(
            name="current_response",
            display_name="Current Response",
            info="Current agent response to store",
            required=False
        )
    ]
    
    outputs = [
        Output(
            name="history_context",
            display_name="History Context",
            method="get_history_context"
        ),
        Output(
            name="history_summary",
            display_name="History Summary",
            method="get_history_summary"
        ),
        Output(
            name="history_data",
            display_name="History Data",
            method="get_history_data"
        )
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._context = ""
        self._summary = ""
        self._history_items = []
    
    def get_history_context(self) -> str:
        """Main output: formatted history context."""
        try:
            from database.db_manager import DatabaseManager
            
            # Initialize database
            db = DatabaseManager(self.db_path)
            
            # Store current interaction if provided
            if self.current_message and self.current_response:
                db.add_conversation(
                    session_id=self.session_id,
                    user_message=self.current_message,
                    agent_response=self.current_response
                )
            
            # Update session activity
            db.update_session_activity(self.session_id)
            
            # Get conversation context
            self._context = db.get_conversation_context(
                session_id=self.session_id,
                max_tokens=self.max_tokens
            )
            
            # Get recent conversations for metadata
            self._history_items = db.get_recent_conversations(
                session_id=self.session_id,
                limit=self.history_limit
            )
            
            db.close()
            
            logger.info(
                f"Retrieved history: {len(self._history_items)} items, "
                f"{len(self._context)} chars"
            )
            
            return self._context
            
        except Exception as e:
            logger.error(f"History retrieval error: {e}")
            self._context = ""
            return ""
    
    def get_history_summary(self) -> str:
        """Output: summarized history (if requested)."""
        if not self._context or not self.gemini_api_key:
            return ""
        
        try:
            # Only summarize if context is too long
            if len(self._context) < self.max_tokens * 3:
                return ""
            
            import asyncio
            from app.gemini_enhanced import GeminiClient
            
            async def summarize():
                client = GeminiClient(
                    api_key=self.gemini_api_key,
                    enable_cache=False
                )
                
                prompt = f"""Summarize the following conversation history concisely, focusing on key points and context:

{self._context}

Provide a brief summary (2-3 sentences) highlighting the main topics and any important facts or decisions."""
                
                response = await client.generate_async(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=200
                )
                
                return response.text
            
            self._summary = asyncio.run(summarize())
            logger.info(f"Generated history summary: {len(self._summary)} chars")
            
            return self._summary
            
        except Exception as e:
            logger.error(f"History summarization error: {e}")
            return ""
    
    def get_history_data(self) -> Data:
        """Output: complete history metadata."""
        return Data(
            data={
                "session_id": self.session_id,
                "num_items": len(self._history_items),
                "context_length": len(self._context),
                "summary_length": len(self._summary),
                "history_items": [
                    {
                        "user_message": item["user_message"][:100],
                        "agent_response": item["agent_response"][:100],
                        "created_at": item["created_at"]
                    }
                    for item in self._history_items[:3]  # Include first 3 items
                ]
            }
        )
    
    def store_context(
        self,
        context_type: str,
        context_key: str,
        context_value: str,
        relevance_score: float = 1.0
    ) -> bool:
        """Store additional context information."""
        try:
            from database.db_manager import DatabaseManager
            
            db = DatabaseManager(self.db_path)
            db.store_context(
                session_id=self.session_id,
                context_type=context_type,
                context_key=context_key,
                context_value=context_value,
                relevance_score=relevance_score
            )
            db.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Context storage error: {e}")
            return False
    
    def get_stored_context(
        self,
        context_type: Optional[str] = None
    ) -> List[Dict]:
        """Retrieve stored context."""
        try:
            from database.db_manager import DatabaseManager
            
            db = DatabaseManager(self.db_path)
            contexts = db.get_context(
                session_id=self.session_id,
                context_type=context_type
            )
            db.close()
            
            return contexts
            
        except Exception as e:
            logger.error(f"Context retrieval error: {e}")
            return []
