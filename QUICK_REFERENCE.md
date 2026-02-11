# 🚀 Quick Reference Card

## 📦 Installation (3 commands)
```bash
cp .env.example .env  # Add your GOOGLE_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 🔑 Required Environment Variables
```bash
GOOGLE_API_KEY=your-api-key-here  # Get at: https://ai.google.dev/
```

## 🌐 API Endpoints

### Send Message
```bash
curl -X POST http://127.0.0.1:8000/api/v1/handle \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-1", "text": "Hello!"}'
```

### Get History
```bash
curl http://127.0.0.1:8000/api/v1/history/user-1?limit=10
```

### Health Check
```bash
curl http://127.0.0.1:8000/health
```

## 💻 CLI Commands
```bash
# Chat
python -m app.cli chat user-1 "Hello!"

# History
python -m app.cli history user-1 --limit 10

# Cleanup cache
python -m app.cli cleanup-cache
```

## 🧪 Testing
```bash
PYTHONPATH=$PWD python tests/test_orchestrator.py
```

## 🐳 Docker
```bash
docker-compose up --build
```

## 📊 System Components

| Component | Purpose | File |
|-----------|---------|------|
| Orchestrator | Routes & classifies | `app/orchestrator.py` |
| Greeting Agent | Casual chat | `app/agents/greeting.py` |
| Planner Agent | Detailed responses | `app/agents/planner.py` |
| Critique Agent | Validates output | `app/agents/critique.py` |
| RAG Pipeline | Search & retrieve | `app/rag.py` |
| Gemini Client | LLM interface | `app/gemini_client.py` |
| Database | Persistence | `app/database.py` |
| Vector Store | Embeddings | `app/vector_store.py` |

## 🎯 Intent Types
- **greeting**: "Hi", "Hello", "Hey"
- **question**: "What", "How", "Why", "?"
- **command**: "Do", "Create", "Build", "Run"
- **unclear**: Ambiguous input

## ⚙️ Configuration Defaults
| Setting | Default | Description |
|---------|---------|-------------|
| `GENERATION_MODEL` | gemini-2.0-flash-exp | Generation model |
| `EMBEDDING_MODEL` | text-embedding-004 | Embedding model |
| `GENERATION_TEMPERATURE` | 0.7 | Generation randomness |
| `CLASSIFICATION_TEMPERATURE` | 0.3 | Classification precision |
| `MAX_TOKENS` | 2048 | Max response length |
| `CONFIDENCE_THRESHOLD` | 0.6 | Intent confidence min |
| `MAX_CRITIQUE_ITERATIONS` | 2 | Critique loop limit |
| `CACHE_TTL_SECONDS` | 3600 | Cache expiry (1 hour) |

## 📁 Project Structure
```
LoanCollateralCheck/
├── app/                    # Core application
│   ├── agents/            # Agent implementations
│   ├── main.py            # FastAPI server
│   ├── orchestrator.py    # Main routing
│   ├── gemini_client.py   # Gemini API
│   ├── database.py        # SQLite manager
│   └── ...
├── scripts/               # Utilities
│   ├── ingest_documents.py
│   └── langflow_integration.py
├── tests/                 # Unit tests
├── requirements.txt       # Dependencies
├── Dockerfile            # Container image
└── docker-compose.yml    # Docker orchestration
```

## 🔐 Security Checklist
- [ ] Set `GOOGLE_API_KEY` in `.env`
- [ ] Never commit `.env` file
- [ ] Use environment variables in production
- [ ] Review safety settings (medium by default)
- [ ] Implement rate limiting (see NEXT_STEPS.md)
- [ ] Add authentication (see NEXT_STEPS.md)

## 📚 Documentation Files
| File | Contents |
|------|----------|
| `README.md` | Full documentation |
| `ARCHITECTURE.md` | System diagram |
| `EXAMPLES.md` | API examples |
| `CHECKLIST.md` | Implementation status |
| `NEXT_STEPS.md` | Future enhancements |
| `IMPLEMENTATION_SUMMARY.md` | What was built |

## 🎨 LangFlow Integration
```bash
# Generate custom nodes
python scripts/langflow_integration.py

# Files created in langflow_nodes/:
# - orchestrator_node.py
# - rag_node.py
# - intent_node.py
```

## 📈 Monitoring Endpoints
| Endpoint | Status |
|----------|--------|
| `/health` | Service health |
| `/` | API info |
| `/docs` | Swagger UI (auto-generated) |

## 🚨 Common Issues & Fixes

### "Google API key not configured"
```bash
# Set in .env file
echo "GOOGLE_API_KEY=your-key" >> .env
```

### "Module not found: app"
```bash
# Set PYTHONPATH
export PYTHONPATH=$PWD
```

### "Port 8000 already in use"
```bash
# Change port in .env
echo "PORT=8001" >> .env
```

### Database locked
```bash
# Stop all servers, then:
rm data/credit_history.db
# Restart - DB will be recreated
```

## 🔗 Useful Links
- Google Gemini API: https://ai.google.dev/
- LangFlow Docs: https://docs.langflow.org/
- FastAPI Docs: https://fastapi.tiangolo.com/
- Pinecone: https://docs.pinecone.io/
- ChromaDB: https://docs.trychroma.com/

## 💡 Quick Tips
1. Tests work without API key (use mocks)
2. In-memory vector store works by default
3. Use `--web` or `--linkedin` flags for extended search
4. Cache reduces API calls (1-hour TTL)
5. Confidence < 0.6 adds disclaimer to response
6. Critique agent loops max 2 times
7. All database operations are indexed for speed

## ⚡ Performance Tips
- Set up Redis for distributed caching
- Use Pinecone/ChromaDB for production vector search
- Enable web/LinkedIn search only when needed
- Monitor API quota usage
- Scale horizontally with Docker Compose

## 📞 Support
- Issues: GitHub Issues
- Docs: This project's markdown files
- Examples: See `EXAMPLES.md`

---

**🎉 You're ready to build AI agent workflows!**

Start with: `./quickstart.sh`
