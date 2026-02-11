"""LangFlow integration guide and custom node definitions.

This module provides templates for creating custom LangFlow nodes
that integrate with the AI Agent Workflow.
"""

# Custom LangFlow Node Template for Orchestrator
ORCHESTRATOR_NODE = """
from langflow import CustomComponent
from typing import Optional
import asyncio

class OrchestratorNode(CustomComponent):
    display_name = "AI Agent Orchestrator"
    description = "Routes messages through intent classification to appropriate agents"
    
    def build_config(self):
        return {
            "user_id": {"display_name": "User ID"},
            "message": {"display_name": "User Message"},
            "use_web": {"display_name": "Enable Web Search", "default": False},
            "use_linkedin": {"display_name": "Enable LinkedIn Search", "default": False},
            "confidence_threshold": {"display_name": "Confidence Threshold", "default": 0.6},
        }
    
    def build(
        self,
        user_id: str,
        message: str,
        use_web: bool = False,
        use_linkedin: bool = False,
        confidence_threshold: float = 0.6,
    ) -> str:
        from app.orchestrator import Orchestrator
        
        orch = Orchestrator(confidence_threshold=confidence_threshold)
        result = asyncio.run(orch.handle(user_id, message, use_web, use_linkedin))
        
        return result.get("response", {}).get("text", "")
"""

# RAG Pipeline Node
RAG_NODE = """
from langflow import CustomComponent
from typing import List, Dict, Any
import asyncio

class RAGNode(CustomComponent):
    display_name = "RAG Pipeline"
    description = "Retrieval-Augmented Generation with vector, web, and LinkedIn search"
    
    def build_config(self):
        return {
            "query": {"display_name": "Search Query"},
            "top_k": {"display_name": "Top K Results", "default": 5},
            "use_web": {"display_name": "Enable Web Search", "default": False},
            "use_linkedin": {"display_name": "Enable LinkedIn Search", "default": False},
        }
    
    def build(
        self,
        query: str,
        top_k: int = 5,
        use_web: bool = False,
        use_linkedin: bool = False,
    ) -> List[Dict[str, Any]]:
        from app.rag import run_rag
        from app.vector_store import InMemoryVectorStore
        from app.gemini_client import get_gemini_client
        
        vector_store = InMemoryVectorStore()
        client = get_gemini_client()
        
        results = asyncio.run(
            run_rag(query, vector_store, client.embed, top_k, use_web, use_linkedin)
        )
        
        return results
"""

# Intent Classification Node
INTENT_NODE = """
from langflow import CustomComponent
from typing import Dict, Any

class IntentClassifierNode(CustomComponent):
    display_name = "Intent Classifier"
    description = "Classifies user intent with confidence scoring"
    
    def build_config(self):
        return {
            "text": {"display_name": "Input Text"},
            "intents": {"display_name": "Intent Categories", "default": "greeting,question,command,unclear"},
        }
    
    def build(self, text: str, intents: str = "greeting,question,command,unclear") -> Dict[str, Any]:
        from app.gemini_client import get_gemini_client
        
        client = get_gemini_client()
        intent_list = [i.strip() for i in intents.split(",")]
        
        result = client.classify_intent(text, intent_list)
        
        return result
"""


def export_langflow_nodes():
    """Export custom nodes to files for LangFlow import."""
    import os

    output_dir = "langflow_nodes"
    os.makedirs(output_dir, exist_ok=True)

    nodes = {
        "orchestrator_node.py": ORCHESTRATOR_NODE,
        "rag_node.py": RAG_NODE,
        "intent_node.py": INTENT_NODE,
    }

    for filename, content in nodes.items():
        with open(os.path.join(output_dir, filename), "w") as f:
            f.write(content.strip())

    print(f"Exported {len(nodes)} LangFlow custom nodes to {output_dir}/")
    print("\nTo use in LangFlow:")
    print("1. Copy the files to your LangFlow custom_components directory")
    print("2. Restart LangFlow")
    print("3. The nodes will appear in the component sidebar")


if __name__ == "__main__":
    export_langflow_nodes()
