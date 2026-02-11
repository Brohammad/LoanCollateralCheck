# Quick Start Guide - AI Agent System

## 🚀 5-Minute Setup

### Step 1: Clone and Setup
```bash
cd /home/labuser/LoanCollateralCheck
chmod +x setup.sh
./setup.sh
```

### Step 2: Configure API Key
```bash
nano .env
# Add your GEMINI_API_KEY
```

### Step 3: Activate Environment
```bash
source venv/bin/activate
```

### Step 4: Initialize Database
```bash
python database/init_db.py
```

### Step 5: Run Examples
```bash
python examples/demo.py
```

---

## 🎯 Quick Commands

### Run Tests
```bash
pytest tests/test_complete_system.py -v
```

### Start LangFlow
```bash
langflow run --host 0.0.0.0 --port 7860
```

### Docker Deployment
```bash
docker-compose -f docker-compose.new.yml up --build
```

---

## 📝 Quick Usage Examples

### 1. Simple Text Generation
```python
import asyncio
from app.gemini_enhanced import GeminiClient

async def main():
    client = GeminiClient(api_key="your_key")
    response = await client.generate_async(
        prompt="What is loan collateral?",
        temperature=0.7
    )
    print(response.text)

asyncio.run(main())
```

### 2. Intent Classification
```python
import asyncio
from app.gemini_enhanced import GeminiClient

async def main():
    client = GeminiClient(api_key="your_key")
    intent, confidence = await client.classify_intent(
        "What is collateral?"
    )
    print(f"{intent} ({confidence:.2f})")

asyncio.run(main())
```

### 3. Planner-Critique Loop
```python
import asyncio
from app.planner_critique import refine_response

async def main():
    response = await refine_response(
        query="What is collateral?",
        context="Context from RAG...",
        gemini_api_key="your_key",
        max_iterations=2
    )
    print(response)

asyncio.run(main())
```

### 4. Database Operations
```python
from database.db_manager import DatabaseManager

db = DatabaseManager("./database/loan_collateral.db")

# Create session
db.create_session("session_1", "user_1")

# Add conversation
db.add_conversation(
    session_id="session_1",
    user_message="What is collateral?",
    agent_response="Collateral is...",
    intent="question",
    confidence=0.95
)

# Get history
history = db.get_recent_conversations("session_1", limit=5)

db.close()
```

---

## 🔧 Configuration Quick Reference

### Essential Settings (.env)
```bash
# Required
GEMINI_API_KEY=your_api_key_here

# Database
SQLITE_DB_PATH=./database/loan_collateral.db
CHROMADB_PATH=./data/chromadb

# RAG
RAG_TOP_K=5
RAG_MAX_TOKENS=4000

# Critique
MAX_CRITIQUE_ITERATIONS=2
CRITIQUE_ACCEPTANCE_THRESHOLD=0.85

# Performance
TOKEN_BUDGET_MAX=8000
```

---

## 🏗️ Architecture Quick View

```
User Query
    ↓
Intent Classifier (greeting/question/command)
    ↓
History Manager (retrieve context)
    ↓
RAG Retriever (vector + web search)
    ↓
Planner-Critique Loop (iterate until approved)
    ├─ Generate response
    ├─ Evaluate quality
    └─ Refine if needed
    ↓
Store & Return
```

---

## 📊 Key Files

| Component | File | Lines |
|-----------|------|-------|
| Database Schema | `database/schema.sql` | 200 |
| Database Manager | `database/db_manager.py` | 550 |
| Gemini Client | `app/gemini_enhanced.py` | 450 |
| Planner-Critique | `app/planner_critique.py` | 350 |
| Intent Classifier | `langflow_flows/components/intent_classifier.py` | 150 |
| RAG Retriever | `langflow_flows/components/rag_retriever.py` | 350 |
| Response Validator | `langflow_flows/components/response_validator.py` | 200 |
| History Manager | `langflow_flows/components/history_manager.py` | 200 |
| Config Loader | `config/config_loader.py` | 250 |
| Tests | `tests/test_complete_system.py` | 450 |
| Examples | `examples/demo.py` | 350 |

