# Cost Analysis & Optimization - Implementation Guide

Complete guide to the cost tracking and optimization system.

## Overview

The cost analysis system provides comprehensive tracking, budgeting, and optimization for LLM API usage costs.

**Features**:
- Real-time token usage tracking
- Automatic cost calculation
- Budget management with alerts
- Cost optimization suggestions
- Analytics and reporting
- Trend analysis and forecasting

---

## Architecture

### Components

1. **Cost Tracker** (`tracker.py`):
   - Tracks token usage in real-time
   - Aggregates metrics by user, model, operation
   - Calculates cache hit rates
   - Persists data periodically

2. **Cost Calculator** (`calculator.py`):
   - Calculates costs based on pricing models
   - Supports multiple LLM models
   - Estimates future costs
   - Compares model costs

3. **Budget Manager** (`budgets.py`):
   - Manages cost budgets (hourly, daily, weekly, monthly, yearly)
   - Generates alerts when thresholds exceeded
   - Supports per-user and per-feature budgets
   - Automatic period resets

4. **Cost Optimizer** (`optimizer.py`):
   - Analyzes usage patterns
   - Identifies optimization opportunities
   - Suggests model alternatives
   - Calculates ROI for optimizations

5. **Cost Analytics** (`analytics.py`):
   - Generates cost breakdowns
   - Analyzes trends
   - Forecasts future costs
   - Detects anomalies
   - Creates comprehensive reports

6. **Middleware** (`middleware.py`):
   - Automatic cost tracking for HTTP requests
   - Integrates with FastAPI
   - Captures token usage from LLM calls

7. **API Endpoints** (`api.py`):
   - RESTful API for cost data
   - Budget management endpoints
   - Analytics and reporting endpoints

---

## Usage

### 1. Basic Cost Tracking

```python
from cost_analysis.tracker import get_cost_tracker, track_operation
from cost_analysis.models import ModelType, OperationType

# Get global tracker
tracker = get_cost_tracker()
await tracker.start()

# Track an operation
token_usage, cost_record = await track_operation(
    model_type=ModelType.GEMINI_FLASH,
    operation_type=OperationType.GENERATION,
    prompt_tokens=150,
    completion_tokens=350,
    user_id="user_123",
    session_id="session_456",
)

print(f"Cost: ${cost_record.total_cost:.4f}")
print(f"Tokens: {token_usage.total_tokens}")

# Get metrics
metrics = tracker.get_metrics()
print(f"Total cost: ${metrics['total_cost']:.2f}")
print(f"Total requests: {metrics['total_requests']}")
print(f"Cache hit rate: {metrics['cache_hit_rate']:.1%}")
```

### 2. Cost Calculation

```python
from cost_analysis.calculator import CostCalculator
from cost_analysis.models import ModelType

calculator = CostCalculator()

# Estimate cost
cost = calculator.estimate_cost(
    model_type=ModelType.GEMINI_FLASH,
    prompt_tokens=1000,
    completion_tokens=2000,
)
print(f"Estimated cost: ${cost:.4f}")

# Compare models
comparison = calculator.compare_models(
    prompt_tokens=1000,
    completion_tokens=2000,
)
for model, cost in comparison.items():
    print(f"{model.value}: ${cost:.4f}")

# Monthly projection
projection = calculator.calculate_monthly_projection(
    daily_requests=1000,
    avg_prompt_tokens=150,
    avg_completion_tokens=350,
    model_type=ModelType.GEMINI_FLASH,
)
print(f"Monthly cost: ${projection['monthly_cost']:.2f}")
```

### 3. Budget Management

```python
from cost_analysis.budgets import BudgetManager
from cost_analysis.models import BudgetPeriod

budget_manager = BudgetManager()
await budget_manager.start()

# Create a monthly budget
budget = budget_manager.create_budget(
    name="monthly_llm_budget",
    limit=100.0,  # $100
    period=BudgetPeriod.MONTHLY,
    alert_thresholds=[75.0, 90.0, 100.0],  # Alert at 75%, 90%, 100%
)

# Record spending
alerts = await budget_manager.record_spend(
    amount=5.50,
    user_id="user_123",
    feature="chat",
)

# Check for alerts
if alerts:
    for alert in alerts:
        print(f"Budget alert: {alert.message}")
        print(f"  Severity: {alert.severity}")
        print(f"  Remaining: ${alert.remaining_budget:.2f}")

# Get budget status
status = budget.get_status()
print(f"Budget: {status['name']}")
print(f"Used: ${status['current_spend']:.2f} / ${status['limit']:.2f}")
print(f"Percent: {status['percent_used']:.1f}%")
```

### 4. Cost Optimization

```python
from cost_analysis.optimizer import CostOptimizer

optimizer = CostOptimizer(cost_tracker=tracker)

# Analyze and get suggestions
suggestions = await optimizer.analyze_and_suggest(lookback_days=7)

for suggestion in suggestions:
    print(f"\n{suggestion.title}")
    print(f"  Category: {suggestion.category}")
    print(f"  Priority: {suggestion.priority}")
    print(f"  Potential savings: ${suggestion.potential_savings:.2f}/month")
    print(f"  Implementation effort: {suggestion.implementation_effort}")
    print(f"  Actions:")
    for action in suggestion.action_items:
        print(f"    - {action}")

# Calculate ROI
if suggestions:
    roi = optimizer.calculate_roi(
        suggestion=suggestions[0],
        implementation_cost=500.0,  # $500 to implement
        implementation_time_days=5,
    )
    print(f"\nROI Analysis:")
    print(f"  Monthly savings: ${roi['monthly_savings']:.2f}")
    print(f"  Break-even: {roi['break_even_months']:.1f} months")
    print(f"  ROI: {roi['roi_percent']:.1f}%")
    print(f"  Recommendation: {roi['recommendation']}")
```

### 5. Analytics and Reporting

```python
from cost_analysis.analytics import CostAnalytics
from datetime import datetime, timedelta

analytics = CostAnalytics(cost_tracker=tracker)

# Generate cost breakdown
period_start = datetime.utcnow() - timedelta(days=7)
period_end = datetime.utcnow()

breakdown = await analytics.generate_cost_breakdown(period_start, period_end)

print(f"Total cost: ${breakdown.total_cost:.2f}")
print(f"Total requests: {breakdown.total_requests}")
print(f"Avg cost per request: ${breakdown.avg_cost_per_request:.4f}")
print(f"\nBy model:")
for model, cost in breakdown.by_model.items():
    print(f"  {model}: ${cost:.2f}")

# Analyze trend
from cost_analysis.models import BudgetPeriod

trend = await analytics.analyze_trend(
    period=BudgetPeriod.DAILY,
    num_periods=30,
)

print(f"\nTrend: {trend.trend_direction} ({trend.trend_percent:+.1f}%)")
print(f"Forecast next period: ${trend.forecast_next_period:.2f}")
print(f"Confidence: ${trend.confidence_interval[0]:.2f} - ${trend.confidence_interval[1]:.2f}")

# Generate comprehensive report
report = await analytics.generate_report(
    period_start=period_start,
    period_end=period_end,
    include_breakdowns=True,
    include_trends=True,
)

print(f"\nReport Summary:")
print(f"  Period: {report['period_days']} days")
print(f"  Total cost: ${report['summary']['total_cost']:.2f}")
print(f"  Monthly projection: ${report['projections']['monthly_projection']:.2f}")
```

### 6. FastAPI Integration

