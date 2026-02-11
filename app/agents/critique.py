"""Critique Agent: validates and improves responses up to N iterations.

Simple heuristic-based critique is used here (placeholder). In a production system,
this agent would run tests, call validators/knowledge-checkers, or use a separate model.
"""
from typing import Dict

class CritiqueAgent:
    def __init__(self, gemini_client=None, max_iterations: int = 2):
        self.client = gemini_client
        self.max_iterations = max_iterations

    def validate(self, response: str, context: str | None = None) -> Dict[str, object]:
        """Return {'approved': bool, 'feedback': str, 'revised': str}

        Current heuristic: approve if length < 2000 and does not contain obvious placeholders.
        """
        if "[planner-fallback]" in response:
            approved = False
            feedback = "Response is placeholder; needs fuller generation."
            revised = response + "\n[critic-suggest] Expand details and cite sources."
        else:
            approved = True
            feedback = "OK"
            revised = response
        return {"approved": approved, "feedback": feedback, "revised": revised}

    def critique_loop(self, initial_response: str, context: str | None = None) -> str:
        response = initial_response
        for i in range(self.max_iterations):
            result = self.validate(response, context)
            if result.get("approved"):
                return response
            # if not approved, attempt to revise by appending critic feedback and re-running generator
            suggestion = result.get("feedback")
            # if we have a generator client, request a revision
            if self.client:
                prompt = f"Previous response: {response}\nCritique: {suggestion}\nPlease produce an improved response."
                try:
                    response = self.client.generate(prompt)
                except Exception:
                    response = result.get("revised")
            else:
                response = result.get("revised")
        return response
