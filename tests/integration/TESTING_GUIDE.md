# Integration Testing Suite - Complete Guide

## Overview

Comprehensive integration testing suite for the AI Agent System covering end-to-end workflows, performance benchmarks, load testing, and chaos engineering.

## Test Structure

```
tests/integration/
├── __init__.py                    # Module initialization
├── pytest.ini                     # Pytest configuration
├── run_tests.py                   # Test runner script
├── test_loan_workflow.py          # Loan application workflow tests
├── test_linkedin_workflow.py      # LinkedIn integration tests
├── test_performance.py            # Performance benchmarks
├── test_load.py                   # Load testing scenarios
├── test_chaos.py                  # Chaos engineering tests
├── test_contracts.py              # API contract tests
└── test_smoke.py                  # Quick smoke tests
```

## Test Categories

### 1. Smoke Tests (`test_smoke.py`)
**Purpose**: Quick verification of critical functionality  
**Duration**: <1 minute  
**Run with**: `python run_tests.py smoke`

**Tests**:
- Health endpoints respond
- Basic intent classification works
- Core services are up
- Authentication is enforced
- Session creation works
- Error handling functions

**When to run**:
- After deployment
- Before starting work
- In CI/CD pipeline (fast feedback)

### 2. Workflow Tests

#### Loan Application Workflow (`test_loan_workflow.py`)
**Purpose**: End-to-end loan application testing  
**Duration**: 2-5 minutes  
**Run with**: `pytest tests/integration/test_loan_workflow.py -v`

**Test Scenarios**:
1. **Complete Loan Workflow** - Full application from start to finish
   - Authentication
   - Intent classification (loan application)
   - Credit history check
   - Profile analysis (LinkedIn)
   - Collateral verification
   - Document upload
   - Application submission
   - Cost tracking verification
   
2. **Multi-Intent Workflow** - Handle multiple intents
   - "Check my credit score and apply for a loan"
   - Detect multiple intents
   - Execute in correct order
   
3. **Error Handling** - Graceful failure scenarios
   - Insufficient credit score
   - Missing documents
   - Invalid collateral
   - Authentication failures
   
4. **Fallback Handling** - Unclear intent handling
   - Ambiguous requests
   - Clarification generation
   - Options presentation
   
5. **Concurrent Applications** - Multiple simultaneous requests
   - 10 concurrent loan applications
   - Rate limiting verification
   - System stability

#### LinkedIn Workflow (`test_linkedin_workflow.py`)
**Purpose**: LinkedIn integration testing  
**Duration**: 2-5 minutes  
**Run with**: `pytest tests/integration/test_linkedin_workflow.py -v`

**Test Scenarios**:
1. **Complete LinkedIn Workflow**
   - Profile parsing
   - Skill extraction (33 categories)
   - Job matching
   - Skill recommendations
   - Cost tracking
   
2. **Job Matching Accuracy**
   - Skills alignment verification
   - Experience level matching
   - Industry match validation
   - Match score justification
   
3. **Skill Gap Analysis**
   - Current vs. required skills
   - Development plan generation
   - Learning resource recommendations
   
4. **Multi-Intent LinkedIn**
   - "Analyze my profile and recommend jobs"
   - Multiple LinkedIn intents
   
5. **Intent History Tracking**
   - LinkedIn intent tracking
   - User pattern analysis
   - Top intents identification

### 3. Performance Benchmarks (`test_performance.py`)
**Purpose**: Measure system performance  
**Duration**: 5-10 minutes  
**Run with**: `python run_tests.py performance`

**Benchmarks**:

1. **Intent Classification Latency**
   - Target: P95 < 50ms, Avg < 30ms
   - Measures: P50, P95, P99, Average, Std Dev
   - 800 iterations across 8 intent types
   
2. **Routing Throughput**
   - Target: >100 req/s
   - 1,000 requests with concurrency 10
   - Success rate >99%
   
3. **End-to-End Workflow Performance**
   - Target: P95 < 500ms
   - Complete loan application workflow
   - 50 iterations
   
4. **Concurrent User Scalability**
   - Target: <10% latency increase at 100 users
   - Tests: 10, 50, 100 concurrent users
   - 10 operations per user
   
5. **Database Query Performance**
   - Simple queries: P95 < 20ms
   - Complex queries: P95 < 100ms
   
6. **Memory Efficiency**
   - Target: <50MB increase after 1,000 operations
   - No memory leaks
   
7. **Cache Effectiveness**
   - Target: >2x speedup
   - Cold vs. warm cache comparison

**Metrics Output**:
```
=== Intent Classification Latency ===
Average: 18.45ms
Median (P50): 16.20ms
P95: 28.30ms
P99: 35.70ms
Std Dev: 8.12ms
```

### 4. Load Tests (`test_load.py`)
**Purpose**: Test system under various load conditions  
**Duration**: 10-30 minutes  
**Run with**: `python run_tests.py load`

**Test Scenarios**:

1. **Sustained Load**
   - 50 concurrent users for 5 minutes
   - Target: <100ms avg latency, >99% success rate
   - Simulates normal production load
   