```python
from fastapi import FastAPI, Request
from cost_analysis.middleware import CostTrackingMiddleware, track_llm_operation
from cost_analysis.models import ModelType, OperationType

app = FastAPI()

# Add cost tracking middleware
app.add_middleware(CostTrackingMiddleware)

@app.post("/api/chat")
async def chat(request: Request, message: str):
    # Call LLM
    response = await llm_call(message)
    
    # Track the operation
    await track_llm_operation(
        request=request,
        model_type=ModelType.GEMINI_FLASH,
        operation_type=OperationType.GENERATION,
        prompt_tokens=len(message.split()),  # Simplified
        completion_tokens=len(response.split()),
    )
    
    return {"response": response}
```

---

## API Endpoints

### Cost Estimates

**POST /api/v1/cost/estimate**

Estimate cost for a given token usage.

```json
{
  "model": "gemini-2.0-flash-exp",
  "input_tokens": 1000,
  "output_tokens": 2000
}
```

Response:
```json
{
  "model": "gemini-2.0-flash-exp",
  "input_tokens": 1000,
  "output_tokens": 2000,
  "total_tokens": 3000,
  "input_cost": 0.000075,
  "output_cost": 0.0006,
  "total_cost": 0.000675
}
```

### Metrics

**GET /api/v1/cost/metrics**

Get current cost metrics.

Query parameters:
- `period_start` (optional): ISO datetime
- `period_end` (optional): ISO datetime
- `user_id` (optional): Filter by user

Response:
```json
{
  "total_cost": 45.50,
  "total_requests": 1250,
  "total_tokens": 450000,
  "avg_cost_per_request": 0.0364,
  "cache_hit_rate": 0.35,
  "by_model": {
    "gemini-2.0-flash-exp": {"cost": 40.00, "requests": 1100},
    "gemini-1.5-pro": {"cost": 5.50, "requests": 150}
  }
}
```

### Budgets

**POST /api/v1/cost/budgets**

Create a new budget.

```json
{
  "name": "monthly_budget",
  "limit": 100.0,
  "period": "monthly",
  "alert_thresholds": [75, 90, 100],
  "user_id": null
}
```

**GET /api/v1/cost/budgets**

List all budgets.

**GET /api/v1/cost/budgets/{name}/status**

Get budget status.

**GET /api/v1/cost/alerts**

Get budget alerts.

Query parameters:
- `acknowledged`: Filter by acknowledgment status
- `severity`: Filter by severity

### Analytics

**GET /api/v1/cost/breakdown**

Get cost breakdown.

Query parameters:
- `period_start`: ISO datetime (required)
- `period_end`: ISO datetime (required)

**GET /api/v1/cost/trend**

Get cost trend analysis.

Query parameters:
- `period`: hourly/daily/weekly/monthly
- `num_periods`: Number of periods to analyze

**GET /api/v1/cost/report**

Generate comprehensive cost report.

### Optimization

**GET /api/v1/cost/suggestions**

Get optimization suggestions.

Query parameters:
- `lookback_days`: Number of days to analyze (default: 7)

**GET /api/v1/cost/suggestions/{id}/roi**

Calculate ROI for a suggestion.

Query parameters:
- `implementation_cost`: Cost to implement
- `implementation_days`: Days to implement

---

## Pricing

Current pricing per 1M tokens (as of 2026):

| Model | Input | Output |
|-------|--------|---------|
| Gemini Flash | $0.075 | $0.30 |
| Gemini Pro | $1.25 | $5.00 |
| Gemini Ultra | $5.00 | $20.00 |
| Text Embedding | $0.025 | - |

**Cache Discount**: 50% off for cached tokens

---

## Configuration

### Environment Variables

```bash
# Enable cost tracking
ENABLE_COST_TRACKING=true

# Persistence interval (seconds)
COST_PERSISTENCE_INTERVAL=60

# Budget check interval (seconds)
BUDGET_CHECK_INTERVAL=300

# Default currency
COST_CURRENCY=USD
```

### Custom Pricing

