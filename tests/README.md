# Testing Guide

Complete guide to the testing infrastructure for the Loan Collateral Check AI Agent System.

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Writing Tests](#writing-tests)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Coverage Reports](#coverage-reports)
7. [Troubleshooting](#troubleshooting)

## Overview

Our testing strategy includes:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions and end-to-end flows
- **Performance Tests**: Test system performance under load
- **Smoke Tests**: Quick validation of critical functionality
- **Security Tests**: Automated security scanning

### Test Coverage Goals

- Unit Tests: **85%+ coverage**
- Integration Tests: Cover all critical user flows
- Performance Tests: Validate latency and throughput targets
- CI/CD: Automated testing on every push and PR

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── pytest.ini               # Pytest configuration
├── test_monitoring.py       # Monitoring system tests
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_gemini_client.py
│   ├── test_database_manager.py
│   ├── test_rag_retriever.py
│   ├── test_intent_classifier.py
│   ├── test_planner_critique.py
│   └── test_cache_manager.py
├── integration/             # Integration tests
│   ├── __init__.py
│   └── test_end_to_end.py
└── performance/             # Performance tests
    ├── __init__.py
    └── test_load.py
```

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_API_KEY="your-api-key"
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Performance tests only
pytest tests/performance/ -v

# Monitoring tests only
pytest tests/test_monitoring.py -v
```

### Run Tests by Marker

```bash
# Run only smoke tests
pytest -m smoke

# Run only integration tests
pytest -m integration

# Run only performance tests (exclude slow ones)
pytest -m "performance and not slow"

# Run slow tests
pytest -m slow
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=app --cov=database --cov=monitoring --cov=config \
       --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html
```

### Parallel Test Execution

```bash
# Run tests in parallel (4 workers)
pytest -n 4

# Run tests in parallel (auto-detect CPUs)
pytest -n auto
```

### Run Specific Tests

```bash
# Run a specific test file
pytest tests/unit/test_gemini_client.py

# Run a specific test class
pytest tests/unit/test_gemini_client.py::TestGeminiClient

# Run a specific test function
pytest tests/unit/test_gemini_client.py::TestGeminiClient::test_successful_api_call
```

### Verbose Output

```bash
# Verbose output with print statements
pytest -v -s

# Show local variables on failure
pytest -l

# Stop on first failure
pytest -x

# Stop after N failures
pytest --maxfail=3
```

## Writing Tests

### Basic Test Structure

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.unit
class TestMyComponent:
    """Test suite for MyComponent"""
    
    @pytest.fixture
    def my_component(self):
        """Create component instance for testing"""
        return MyComponent()
    
    @pytest.mark.asyncio
    async def test_basic_functionality(self, my_component):
        """Test basic functionality"""
        result = await my_component.do_something()
        assert result is not None
```

### Using Fixtures

Fixtures are defined in `tests/conftest.py`:

```python
def test_with_database(test_database):
    """Test using database fixture"""
    # test_database provides a clean SQLite database
    pass

def test_with_mock_client(mock_gemini_client):
    """Test using mock Gemini client"""
    # mock_gemini_client is pre-configured AsyncMock
    pass

def test_with_sample_data(sample_conversations):
    """Test using sample data"""
    # sample_conversations provides test conversation data
    pass
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function"""
    result = await some_async_function()
    assert result == expected_value
```

### Mocking

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock():
    """Test with mocked dependencies"""
    mock_client = AsyncMock()
    mock_client.generate_async.return_value = "Test response"
    
    with patch('app.gemini_client.GeminiClient', return_value=mock_client):
        result = await function_using_client()
        assert result == "Test response"
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "greeting"),
    ("what is?", "question"),
    ("show me", "command"),
])
def test_intent_classification(input, expected):
    """Test multiple input/output combinations"""
    result = classify_intent(input)
    assert result == expected
```

### Test Markers

Available markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.smoke` - Smoke tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.asyncio` - Async tests

## CI/CD Pipeline

### GitHub Actions Workflows

#### Tests Workflow (`.github/workflows/tests.yml`)

Runs on every push and PR:

1. **Matrix Testing**: Python 3.11 and 3.12
2. **Unit Tests**: With coverage reporting
3. **Integration Tests**: End-to-end flow testing
4. **Smoke Tests**: Quick validation
5. **Performance Tests**: On main branch only
6. **Artifacts**: Coverage reports and test results

#### Lint Workflow (`.github/workflows/lint.yml`)

Code quality checks:

- Black (formatting)
- isort (import sorting)
- Flake8 (style guide)
- Pylint (code analysis)
- MyPy (type checking)
- Docstring coverage

#### Security Workflow (`.github/workflows/security.yml`)

Security scanning:

- Safety (dependency vulnerabilities)
- Bandit (security linting)
- Semgrep (static analysis)
- Gitleaks (secret scanning)
- TruffleHog (secret scanning)
- Radon (code complexity)

### Viewing CI Results

1. Go to repository's **Actions** tab
2. Select workflow run
3. View job logs and artifacts
4. Download coverage reports

## Coverage Reports

### HTML Coverage Report

```bash
# Generate HTML report
pytest --cov=app --cov=database --cov=monitoring --cov=config \
       --cov-report=html

# Open report
open htmlcov/index.html
```

### Terminal Coverage Report

```bash
# Show coverage in terminal
pytest --cov=app --cov-report=term-missing
```

### Coverage Targets

- **Unit Tests**: 85%+ coverage
- **Critical Paths**: 95%+ coverage
- **Overall**: 80%+ coverage

### Coverage Configuration

Coverage settings in `pytest.ini`:

```ini
[pytest]
addopts = --cov=app --cov=database --cov=monitoring --cov=config
          --cov-report=html
          --cov-report=term
          --cov-report=xml
```

## Troubleshooting

### Common Issues

#### Import Errors

```bash
# Problem: ModuleNotFoundError
# Solution: Install monitoring dependencies
pip install -r requirements.txt
bash scripts/install_monitoring.sh
```

#### Async Test Failures

```bash
# Problem: RuntimeError: no running event loop
# Solution: Use @pytest.mark.asyncio decorator
@pytest.mark.asyncio
async def test_function():
    pass
```

#### Database Locked

```bash
# Problem: sqlite3.OperationalError: database is locked
# Solution: Use test_database fixture which creates clean DB
def test_function(test_database):
    db = DatabaseManager(db_path=test_database)
```

#### Slow Tests

```bash
# Run only fast tests
pytest -m "not slow"

# Set timeout for tests
pytest --timeout=30

# Identify slow tests
pytest --durations=10
```

#### Mock Issues

```bash
# Problem: Mock not being called
# Solution: Verify patch path is correct
# Patch where the object is used, not where it's defined
with patch('app.orchestrator.GeminiClient') as mock:
    pass
```

### Debug Mode

```bash
# Run with pdb debugger
pytest --pdb

# Drop into debugger on failures
pytest --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb

# Show print statements
pytest -s
```

### Test Isolation

```bash
# Run tests in separate processes
pytest --forked

# Clear pytest cache
pytest --cache-clear
```

## Performance Testing

### Latency Targets

- P50: < 4 seconds
- P95: < 8 seconds
- P99: < 15 seconds

### Load Testing

```bash
# Run load tests
pytest tests/performance/test_load.py -v

# Run stress tests (slow)
pytest tests/performance/test_load.py -v -m slow
```

### Performance Benchmarks

```bash
# Install pytest-benchmark
pip install pytest-benchmark

# Run benchmarks
pytest tests/performance/ --benchmark-only
```

## Best Practices

### Test Naming

- Use descriptive test names
- Follow pattern: `test_<what>_<condition>_<expected>`
- Example: `test_gemini_api_timeout_raises_error`

### Test Organization

- One test class per component
- Group related tests together
- Use fixtures for setup/teardown

### Test Data

- Use fixtures for test data
- Keep test data minimal but realistic
- Use factories for generating test data

### Assertions

- One logical assertion per test
- Use specific assertion messages
- Check both positive and negative cases

### Mocking

- Mock external dependencies
- Don't mock code under test
- Verify mock calls when necessary

### Documentation

- Add docstrings to test classes and functions
- Explain complex test scenarios
- Document test data and fixtures

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)

## Test Statistics

Current test coverage:

- **Total Tests**: 150+
- **Unit Tests**: 100+
- **Integration Tests**: 20+
- **Performance Tests**: 15+
- **Test Execution Time**: ~2-3 minutes
- **Code Coverage**: Target 85%+

## Continuous Improvement

- Add tests for new features
- Increase coverage for low-coverage modules
- Optimize slow tests
- Update tests when requirements change
- Review and refactor tests regularly