**Total: 4,500+ lines**

---

## 🧪 Testing Quick Reference

```bash
# All tests
pytest tests/ -v

# Specific component
pytest tests/test_complete_system.py::TestDatabaseManager -v

# With coverage
pytest tests/ --cov=app --cov=database --cov-report=html

# Fast tests only (skip integration)
pytest tests/ -v -m "not integration"
```

---

## 🐛 Troubleshooting

### Problem: API Key Error
```bash
# Check if key is loaded
python -c "from config.config_loader import get_config; print(get_config().gemini_api_key[:10])"
```

### Problem: Database Not Found
```bash
# Reinitialize
python database/init_db.py
```

### Problem: Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Problem: LangFlow Won't Start
```bash
# Clear cache
rm -rf ~/.langflow
langflow run --host 0.0.0.0 --port 7860
```

---

## 📈 Performance Targets

| Metric | Target | How to Check |
|--------|--------|--------------|
| Latency | <8s | Check logs or demo output |
| Tokens | <8000 | `response.token_usage.total_tokens` |
| Cache Hit | >60% | `client.get_statistics()['cache_hit_rate']` |
| DB Query | <200ms | Run performance tests |
| Cost | <$0.05 | `response.token_usage.estimated_cost` |

---

## 🔒 Security Checklist

- [ ] API keys in `.env` (not committed)
- [ ] `.env` in `.gitignore`
- [ ] Input validation enabled
- [ ] Rate limiting configured
- [ ] Request size limits set
- [ ] SQL injection protection (parameterized queries)
- [ ] Error messages sanitized

---

## 📞 Common Tasks

### Check Database Stats
```python
from database.db_manager import DatabaseManager
db = DatabaseManager("./database/loan_collateral.db")
print(db.get_database_stats())
```

### Clear Cache
```python
from database.db_manager import DatabaseManager
db = DatabaseManager("./database/loan_collateral.db")
cleared = db.clear_expired_cache()
print(f"Cleared {cleared} entries")
```

### Prune Old Data
```python
from database.db_manager import DatabaseManager
db = DatabaseManager("./database/loan_collateral.db")
pruned = db.prune_old_context(days=30)
print(f"Pruned {pruned} entries")
```

### Get Performance Metrics
```python
from database.db_manager import DatabaseManager
db = DatabaseManager("./database/loan_collateral.db")
metrics = db.get_metrics_summary("response_time_ms", hours=24)
print(metrics)
```

---

## 🎯 Next Steps After Setup

1. **Test the System**: Run `python examples/demo.py`
2. **Review Logs**: Check `./logs/app.log`
3. **Run Tests**: Execute `pytest tests/ -v`
4. **Try LangFlow**: Start server and import flow
5. **Customize Config**: Adjust `.env` settings
6. **Add Documents**: Populate ChromaDB with your data
7. **Monitor Performance**: Check database stats regularly

---

## 📚 Documentation Links

- **Full README**: `README_NEW.md`
- **Implementation Details**: `IMPLEMENTATION_COMPLETE.md`
- **Examples**: `examples/demo.py`
- **Tests**: `tests/test_complete_system.py`
- **Schema**: `database/schema.sql`

---

## ✅ Verification Checklist

After setup, verify:

```bash
# 1. Environment variables loaded
python -c "from config.config_loader import get_config; get_config().validate()"

# 2. Database initialized
ls -lh database/loan_collateral.db

# 3. Dependencies installed
pip list | grep -E "google-generativeai|chromadb|langflow"

# 4. Tests pass
pytest tests/ -v --tb=short

# 5. Examples run
python examples/demo.py
```

---

**Status**: ✅ All components ready for use!

**Support**: Check logs in `./logs/` and review documentation in markdown files.

