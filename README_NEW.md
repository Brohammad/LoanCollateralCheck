# AI Agent System with RAG and Planner-Critique Loop

A sophisticated AI agent system using Google's Gemini 2.0 Flash Experimental, implementing RAG (Retrieval-Augmented Generation) with vector search, planner-critique iterative refinement, and LangFlow integration.

## 🌟 Features

- **Intent Classification**: Automatically classifies user messages (greeting, question, command, etc.)
- **RAG Pipeline**: Vector similarity search + optional web search with intelligent merging
- **Planner-Critique Loop**: Iterative response refinement with quality evaluation
- **Conversation History**: SQLite-based context management with automatic pruning
- **Response Caching**: Multi-level caching for performance optimization
- **Token Management**: Automatic token counting and budget enforcement
- **LangFlow Integration**: Custom components for visual workflow design

## 📋 System Architecture

```
User Query
    ↓
Intent Classifier → [greeting/question/command]
    ↓
History Manager → Retrieve conversation context
    ↓
RAG Retriever → Vector Search + Web Search → Merged Context
    ↓
Planner-Critique Loop (max 2 iterations)
    ├─ Planner: Generate response using context
    ├─ Critique: Evaluate (accuracy/completeness/clarity)
    └─ Refine if score < 0.85
    ↓
Final Response → Store in History
```

## 🚀 Quick Start

### Option 1: Local Setup

```bash
# Clone and setup
git clone <repository>
cd LoanCollateralCheck
chmod +x setup.sh
./setup.sh

# Configure API keys
nano .env  # Add your GEMINI_API_KEY

# Activate environment
source venv/bin/activate

# Run LangFlow
langflow run --host 0.0.0.0 --port 7860

# Open browser
open http://localhost:7860
```

### Option 2: Docker

```bash
# Configure environment
cp .env.template .env
nano .env  # Add your API keys

# Build and run
docker-compose -f docker-compose.new.yml up --build

# Access LangFlow
open http://localhost:7860
```

## 📦 Installation

### Prerequisites

- Python 3.11+
- Google AI API key (for Gemini)
- Optional: SERP API key (for web search)

### Dependencies

```bash
pip install -r requirements.txt
```

Key packages:
- `google-generativeai`: Gemini API client
- `chromadb`: Vector database
- `langflow`: Visual workflow builder
- `aiohttp`: Async HTTP client
- `python-dotenv`: Environment management

## ⚙️ Configuration

All configuration is managed through environment variables (`.env` file):

### Required
```env
GEMINI_API_KEY=your_api_key_here
```

### Optional
```env
# Model Configuration
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_MAX_RETRIES=3
GEMINI_TIMEOUT_SECONDS=15

# RAG Configuration
RAG_TOP_K=5
RAG_MAX_TOKENS=4000
ENABLE_SEARCH_CACHE=true

# Planner-Critique
MAX_CRITIQUE_ITERATIONS=2
CRITIQUE_ACCEPTANCE_THRESHOLD=0.85

# Database
SQLITE_DB_PATH=./database/loan_collateral.db
CHROMADB_PATH=./data/chromadb

# Web Search (optional)
SERP_API_KEY=your_serp_key
ENABLE_WEB_SEARCH=false
```

## 🏗️ Project Structure

```
LoanCollateralCheck/
├── app/
│   ├── gemini_enhanced.py      # Gemini client with retry & caching
│   ├── planner_critique.py     # Iterative refinement orchestrator
│   └── orchestrator.py         # Main orchestrator
├── database/
│   ├── schema.sql              # Database schema
│   ├── db_manager.py           # Connection pooling & operations
│   └── init_db.py              # Initialization script
├── langflow_flows/
│   ├── components/
│   │   ├── intent_classifier.py    # Intent classification
│   │   ├── rag_retriever.py        # RAG pipeline
│   │   ├── response_validator.py   # Critique agent
│   │   └── history_manager.py      # History management
│   └── main_orchestrator.json      # LangFlow configuration
├── config/
│   └── config_loader.py        # Configuration management
├── tests/
│   └── test_orchestrator.py    # Unit tests
├── .env.template               # Environment template
├── requirements.txt            # Python dependencies
├── setup.sh                    # Setup script
├── Dockerfile.new              # Docker configuration
└── docker-compose.new.yml      # Docker Compose
```

## 🔧 Component Overview

### 1. Intent Classifier
Classifies user messages into intents using Gemini API.

```python
from langflow_flows.components.intent_classifier import IntentClassifierComponent

# Returns: intent (str) + confidence (float)
```

### 2. RAG Retriever
Performs parallel vector and web searches, merges results.

```python
from langflow_flows.components.rag_retriever import RAGRetrieverComponent

# Returns: context (str) + sources (list)
```

### 3. Response Validator (Critique)
Evaluates responses on accuracy, completeness, clarity.

```python
from langflow_flows.components.response_validator import ResponseValidatorComponent

# Returns: approved (bool) + feedback (str) + scores (dict)
```

### 4. History Manager
Manages conversation history and context from SQLite.

```python
from langflow_flows.components.history_manager import HistoryManagerComponent

# Returns: history_context (str) + summary (str)
```

### 5. Planner-Critique Orchestrator
Coordinates iterative refinement loop.

```python
from app.planner_critique import PlannerCritiqueOrchestrator

orchestrator = PlannerCritiqueOrchestrator(
    gemini_client=client,
    max_iterations=2,
    acceptance_threshold=0.85
)

result = await orchestrator.run(query=query, context=context)
```

## 📊 Database Schema

### Tables
- `user_sessions`: Session management
- `conversation_history`: User-agent interactions
- `credit_history`: Context storage with TTL
- `search_cache`: Cached search results
- `response_cache`: Cached API responses
- `critique_history`: Planner-critique iterations
- `api_call_logs`: API monitoring
- `performance_metrics`: Performance tracking

### Indexes
All tables have optimized indexes for query performance (<200ms target).

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov=database --cov-report=html

# Run specific test
pytest tests/test_orchestrator.py -v
```

## 📈 Performance Targets

- **End-to-end latency**: <8 seconds
- **Token budget**: <8000 tokens per request
- **Cache hit rate**: >60%
- **Database queries**: <200ms
- **Cost per request**: <$0.05

## 🔍 Monitoring

The system logs comprehensive metrics:

```python
# Get statistics
from config.config_loader import get_config
from database.db_manager import DatabaseManager

config = get_config()
db = DatabaseManager(config.db_path)

# Database stats
stats = db.get_database_stats()

# Performance metrics
metrics = db.get_metrics_summary("response_time_ms", hours=24)

# Gemini client stats
from app.gemini_enhanced import GeminiClient
client = GeminiClient(api_key=config.gemini_api_key)
print(client.get_statistics())
```

## 🚨 Error Handling

The system implements graceful degradation:

1. **Retry Logic**: Exponential backoff for API failures (max 3 attempts)
2. **Timeout Handling**: 15s timeout per LLM call
3. **Fallback Responses**: If all searches fail, uses conversation history
4. **Graceful Critique Failure**: Approves response if critique fails
5. **Structured Logging**: All errors logged with context

## 🔐 Security

- API keys stored in environment variables (never committed)
- Request size limits (10MB max)
- Rate limiting (60 requests/minute)
- SQL injection protection (parameterized queries)
- Connection pooling with timeouts

## 📝 Usage Examples

### Standalone Gemini Client

```python
import asyncio
from app.gemini_enhanced import GeminiClient

async def main():
    client = GeminiClient(
        api_key="your_key",
        enable_cache=True
    )
    
    response = await client.generate_async(
        prompt="What is loan collateral?",
        temperature=0.7
    )
    
    print(response.text)
    print(f"Tokens: {response.token_usage.total_tokens}")
    print(f"Cost: ${response.token_usage.estimated_cost:.4f}")

asyncio.run(main())
```

### Planner-Critique Loop

```python
import asyncio
from app.planner_critique import refine_response

async def main():
    response = await refine_response(
        query="Explain loan collateral requirements",
        context="<RAG retrieved context>",
        gemini_api_key="your_key",
        max_iterations=2,
        acceptance_threshold=0.85
    )
    
    print(response)

asyncio.run(main())
```

### Database Operations

```python
from database.db_manager import DatabaseManager

db = DatabaseManager("./database/loan_collateral.db")

# Create session
db.create_session(
    session_id="session_123",
    user_id="user_456"
)

# Add conversation
conv_id = db.add_conversation(
    session_id="session_123",
    user_message="What is collateral?",
    agent_response="Collateral is an asset...",
    intent="question",
    confidence=0.95
)

# Get recent conversations
history = db.get_recent_conversations(
    session_id="session_123",
    limit=5
)

db.close()
```

## 🐛 Troubleshooting

### API Key Issues
```bash
# Check if API key is loaded
python -c "from config.config_loader import get_config; print(get_config().gemini_api_key[:10])"
```

### Database Issues
```bash
# Reinitialize database
python database/init_db.py
```

### LangFlow Issues
```bash
# Clear cache and restart
rm -rf ~/.langflow
langflow run --host 0.0.0.0 --port 7860
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Google AI for Gemini 2.0 Flash Experimental
- LangFlow team for the visual workflow builder
- ChromaDB for vector database
- All contributors and testers

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check documentation in `/docs`
- Review examples in `/EXAMPLES.md`

---

**Version**: 1.0.0  
**Last Updated**: February 11, 2026