2. **Spike Load**
   - Sudden increase: 10 → 100 users
   - Target: <20% latency increase
   - Tests auto-scaling response
   
3. **Stress Test**
   - Find breaking point
   - Gradual increase: 10, 25, 50, 100, 200, 500 users
   - Identify maximum capacity
   - Target: Support ≥50 concurrent users
   
4. **Soak Test (Endurance)**
   - 20 concurrent users for 10 minutes (simulating 1 hour)
   - Target: Stable performance, no memory leaks
   - Success rate variance <5%
   
5. **Volume Test**
   - Process 10,000 intents
   - Batch processing (100 at a time)
   - Target: >99% success rate, <1000ms batch latency

**Results Format**:
```
=== Sustained Load Test Results ===
Duration: 300.15s
Concurrent users: 50
Total requests: 2,508
Successful: 2,501
Failed: 7
Average latency: 85.32ms
Success rate: 99.72%
Throughput: 8.36 req/s
```

### 5. Chaos Engineering Tests (`test_chaos.py`)
**Purpose**: Test system resilience under failure conditions  
**Duration**: 5-15 minutes  
**Run with**: `python run_tests.py chaos`

**Failure Scenarios**:

1. **Database Failure**
   - Database unavailable
   - Expected: Graceful degradation, cached data used
   - Returns 503 with proper error or uses cache
   
2. **External Service Timeout**
   - LinkedIn service takes >10s
   - Expected: Timeout enforced (<5s), proper error
   - Returns 408/504
   
3. **Cache Failure (Redis)**
   - Redis unavailable
   - Expected: Continue without cache, slight latency increase
   - Still returns 200, no crashes
   
4. **Partial Service Outage**
   - Credit service down, LinkedIn up
   - Expected: Independent services continue working
   - Isolation verified
   
5. **Network Latency Injection**
   - 2 second latency added
   - Expected: Circuit breaker activates, fast failures
   - Not all requests wait full 2s
   
6. **Cascading Failure Prevention**
   - Auth service fails
   - Expected: Public endpoints work, protected fail gracefully
   - System doesn't cascade
   
7. **Resource Exhaustion**
   - 1,000 requests, 100 concurrency
   - Expected: Rate limiting, graceful rejection
   - Crash rate <10%
   
8. **Data Corruption**
   - Malformed requests (empty, oversized, null, invalid)
   - Expected: Validation catches, returns 400/422
   - No 500 errors
   
9. **Dependency Failure Isolation**
   - Gemini AI failure → Routing still works
   - Cost tracking failure → Operations continue
   - Monitoring failure → System operates normally
   
10. **Recovery After Failure**
    - Temporary service outage
    - Expected: Auto-recovery when service returns
    - Circuit breaker resets

**Results Format**:
```
=== Resource Exhaustion Results ===
Status 200: 850 requests
Status 429: 145 requests (rate limited)
Status 500: 5 requests (0.5% crash rate)
```

### 6. Contract Tests (`test_contracts.py`)
**Purpose**: Ensure API contracts remain stable  
**Duration**: 1-3 minutes  
**Run with**: `pytest tests/integration/test_contracts.py -v`

**Contract Validations**:

1. **Intent Classification Contract**
   - Required fields present
   - Correct types
   - Valid value ranges
   
2. **Route Result Contract**
   - Response schema stable
   - Field types correct
   
3. **Multi-Intent Contract**
   - Primary/secondary intents structure
   - Execution order format
   
4. **Session Contract**
   - Session creation/retrieval
   - Required session fields
   
5. **Error Response Contract**
   - Standard error format
   - Detail field present
   
6. **Pagination Contract**
   - List endpoints have pagination
   - Count/total fields
   
7. **Backward Compatibility**
   - Old API calls still work
   - Optional fields handled
   
8. **API Versioning**
   - Version exposed in headers/body
   
9. **Rate Limit Headers**
   - Standard headers present
   
10. **Authentication Contract**
    - Bearer token format recognized
    - Proper status codes
    
11. **Content Type Negotiation**
    - JSON request/response
    - Proper Content-Type headers
    
12. **Timestamp Format**
    - ISO 8601 format
    - Consistent across endpoints
    
13. **Enum Values**
    - Stable enum sets
    - Known intent types
    - Known confidence levels

## Running Tests

### Quick Start

```bash
# Smoke tests (fastest)
python tests/integration/run_tests.py smoke

# Full integration suite
python tests/integration/run_tests.py integration

# Performance benchmarks
python tests/integration/run_tests.py performance

# Load tests
python tests/integration/run_tests.py load

# Chaos engineering
python tests/integration/run_tests.py chaos

# Everything
python tests/integration/run_tests.py all

# With coverage
python tests/integration/run_tests.py coverage
```

### Using pytest directly

```bash
# Run specific test file
pytest tests/integration/test_loan_workflow.py -v

# Run specific test
pytest tests/integration/test_loan_workflow.py::TestLoanApplicationWorkflow::test_complete_loan_workflow -v

# Run by marker
pytest tests/integration -m smoke -v
pytest tests/integration -m "performance and not slow" -v

# Show print statements
pytest tests/integration/test_performance.py -s

# Stop on first failure
pytest tests/integration -x

# Run in parallel (requires pytest-xdist)
pytest tests/integration -n 4
```

