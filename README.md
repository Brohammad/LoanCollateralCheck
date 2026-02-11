# AI Agent Workflow System with LangFlow Integration

> 📚 **New here?** Check [INDEX.md](INDEX.md) for a guide to all documentation files.  
> ⚡ **Quick start?** Run `./quickstart.sh` or see [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

A production-ready AI agent workflow system built with LangFlow, Google Gemini API, and intelligent routing. Features multi-agent orchestration with intent classification, RAG (Retrieval-Augmented Generation), conversation history tracking, and vector search capabilities.

## 🎯 Features

- **Intelligent Orchestrator**: Intent classification with confidence scoring
- **Multi-Agent Architecture**: Greeting, Planner, and Critique agents
- **RAG Pipeline**: Vector search + optional web and LinkedIn search
- **Conversation Persistence**: SQLite database with full history tracking
- **Search Caching**: Query result caching with configurable TTL
- **Vector Storage**: Support for Pinecone, ChromaDB, and in-memory stores
- **Real-time API**: FastAPI server with async support
- **LangFlow Ready**: Custom node definitions for visual workflow building

## 🏗️ Architecture

```
User Input
    ↓
Orchestrator (Intent Classification with Confidence)
    ↓
├─→ Greeting Agent (if greeting/casual, confidence ≥ threshold)
└─→ RAG Pipeline (for questions/commands/unclear)
    ↓
    [Parallel Searches with Caching]
    ├─→ Vector DB Search
    ├─→ Web Search (optional)
    └─→ LinkedIn Search (optional)
    ↓
    Context Aggregation
    ↓
    Planner Agent (generates response using Gemini)
    ↓
    Critique Agent (validates, max 2 iterations)
    ↓
    Save to Database (conversation + credit history)
    ↓
    Return Response
```

## 📋 Tech Stack

- **Python 3.11+**
- **LangFlow** - Visual workflow builder
- **Google Gemini API** - gemini-2.0-flash-exp model for generation
- **SQLite** - Conversation and credit history persistence
- **FastAPI** - REST API server
- **Pinecone/ChromaDB** - Vector storage (optional)
- **Async/Await** - High-performance async operations

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
cd /home/labuser/LoanCollateralCheck

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For Pinecone support (optional)
pip install pinecone-client

# For ChromaDB support (optional)
pip install chromadb
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

**Required Configuration:**
```bash
GOOGLE_API_KEY=your-google-api-key-here
```

**Optional Configuration:**
```bash
# Model settings
GENERATION_MODEL=gemini-2.0-flash-exp
EMBEDDING_MODEL=text-embedding-004
GENERATION_TEMPERATURE=0.7
CLASSIFICATION_TEMPERATURE=0.3
MAX_TOKENS=2048
SAFETY_SETTINGS=medium

# Vector stores
PINECONE_API_KEY=your-key
PINECONE_ENV=us-west1-gcp
PINECONE_INDEX=ai-agent-workflow

CHROMA_PERSIST_DIR=./chroma_db

# Orchestrator
CONFIDENCE_THRESHOLD=0.6
MAX_CRITIQUE_ITERATIONS=2

# Database
SQLITE_PATH=./data/credit_history.db
CACHE_TTL_SECONDS=3600
```

### 3. Run the Server

```bash
# Start FastAPI server
uvicorn app.main:app --reload

# Or run directly
python -m app.main
```

Server will start at `http://127.0.0.1:8000`

## 📡 API Usage

### Send a Message

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/handle" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "text": "What is machine learning?",
    "use_web": false,
    "use_linkedin": false
  }'
```

**Response:**
```json
{
  "agent": "planner",
  "response": {
    "role": "assistant",
    "text": "Machine learning is..."
  },
  "intent": "question",
  "confidence": 0.85,
  "conversation_id": 1,
  "rag": [...]
}
```

### Get Conversation History

```bash
curl "http://127.0.0.1:8000/api/v1/history/user-123?limit=10"
```

### Health Check

```bash
curl "http://127.0.0.1:8000/health"
```

## 🖥️ CLI Usage

```bash
# Chat with the agent
python -m app.cli chat user-123 "Hello, how are you?"

# With web search
python -m app.cli chat user-123 "Latest AI news" --web

# With LinkedIn search
python -m app.cli chat user-123 "Find AI engineers" --linkedin

# Get conversation history
python -m app.cli history user-123 --limit 20

# Cleanup expired cache
python -m app.cli cleanup-cache
```

## 🗄️ Database Schema

### Conversations Table
- `id`: Primary key
- `user_id`: User identifier
- `message`: User input
- `response`: Agent response
- `intent`: Classified intent (greeting, question, command, unclear)
- `confidence`: Confidence score (0.0-1.0)
- `agent_used`: Which agent handled the request
- `metadata`: Additional context (JSON)
- `timestamp`: Creation time

### Credit History Table
- `id`: Primary key
- `conversation_id`: Foreign key to conversations
- `context_snapshot`: RAG results and context (JSON)
- `metadata`: Additional metadata
- `created_at`: Creation time

### Search Cache Table
- `query_hash`: SHA256 hash of query (primary key)
- `query`: Original query text
- `results`: Cached results (JSON)
- `expiry`: Expiration timestamp
- `created_at`: Creation time

## 🤖 LangFlow Integration

### Option 1: Use as Custom Nodes

```bash
# Generate LangFlow node files
python scripts/langflow_integration.py
```

This creates:
- `langflow_nodes/orchestrator_node.py` - Full orchestrator
- `langflow_nodes/rag_node.py` - RAG pipeline
- `langflow_nodes/intent_node.py` - Intent classifier

Copy these to your LangFlow `custom_components` directory and restart LangFlow.

### Option 2: Call API from LangFlow

Use LangFlow's HTTP Request node to call:
```
POST http://127.0.0.1:8000/api/v1/handle
```

### Option 3: Import Python Modules

Import modules directly in LangFlow custom components:
```python
from app.orchestrator import Orchestrator
from app.gemini_client import get_gemini_client
```

## 📊 Vector Store Setup

### In-Memory (Default)
No setup required. Data persists only during runtime.

### Pinecone

```bash
pip install pinecone-client

# Set environment variables
export PINECONE_API_KEY=your-key
export PINECONE_ENV=us-west1-gcp
export PINECONE_INDEX=ai-agent-workflow
```

### ChromaDB

```bash
pip install chromadb

# Set environment variable
export CHROMA_PERSIST_DIR=./chroma_db
```

### Ingest Documents

```bash
# Ingest documents into vector store
python scripts/ingest_documents.py --source ./docs --store pinecone
python scripts/ingest_documents.py --source ./docs --store chroma
python scripts/ingest_documents.py --source ./docs --store memory
```

## 🧪 Testing

```bash
# Run unit tests
PYTHONPATH=/home/labuser/LoanCollateralCheck python tests/test_orchestrator.py

# Or with pytest (if installed)
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## 🔧 Configuration Details

### Intent Classification
The orchestrator classifies user input into:
- **greeting**: Casual conversation (e.g., "hello", "hi")
- **question**: Information requests (e.g., "what is...", "how to...")
- **command**: Action requests (e.g., "create", "build", "run")
- **unclear**: Ambiguous or unrecognized intent

### Confidence Thresholding
- Default threshold: `0.6`
- If confidence < threshold, a disclaimer is appended to the response
- Greeting agent is only used if intent="greeting" AND confidence ≥ threshold

### Critique Loop
- Max iterations: `2` (configurable via `MAX_CRITIQUE_ITERATIONS`)
- Validates responses for quality and completeness
- Iteratively improves responses until approved or max iterations reached

### Caching Strategy
- Query results cached for `3600` seconds (1 hour) by default
- Uses SHA256 hash of query as cache key
- Automatic cleanup of expired entries

## 📁 Project Structure

```
LoanCollateralCheck/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI server
│   ├── orchestrator.py          # Main orchestrator with intent routing
│   ├── gemini_client.py         # Gemini API wrapper
│   ├── database.py              # SQLite manager
│   ├── config.py                # Configuration management
│   ├── rag.py                   # RAG pipeline
│   ├── vector_store.py          # Vector store adapters
│   ├── credit_history.py        # Legacy history manager
│   ├── cli.py                   # CLI interface
│   └── agents/
│       ├── greeting.py          # Greeting agent
│       ├── planner.py           # Planner agent
│       └── critique.py          # Critique agent
├── scripts/
│   ├── ingest_documents.py      # Document ingestion utility
│   └── langflow_integration.py  # LangFlow node generator
├── tests/
│   └── test_orchestrator.py     # Unit tests
├── data/                         # SQLite database (auto-created)
├── requirements.txt
├── .env.example
└── README.md
```

## 🔐 Security Considerations

1. **API Keys**: Never commit `.env` file. Use environment variables in production.
2. **Input Validation**: User inputs are sanitized before processing.
3. **Safety Settings**: Gemini API configured with medium safety settings.
4. **Rate Limiting**: Consider adding rate limiting for production deployments.

## 🚧 Next Steps & Enhancements

- [ ] Add authentication/authorization for API endpoints
- [ ] Implement rate limiting and request throttling
- [ ] Add monitoring and logging (Prometheus, Grafana)
- [ ] Implement real web scraping for web search
- [ ] Add LinkedIn API integration (observing ToS)
- [ ] Create comprehensive LangFlow workflow templates
- [ ] Add support for more LLM providers (OpenAI, Anthropic, etc.)
- [ ] Implement streaming responses for real-time UX
- [ ] Add unit tests for all agents
- [ ] Set up CI/CD pipeline
- [ ] Docker containerization
- [ ] Kubernetes deployment manifests

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 💬 Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/Brohammad/LoanCollateralCheck/issues)
- Documentation: This README

---

**Built with ❤️ using LangFlow, Google Gemini, and FastAPI**
