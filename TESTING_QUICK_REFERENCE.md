# Test Suite - Quick Reference

## Run Commands

### Basic Testing
```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Performance tests
pytest tests/performance/ -v

# With coverage
pytest --cov=app --cov=database --cov=monitoring --cov-report=html
```

### By Marker
```bash
pytest -m unit          # Fast unit tests
pytest -m integration   # Integration tests
pytest -m performance   # Performance tests
pytest -m smoke         # Smoke tests
pytest -m slow          # Slow tests
pytest -m "performance and not slow"  # Fast performance tests
```

### Parallel Execution
```bash
pytest -n auto          # Auto-detect CPUs
pytest -n 4             # 4 workers
```

### Debug Mode
```bash
pytest -v -s            # Verbose with print
pytest -x               # Stop on first failure
pytest --maxfail=3      # Stop after 3 failures
pytest --pdb            # Drop into debugger on failure
pytest -l               # Show local variables
```

## Test Statistics

- **Total Tests**: 150+
- **Unit Tests**: 100+
- **Integration Tests**: 25+
- **Performance Tests**: 15+
- **Lines of Code**: 8,500+
- **Coverage Target**: 85%+

## Test Files

### Unit Tests (4,500 lines)
- `test_gemini_client.py` - 30 tests
- `test_database_manager.py` - 35 tests
- `test_rag_retriever.py` - 35 tests
- `test_intent_classifier.py` - 30 tests
- `test_planner_critique.py` - 30 tests
- `test_cache_manager.py` - 35 tests

### Integration Tests (1,000 lines)
- `test_end_to_end.py` - 25 tests

### Performance Tests (1,200 lines)
- `test_load.py` - 15 tests

## CI/CD Workflows

### Tests Workflow
- Matrix: Python 3.11, 3.12
- Runs: Unit, integration, smoke, performance
- Artifacts: Coverage reports, test results

### Lint Workflow
- Black, isort, Flake8, Pylint, MyPy
- Docstring coverage (70%+)

### Security Workflow
- Safety, Bandit, Semgrep
- Gitleaks, TruffleHog
- Radon complexity

## Coverage Commands

```bash
# HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov=app --cov-report=term-missing

# XML for CI
pytest --cov=app --cov-report=xml
```

## Common Fixtures

From `conftest.py`:

- `test_database` - Clean SQLite database
- `mock_gemini_client` - Mocked Gemini API
- `mock_vector_search` - Mocked vector store
- `mock_web_search` - Mocked web search
- `sample_conversations` - Test conversation data
- `sample_rag_results` - Test RAG results

## Performance Targets

- P50: < 4 seconds
- P95: < 8 seconds
- P99: < 15 seconds
- Throughput: 1000 RPM sustained
- Burst: 100 concurrent requests
- Users: 100 concurrent

## Quick Troubleshooting

```bash
# Import errors
pip install -r requirements.txt
bash scripts/install_monitoring.sh

# Clear cache
pytest --cache-clear

# Show durations
pytest --durations=10

# Specific test
pytest tests/unit/test_gemini_client.py::TestGeminiClient::test_successful_api_call
```

## Test Markers

- `@pytest.mark.unit` - Unit test
- `@pytest.mark.integration` - Integration test
- `@pytest.mark.performance` - Performance test
- `@pytest.mark.slow` - Slow test (skipped by default)
- `@pytest.mark.smoke` - Critical path test
- `@pytest.mark.asyncio` - Async test

## Environment Variables

```bash
export GOOGLE_API_KEY="your-api-key"
```

## Documentation

Full guide: `tests/README.md` (950 lines)
