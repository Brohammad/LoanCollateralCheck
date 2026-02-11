"""Simple FastAPI server exposing the orchestrator endpoint.

Endpoint: POST /api/v1/handle
Body: {"user_id": "id", "text": "...", "use_web": bool, "use_linkedin": bool}

Endpoint: GET /api/v1/history/{user_id}
Returns conversation history for a user
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

from .orchestrator import Orchestrator
from .database import DatabaseManager
from .vector_store import InMemoryVectorStore
from .gemini_client import get_gemini_client

app = FastAPI(title="AI Agent Workflow", version="1.0.0")


class HandleRequest(BaseModel):
    user_id: str
    text: str
    use_web: bool = False
    use_linkedin: bool = False


# single orchestrator instance
orch = Orchestrator()


@app.get("/")
async def root():
    return {
        "message": "AI Agent Workflow API",
        "endpoints": {
            "POST /api/v1/handle": "Process user input",
            "GET /api/v1/history/{user_id}": "Get conversation history",
            "GET /health": "Health check",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ai-agent-workflow"}


@app.post("/api/v1/handle")
async def handle(req: HandleRequest):
    try:
        out = await orch.handle(req.user_id, req.text, use_web=req.use_web, use_linkedin=req.use_linkedin)
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/history/{user_id}")
async def get_history(user_id: str, limit: int = 10):
    try:
        history = await orch.get_conversation_history(user_id, limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )

