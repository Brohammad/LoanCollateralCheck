"""Orchestrator: intent classification with confidence scoring and routing to agents and RAG pipeline."""
from typing import Any, Dict
import asyncio

from .agents.greeting import GreetingAgent
from .agents.planner import PlannerAgent
from .agents.critique import CritiqueAgent
from .database import DatabaseManager
from .rag import run_rag
from .gemini_client import get_gemini_client
from .vector_store import InMemoryVectorStore


class Orchestrator:
    """Main orchestrator with intelligent intent classification and routing.

    Features:
    - Intent classification with confidence scoring
    - Routes to: greeting, question, command, unclear
    - Fallback handling for edge cases
    - Conversation context tracking
    """

    def __init__(
        self,
        vector_store=None,
        database: DatabaseManager | None = None,
        gemini_client=None,
        confidence_threshold: float = 0.6,
    ):
        self.greeting = GreetingAgent()
        self.gemini = gemini_client or get_gemini_client()
        self.planner = PlannerAgent(self.gemini)
        self.critic = CritiqueAgent(self.gemini)
        self.db = database or DatabaseManager()
        self.vector_store = vector_store or InMemoryVectorStore()
        self.confidence_threshold = confidence_threshold

    async def handle(
        self, user_id: str, text: str, use_web: bool = False, use_linkedin: bool = False
    ) -> Dict[str, Any]:
        """Main handler with intent classification and routing.

        Args:
            user_id: User identifier
            text: User input text
            use_web: Enable web search in RAG
            use_linkedin: Enable LinkedIn search in RAG

        Returns:
            Dict containing agent, response, intent, confidence, and optionally RAG results
        """
        # Step 1: Intent classification with confidence scoring
        classification = self.gemini.classify_intent(text)
        intent = classification.get("intent", "unclear")
        confidence = classification.get("confidence", 0.5)

        # Step 2: Route based on intent and confidence
        if intent == "greeting" and confidence >= self.confidence_threshold:
            # Simple greeting - no need for RAG
            reply = self.greeting.respond(text, user_id)

            # Save to database
            conv_id = self.db.add_conversation(
                user_id=user_id,
                message=text,
                response=reply.get("text", ""),
                intent=intent,
                confidence=confidence,
                agent_used="greeting",
                metadata={"use_web": use_web, "use_linkedin": use_linkedin},
            )

            return {
                "agent": "greeting",
                "response": reply,
                "intent": intent,
                "confidence": confidence,
                "conversation_id": conv_id,
            }

        # Step 3: For questions, commands, or unclear intents -> use RAG pipeline
        # Check cache first
        cached_results = self.db.get_cache(text)
        if cached_results:
            aggregated = cached_results
        else:
            # Run RAG to gather context
            aggregated = await run_rag(
                text,
                self.vector_store,
                self.gemini.embed,
                top_k=5,
                use_web=use_web,
                use_linkedin=use_linkedin,
            )
            # Cache for 1 hour
            self.db.set_cache(text, aggregated, ttl_seconds=3600)

        # Step 4: Planner generates a response
        planned = self.planner.plan(text, aggregated)

        # Step 5: Critique loop (max 2 iterations)
        final = self.critic.critique_loop(planned, context=str(aggregated[:3]))

        # Step 6: Persist to database
        conv_id = self.db.add_conversation(
            user_id=user_id,
            message=text,
            response=final,
            intent=intent,
            confidence=confidence,
            agent_used="planner",
            metadata={
                "use_web": use_web,
                "use_linkedin": use_linkedin,
                "rag_results_count": len(aggregated),
            },
        )

        # Add credit history snapshot
        self.db.add_credit_history(
            conversation_id=conv_id,
            context_snapshot={
                "rag_results": aggregated[:3],  # Store top 3 for reference
                "intent": intent,
                "confidence": confidence,
            },
        )

        # Step 7: Handle low-confidence cases
        if confidence < self.confidence_threshold:
            final = f"{final}\n\n(Note: I'm {confidence:.0%} confident in my understanding. Please clarify if needed.)"

        return {
            "agent": "planner",
            "response": {"role": "assistant", "text": final},
            "intent": intent,
            "confidence": confidence,
            "rag": aggregated,
            "conversation_id": conv_id,
        }

    async def get_conversation_history(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Retrieve recent conversation history for a user."""
        conversations = self.db.get_recent_conversations(user_id, limit)
        return {"user_id": user_id, "conversations": conversations}


# Synchronous helper for CLI/tests
def handle_sync(user_id: str, text: str):
    import asyncio

    orch = Orchestrator()
    return asyncio.run(orch.handle(user_id, text))

