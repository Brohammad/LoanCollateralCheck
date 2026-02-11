"""Greeting Agent: handles casual conversation and small-talk routing."""
from typing import Dict

class GreetingAgent:
    GREETING_KEYWORDS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}

    def is_greeting(self, text: str) -> bool:
        txt = text.lower().strip()
        for kw in self.GREETING_KEYWORDS:
            if kw in txt:
                return True
        return False

    def respond(self, text: str, user_id: str | None = None) -> Dict[str, str]:
        # Very small deterministic reply for scaffolding
        return {"role": "assistant", "text": "Hello! How can I help you today?"}