```python
from cost_analysis.calculator import CostCalculator
from cost_analysis.models import ModelType

custom_pricing = {
    ModelType.GEMINI_FLASH: {
        "prompt": 0.05,  # Custom price per 1M tokens
        "completion": 0.20,
    }
}

calculator = CostCalculator(pricing=custom_pricing)
```

---

## Best Practices

### 1. Budget Setup

- Create budgets at multiple levels (global, per-user, per-feature)
- Set alert thresholds at 75%, 90%, and 100%
- Review budgets monthly
- Adjust based on actual usage patterns

### 2. Optimization

- Review suggestions weekly
- Implement high-priority, low-effort optimizations first
- Track actual savings after implementation
- A/B test model changes before full rollout

### 3. Monitoring

- Check cost metrics daily
- Set up alert notifications
- Monitor cache hit rates
- Review top users and features regularly

### 4. Cost Control

- Use caching aggressively
- Choose appropriate models (Flash vs Pro)
- Optimize prompt lengths
- Implement rate limiting per user
- Set per-user spending limits

---

## Troubleshooting

### High Costs

1. Check which models are being used
2. Review top users/features
3. Check cache hit rate
4. Analyze token usage patterns
5. Review optimization suggestions

### Budget Alerts Not Working

1. Verify budget manager is started
2. Check budget period hasn't expired
3. Verify spend is being recorded
4. Check alert thresholds

### Inaccurate Cost Calculations

1. Verify pricing table is up to date
2. Check token counts are accurate
3. Verify model types are correct
4. Review cost calculator configuration

---

## Examples

### Complete Integration Example

```python
from fastapi import FastAPI
from cost_analysis import (
    CostTracker,
    BudgetManager,
    CostOptimizer,
    CostAnalytics,
)
from cost_analysis.middleware import CostTrackingMiddleware
from cost_analysis.models import BudgetPeriod

# Initialize
app = FastAPI()
tracker = CostTracker()
budget_manager = BudgetManager(cost_tracker=tracker)
optimizer = CostOptimizer(cost_tracker=tracker)
analytics = CostAnalytics(cost_tracker=tracker)

# Add middleware
app.add_middleware(CostTrackingMiddleware)

# Setup budgets
@app.on_event("startup")
async def startup():
    await tracker.start()
    await budget_manager.start()
    
    # Create budgets
    budget_manager.create_budget(
        name="daily_budget",
        limit=10.0,
        period=BudgetPeriod.DAILY,
    )
    
    budget_manager.create_budget(
        name="monthly_budget",
        limit=300.0,
        period=BudgetPeriod.MONTHLY,
    )

@app.on_event("shutdown")
async def shutdown():
    await tracker.stop()
    await budget_manager.stop()

# Periodic optimization check
@app.get("/admin/optimize")
async def check_optimizations():
    suggestions = await optimizer.analyze_and_suggest(lookback_days=7)
    return {"suggestions": [s.dict() for s in suggestions]}

# Cost dashboard
@app.get("/admin/costs")
async def cost_dashboard():
    from datetime import datetime, timedelta
    
    period_start = datetime.utcnow() - timedelta(days=7)
    period_end = datetime.utcnow()
    
    report = await analytics.generate_report(
        period_start=period_start,
        period_end=period_end,
    )
    
    budgets = budget_manager.get_all_budgets()
    alerts = budget_manager.get_alerts(acknowledged=False)
    
    return {
        "report": report,
        "budgets": budgets,
        "alerts": [a.dict() for a in alerts],
    }
```

---

## Performance Considerations

- Cost tracking adds minimal overhead (< 1ms per request)
- Metrics are calculated in memory for speed
- Persistence happens asynchronously
- Budget checks run periodically, not per request
- Analytics queries can be cached

---

## Security

- Cost data may contain sensitive information
- Protect cost endpoints with authentication
- Log cost access for audit
- Consider anonymizing user IDs in reports
- Encrypt cost data at rest

---

For issues or questions, see the main documentation or create an issue.