### CI/CD Integration

```yaml
# GitHub Actions example
name: Integration Tests
on: [push, pull_request]

jobs:
  smoke-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run smoke tests
        run: python tests/integration/run_tests.py smoke
  
  full-tests:
    runs-on: ubuntu-latest
    needs: smoke-tests
    steps:
      - uses: actions/checkout@v2
      - name: Run full integration tests
        run: python tests/integration/run_tests.py integration
```

## Test Markers

Use pytest markers to filter tests:

- `@pytest.mark.smoke` - Quick smoke tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.load` - Load tests
- `@pytest.mark.chaos` - Chaos engineering
- `@pytest.mark.slow` - Slow tests (>1 minute)
- `@pytest.mark.asyncio` - Async tests

## Performance Targets

| Metric | Target | Test |
|--------|--------|------|
| Intent classification (P95) | <50ms | test_performance.py |
| Routing throughput | >100 req/s | test_performance.py |
| End-to-end workflow (P95) | <500ms | test_performance.py |
| Simple DB query (P95) | <20ms | test_performance.py |
| Complex DB query (P95) | <100ms | test_performance.py |
| Scalability degradation | <10% at 100 users | test_performance.py |
| Memory increase | <50MB after 1k ops | test_performance.py |
| Cache speedup | >2x | test_performance.py |
| Sustained load success rate | >99% | test_load.py |
| Spike latency increase | <20% | test_load.py |
| Minimum capacity | ≥50 concurrent users | test_load.py |
| Soak stability | <5% variance | test_load.py |
| Volume processing | >99% success | test_load.py |

## Debugging Failed Tests

### View detailed output
```bash
pytest tests/integration/test_loan_workflow.py -vv -s
```

### Show local variables on failure
```bash
pytest tests/integration/test_loan_workflow.py -l
```

### Drop into debugger on failure
```bash
pytest tests/integration/test_loan_workflow.py --pdb
```

### Run only failed tests
```bash
pytest tests/integration --lf
```

### Generate HTML report
```bash
pytest tests/integration --html=report.html --self-contained-html
```

## Best Practices

### 1. Test Independence
- Each test should be independent
- Use fixtures for setup/teardown
- Don't rely on test execution order

### 2. Test Data
- Use deterministic test data
- Clean up after tests
- Avoid hardcoded IDs

### 3. Assertions
- Use specific assertions
- Include helpful error messages
- Test positive and negative cases

### 4. Performance Tests
- Run multiple iterations
- Calculate statistics (mean, median, percentiles)
- Set realistic targets

### 5. Chaos Tests
- Test one failure at a time
- Verify graceful degradation
- Check recovery mechanisms

### 6. CI/CD
- Run smoke tests on every commit
- Run full suite on pull requests
- Run performance tests nightly
- Run chaos tests weekly

## Troubleshooting

### Tests timing out
```bash
# Increase timeout
pytest tests/integration --timeout=60
```

### Connection errors
- Check if services are running
- Verify network connectivity
- Check firewall settings

### Flaky tests
- Add retries for network operations
- Increase wait times
- Use exponential backoff

### Memory issues
- Increase system memory
- Reduce batch sizes
- Run fewer concurrent tests

## Contributing

When adding new tests:

1. Follow existing patterns
2. Add appropriate markers
3. Update this documentation
4. Ensure tests are independent
5. Include docstrings
6. Set realistic targets

## Examples

### Example: Adding a new workflow test

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_new_workflow(self, test_client: AsyncClient, user_data: Dict):
    """
    Test new feature workflow
    
    Steps:
    1. Setup
    2. Execute
    3. Verify
    """
    # Setup
    response = await test_client.post("/setup", json=user_data)
    assert response.status_code == 200
    
    # Execute
    result = await test_client.post("/execute", json={"data": "test"})
    assert result.status_code == 200
    
    # Verify
    verify = await test_client.get("/verify")
    assert verify.status_code == 200
```

### Example: Adding a performance benchmark

```python
@pytest.mark.asyncio
@pytest.mark.performance
async def test_new_operation_latency(self, test_client: AsyncClient):
    """
    Benchmark new operation latency
    
    Target: P95 < 100ms
    """
    latencies = []
    
    for _ in range(100):
        start = time.perf_counter()
        await test_client.post("/new-operation", json={"test": "data"})
        end = time.perf_counter()
        latencies.append((end - start) * 1000)
    
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]
    
    assert p95 < 100, f"P95 latency {p95:.2f}ms exceeds 100ms target"
```

## Conclusion

This integration testing suite provides comprehensive coverage of:
- ✅ End-to-end workflows
- ✅ Performance benchmarks
- ✅ Load testing
- ✅ Chaos engineering
- ✅ API contracts
- ✅ Smoke tests

Total: **2,000+ lines** of integration tests ensuring production readiness.
