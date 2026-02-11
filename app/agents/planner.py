"""Planner Agent: generates detailed responses using the GeminiClient.

Receives aggregated context and user message, produces a response string.
"""
from typing import List, Dict, Any

class PlannerAgent:
    def __init__(self, gemini_client):
        self.client = gemini_client

    def plan(self, user_message: str, context_items: List[Dict[str, Any]] | None = None) -> str:
        # Summarize context into a prompt
        ctx = "\n".join([str(c.get("metadata") or c) for c in (context_items or [])][:5])
        prompt = f"You are a helpful assistant. Context:\n{ctx}\nUser: {user_message}\nAnswer concisely and cite sources where applicable."
        # call Gemini client
        try:
            out = self.client.generate(prompt)
        except Exception as e:
            # fallback: simple deterministic reply
            out = f"[planner-fallback] I would respond to '{user_message[:80]}' given the context."
        return out
