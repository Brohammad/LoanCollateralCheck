# Cost Analysis & Optimization System

## Overview

The Cost Analysis & Optimization System provides comprehensive cost tracking, budget management, and optimization recommendations for LLM API usage. It helps monitor spending, prevent budget overruns, and identify cost-saving opportunities.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Components](#components)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Best Practices](#best-practices)

## Features

### 1. **Cost Tracking**
- Real-time token usage and cost tracking
- SQLite-based persistent storage
- Support for all Gemini models (2.0 Flash, 1.5 Pro, 1.5 Flash, Embeddings)
- Context-aware pricing tiers
- User and session attribution
- Metadata tagging for analysis

### 2. **Budget Management**
- Multi-period budgets (daily, weekly, monthly, yearly)
- Per-user and per-model budgets
- Configurable alert thresholds
- Automatic alert generation
- Alert acknowledgement workflow

### 3. **Cost Optimization**
- AI-driven optimization recommendations
- Model switching analysis
- Prompt optimization suggestions
- Caching recommendations
- Batch processing opportunities
- Rate limiting strategies
- Context management optimization

### 4. **Analytics & Reporting**
- Comprehensive usage reports
- Cost trends and projections
- Top users and models analysis
- Hourly and daily breakdowns
- Period comparisons
- Export to JSON/CSV

### 5. **Integration**
- FastAPI middleware for automatic tracking
- Context manager for manual tracking
- Decorator for function-level tracking
- REST API endpoints
- Cost headers in responses

## Architecture

```
cost_analysis/
├── models.py          # Data models (Pydantic)
├── pricing.py         # Pricing configuration
├── tracker.py         # Cost tracking (SQLite)
├── calculator.py      # Cost calculations & analytics
├── budget.py          # Budget management
├── optimizer.py       # Optimization recommendations
├── analytics.py       # Reporting & analytics
├── middleware.py      # FastAPI integration
└── api.py            # REST API endpoints
```

### Data Flow

```
┌─────────────────┐
│  LLM Request    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Middleware    │  (Automatic tracking)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cost Tracker   │  (Store usage & costs)
└────────┬────────┘
         │
         ├──────────► Budget Manager (Check limits)
         │
         ├──────────► Calculator (Analytics)
         │
         ├──────────► Optimizer (Recommendations)
         │
         └──────────► Analytics (Reports)
```

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```python
from cost_analysis.tracker import CostTracker
from cost_analysis.models import ModelType, RequestType

# Initialize tracker
tracker = CostTracker()

# Track a request
record = tracker.track_usage(
    model=ModelType.GEMINI_15_PRO,
    request_type=RequestType.GENERATION,
    input_tokens=1000,
    output_tokens=500,
    user_id="user123",
)

print(f"Cost: ${record.total_cost:.6f}")
```

### FastAPI Integration

```python
from fastapi import FastAPI
from cost_analysis.middleware import cost_tracking_middleware
from cost_analysis.tracker import CostTracker

app = FastAPI()
tracker = CostTracker()

# Add middleware
app.add_middleware(
    cost_tracking_middleware(tracker),
)
```

### Budget Management

```python
from cost_analysis.budget import BudgetManager
from cost_analysis.models import BudgetPeriod

# Create budget manager
budget_manager = BudgetManager()

# Create daily budget
budget = budget_manager.create_budget(
    name="Daily API Budget",
    period=BudgetPeriod.DAILY,
    limit=10.0,
    warning_threshold=0.8,  # Alert at 80%
    critical_threshold=0.95,  # Critical at 95%
)

# Update usage
updated = budget_manager.update_budget_usage(budget.id, tracker)

# Check alerts
alerts = budget_manager.get_alerts(budget_id=budget.id)
```

## Components

### 1. Cost Tracker

Tracks all LLM requests and calculates costs based on token usage.

```python
from cost_analysis.tracker import CostTracker

tracker = CostTracker(db_path="costs.db")

# Track usage
record = tracker.track_usage(
    model=ModelType.GEMINI_15_PRO,
    request_type=RequestType.GENERATION,
    input_tokens=1000,
    output_tokens=500,
    user_id="user123",
    session_id="session456",
    agent_name="planner",
    metadata={"task": "create_plan"},
)

# Get summary
summary = tracker.get_usage_summary(
    start_time=start,
    end_time=end,
    user_id="user123",  # Optional filter
    model=ModelType.GEMINI_15_PRO,  # Optional filter
)

# Get total cost
total = tracker.get_total_cost(
    start_time=start,
    end_time=end,
)

# Get recent requests
records = tracker.get_recent_requests(
    limit=100,
    user_id="user123",
)

# Cleanup old records
deleted = tracker.cleanup_old_records(days=90)
```

### 2. Cost Calculator

Advanced cost calculations and projections.

```python
from cost_analysis.calculator import CostCalculator

calculator = CostCalculator()

# Project future costs
projection = calculator.calculate_projected_cost(
    historical_records=records,
    days=30,
)

# Cost breakdown
breakdown = calculator.calculate_cost_breakdown(records)

# Savings opportunity
savings = calculator.calculate_savings_opportunity(
    records,
    target_model=ModelType.GEMINI_15_FLASH,
)

# ROI calculation
roi = calculator.calculate_roi(
    implementation_cost=1000,
    monthly_savings=500,
)

# Compare models
comparison = calculator.pricing_model.compare_model_costs(
    input_tokens=10000,
    output_tokens=5000,
)
```

### 3. Budget Manager

Manage spending limits and alerts.

```python
from cost_analysis.budget import BudgetManager
from cost_analysis.models import BudgetPeriod

manager = BudgetManager(db_path="budgets.db")

# Create budget
budget = manager.create_budget(
    name="Monthly Budget",
    period=BudgetPeriod.MONTHLY,
    limit=1000.0,
    user_id="user123",  # Optional: per-user budget
    model=ModelType.GEMINI_15_PRO,  # Optional: per-model budget
    warning_threshold=0.8,
    critical_threshold=0.95,
)

# List budgets
budgets = manager.list_budgets(
    user_id="user123",
    period=BudgetPeriod.MONTHLY,
)

# Update usage
updated = manager.update_budget_usage(budget.id, tracker)

# Get alerts
alerts = manager.get_alerts(
    budget_id=budget.id,
    level=AlertLevel.WARNING,
    acknowledged=False,
)

# Acknowledge alert
acknowledged = manager.acknowledge_alert(alert.id, "admin")

# Reset budget
reset = manager.reset_budget(budget.id)

# Delete budget
manager.delete_budget(budget.id)
```

### 4. Cost Optimizer

Generate cost-saving recommendations.

```python
from cost_analysis.optimizer import CostOptimizer

optimizer = CostOptimizer()

# Analyze and get recommendations
recommendations = optimizer.analyze_and_recommend(records)

for rec in recommendations:
    print(f"Type: {rec.optimization_type}")
    print(f"Priority: {rec.priority}")
    print(f"Savings: ${rec.estimated_savings:.2f}/month")
    print(f"Description: {rec.description}")
    print(f"Effort: {rec.implementation_effort}")
    print(f"Steps: {rec.implementation_steps}")
```

**Recommendation Types:**

1. **Model Optimization**: Switch to cheaper models where appropriate
2. **Prompt Optimization**: Reduce token usage (20% savings)
3. **Response Caching**: Cache frequent queries (30% savings)
4. **Batch Processing**: Batch similar requests (15% savings)
5. **Rate Limiting**: Control cost spikes (10% savings)
6. **Context Management**: Smart context pruning (25% savings)

### 5. Analytics Engine

Comprehensive reporting and analysis.

```python
from cost_analysis.analytics import CostAnalytics

analytics = CostAnalytics(tracker)

# Generate comprehensive report
report = analytics.generate_report(
    start_time=start,
    end_time=end,
    user_id="user123",  # Optional
)

# Report contains:
# - Summary statistics
# - Top users by cost
# - Top models by usage
# - Daily breakdown
# - Hourly patterns
# - Recommendations

# Get cost trends
trends = analytics.get_cost_trends(days=30)

# Compare periods
comparison = analytics.compare_periods(
    period1_start=start1,
    period1_end=end1,
    period2_start=start2,
    period2_end=end2,
)

# Export report
analytics.export_report(report, format="json", path="report.json")
analytics.export_report(report, format="csv", path="report.csv")
```

### 6. Middleware Integration

Automatic tracking for FastAPI applications.

```python
from fastapi import FastAPI
from cost_analysis.middleware import (
    CostTrackingMiddleware,
    cost_tracking_middleware,
)
from cost_analysis.tracker import CostTracker

app = FastAPI()
tracker = CostTracker()

# Option 1: Use factory function
app.add_middleware(
    cost_tracking_middleware(
        tracker=tracker,
        enabled=True,
        add_headers=True,
    )
)

# Option 2: Use class directly
app.add_middleware(
    CostTrackingMiddleware,
    tracker=tracker,
)

# Cost data will be automatically tracked
# Response headers: X-Cost-Tokens, X-Cost-USD
```

**Context Manager:**

```python
from cost_analysis.middleware import CostTrackingContext

async def process_request():
    async with CostTrackingContext(
        tracker=tracker,
        model=ModelType.GEMINI_15_PRO,
        user_id="user123",
    ) as ctx:
        # Make LLM calls
        result = await llm_call()
        
        # Track tokens
        ctx.add_tokens(
            input_tokens=1000,
            output_tokens=500,
        )
    
    # Cost is automatically tracked
```

**Decorator:**

```python
from cost_analysis.middleware import track_cost

@track_cost(
    tracker=tracker,
    model=ModelType.GEMINI_15_PRO,
)
async def generate_response(prompt: str):
    # Function implementation
    return response
```

## API Reference

### REST API Endpoints

All endpoints are prefixed with `/api/v1/cost`.

#### Cost Summary

```http
GET /api/v1/cost/summary?days=30&user_id=user123&model=gemini-1.5-pro
```

Returns aggregated usage statistics for a time period.

**Response:**
```json
{
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-01-31T23:59:59Z",
  "total_requests": 1000,
  "total_tokens": 1500000,
  "total_cost": 12.50,
  "by_model": {
    "gemini-1.5-pro": {
      "count": 500,
      "tokens": 750000,
      "cost": 10.00
    }
  },
  "by_user": {
    "user123": {
      "count": 300,
      "cost": 7.50
    }
  }
}
```

#### Cost Estimate

```http
POST /api/v1/cost/estimate
Content-Type: application/json

{
  "model": "gemini-1.5-pro",
  "input_tokens": 1000,
  "output_tokens": 500
}
```

Calculate cost for a hypothetical request.

**Response:**
```json
{
  "model": "gemini-1.5-pro",
  "input_tokens": 1000,
  "output_tokens": 500,
  "total_tokens": 1500,
  "input_cost": 0.00125,
  "output_cost": 0.0025,
  "total_cost": 0.00375
}
```

#### Cost Trends

```http
GET /api/v1/cost/trends?days=30
```

Get cost trends over time.

#### Usage Report

```http
GET /api/v1/cost/report?days=30&user_id=user123
```

Generate comprehensive usage report.

#### Create Budget

```http
POST /api/v1/cost/budgets
Content-Type: application/json

{
  "name": "Daily Budget",
  "period": "daily",
  "limit": 10.0,
  "user_id": "user123",
  "warning_threshold": 0.8,
  "critical_threshold": 0.95
}
```

#### List Budgets

```http
GET /api/v1/cost/budgets?user_id=user123&period=daily
```

#### Update Budget Usage

```http
POST /api/v1/cost/budgets/{budget_id}/update
```

#### Get Budget Alerts

```http
GET /api/v1/cost/budgets/{budget_id}/alerts?acknowledged=false
```

#### Acknowledge Alert

```http
POST /api/v1/cost/budgets/alerts/{alert_id}/acknowledge?acknowledged_by=admin
```

#### Optimization Recommendations

```http
GET /api/v1/cost/optimize?days=30
```

#### Cost Breakdown

```http
GET /api/v1/cost/breakdown?days=30&user_id=user123
```

#### Model Comparison

```http
GET /api/v1/cost/models/compare?input_tokens=10000&output_tokens=5000
```

## Examples

See `examples/cost_tracking_example.py` for comprehensive examples covering:

1. Basic cost tracking
2. Usage summaries
3. Budget management
4. Per-user budgets
5. Optimization recommendations
6. Analytics reports
7. Model cost comparisons
8. Cost projections
9. Detailed breakdowns
10. Alert management

Run examples:

```bash
python examples/cost_tracking_example.py
```

## Best Practices

### 1. Budget Configuration

- **Set realistic limits**: Base budgets on historical usage
- **Use appropriate periods**: Daily for active development, monthly for production
- **Configure thresholds**: 80% warning, 95% critical is a good starting point
- **Per-user budgets**: Prevent individual users from exceeding quotas
- **Per-model budgets**: Control usage of expensive models

### 2. Cost Optimization

- **Review recommendations regularly**: Check weekly for optimization opportunities
- **Implement high-priority items first**: Focus on high-savings, low-effort changes
- **Use cheaper models**: Gemini 1.5 Flash is 94% cheaper than Pro for similar tasks
- **Implement caching**: Can save 30% on repeated queries
- **Optimize prompts**: Reduce token usage by 20% through better prompt engineering

### 3. Monitoring

- **Track trends**: Monitor cost increases week-over-week
- **Set up alerts**: Get notified before budgets are exceeded
- **Analyze patterns**: Identify peak usage times and adjust accordingly
- **Review top users**: Identify high-cost users for optimization
- **Audit expensive requests**: Review requests with high token counts

### 4. Data Retention

- **Cleanup old records**: Run cleanup monthly to save storage
- **Export historical data**: Archive data before cleanup
- **Retain summaries**: Keep aggregated statistics even after cleanup

### 5. Integration

- **Use middleware**: Automatic tracking is more reliable than manual
- **Add metadata**: Tag requests with agent, task, priority for analysis
- **Include user context**: Essential for per-user budgets and analysis
- **Monitor performance**: Ensure tracking doesn't impact latency

## Pricing Information

### Current Gemini Pricing (as of 2024)

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Best For |
|-------|----------------------|------------------------|----------|
| **Gemini 2.0 Flash** | Free (preview) | Free (preview) | Testing, development |
| **Gemini 1.5 Flash** | $0.075 | $0.30 | Production, high-volume |
| **Gemini 1.5 Pro** | $1.25 | $5.00 | Complex tasks |
| **Text Embedding** | Free | - | Embeddings |

**Context Pricing:**
- Standard (<128K tokens): Base rate
- Extended (>128K tokens): Doubled rate

### Cost Savings Examples

**Example 1: Switch from Pro to Flash**
- Before: 1M tokens on Pro = $6.25
- After: 1M tokens on Flash = $0.375
- **Savings: 94% ($5.875 per 1M tokens)**

**Example 2: Implement Caching**
- Before: 100K requests/month at $100
- After: 30% cache hit rate = $70
- **Savings: 30% ($30/month)**

**Example 3: Optimize Prompts**
- Before: 2000 tokens/request
- After: 1600 tokens/request (20% reduction)
- **Savings: 20% on all requests**

## Troubleshooting

### Issue: Costs not being tracked

**Check:**
1. Middleware is properly installed
2. Cost data is attached to responses
3. Database is writable
4. Tracker is initialized

### Issue: Budget alerts not triggering

**Check:**
1. Budget is active
2. Thresholds are configured correctly
3. Budget usage is being updated
4. Alert generation is enabled

### Issue: Inaccurate cost calculations

**Check:**
1. Token counts are correct
2. Model type is correct
3. Pricing configuration is up to date
4. Context length is considered

### Issue: Performance impact

**Optimize:**
1. Use batch inserts
2. Cleanup old records regularly
3. Add database indexes
4. Use async operations

## Support

For issues, questions, or contributions:
- GitHub Issues: [repository]/issues
- Documentation: [repository]/docs
- Examples: [repository]/examples

## License

MIT License - See LICENSE file for details
