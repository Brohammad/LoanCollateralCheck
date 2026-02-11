# Polymorphic Intent Routing System

## Overview

The Polymorphic Intent Routing System is an advanced intent classification and routing framework that enables intelligent conversation flow in AI agent systems. It provides pattern-based intent classification, multi-intent detection, context-aware routing, and graceful fallback handling.

## Architecture

### Core Components

1. **Intent Classifier** (`intent_classifier.py`)
   - Pattern-based classification using keywords, phrases, and regex
   - Multi-intent detection
   - Entity extraction
   - Confidence scoring (5 levels)
   - Sentiment analysis
   - Context-aware scoring bonuses

2. **Intent Router** (`router.py`)
   - Routes intents to handlers
   - Validates confidence thresholds
   - Checks authentication and context requirements
   - Handles multi-intent execution
   - Tracks execution metrics

3. **Route Registry** (`route_registry.py`)
   - Manages route registration
   - Priority-based routing
   - Route metrics tracking
   - Dynamic enabling/disabling

4. **Context Manager** (`context_manager.py`)
   - Session management
   - Conversation history tracking
   - User preferences storage
   - Session expiration

5. **Fallback Handler** (`fallback_handler.py`)
   - Handles unclear intents
   - 5 fallback strategies
   - Clarification generation
   - Human escalation

6. **Intent History Tracker** (`intent_history_tracker.py`)
   - Tracks all intents
   - Pattern analysis
   - User behavior insights
   - Time-based analytics

7. **API Endpoints** (`api.py`)
   - FastAPI integration
   - 25+ REST endpoints
   - Classification, routing, metrics

## Intent Types

The system supports 16 intent types:

### Business Operations
- `LOAN_APPLICATION` - Apply for loans
- `COLLATERAL_CHECK` - Check collateral requirements
- `CREDIT_HISTORY` - View credit history/score
- `DOCUMENT_UPLOAD` - Upload documents

### LinkedIn Features
- `PROFILE_ANALYSIS` - Analyze LinkedIn profile
- `JOB_MATCHING` - Find job matches
- `SKILL_RECOMMENDATION` - Get skill recommendations

### General Intents
- `GREETING` - Greetings and salutations
- `QUESTION` - Questions and inquiries
- `COMMAND` - Commands and actions
- `FEEDBACK` - User feedback
- `HELP` - Help requests
- `STATUS` - Status checks
- `SETTINGS` - Settings management

### Meta Intents
- `MULTI_INTENT` - Multiple intents detected
- `CLARIFICATION_NEEDED` - Clarification required
- `UNKNOWN` - Unknown intent

## Confidence Levels

Five confidence levels with score thresholds:

- **VERY_HIGH** (>0.9) - Very confident classification
- **HIGH** (0.75-0.9) - High confidence
- **MEDIUM** (0.5-0.75) - Medium confidence
- **LOW** (0.3-0.5) - Low confidence
- **VERY_LOW** (<0.3) - Very low confidence

## Fallback Strategies

Five strategies for handling unclear intents:

1. **ASK_CLARIFICATION** - Ask user for clarification
2. **USE_DEFAULT** - Use default response
3. **USE_HISTORY** - Infer from conversation history
4. **ESCALATE_TO_HUMAN** - Escalate to human agent
5. **PROVIDE_OPTIONS** - Show multiple options

## Quick Start

### 1. Initialize Routing System

```python
from routing.api import init_routing_system

# Initialize all components
init_routing_system()
```

### 2. Classify User Input

```python
from routing.intent_classifier import IntentClassifier

classifier = IntentClassifier()

# Single intent classification
intent = classifier.classify("I want to apply for a business loan")
print(f"Intent: {intent.intent_type}")
print(f"Confidence: {intent.confidence}")
print(f"Entities: {intent.entities}")

# Multi-intent classification
multi_result = classifier.classify_multi(
    "Check my credit score and help me apply for a loan"
)
print(f"Primary: {multi_result.primary_intent.intent_type}")
print(f"Secondary: {[i.intent_type for i in multi_result.secondary_intents]}")
print(f"Needs clarification: {multi_result.requires_clarification}")
```

### 3. Register Routes

```python
from routing.route_registry import RouteRegistry
from routing.models import Route, IntentType

registry = RouteRegistry()

# Define route
route = Route(
    route_id="loan_application",
    intent_type=IntentType.LOAN_APPLICATION,
    handler_name="handle_loan_application",
    priority=1,
    requires_auth=True,
    min_confidence=0.7
)

# Define handler
async def handle_loan_application(intent, context):
    loan_type = intent.entities.get("loan_type", "personal")
    amount = intent.entities.get("amount", "unspecified")
    
    return {
        "message": f"Processing {loan_type} loan application for ${amount}",
        "next_steps": ["Verify identity", "Check credit", "Submit documents"]
    }

# Register route
registry.register_route(route, handle_loan_application)
```

### 4. Route Intents

```python
from routing.router import IntentRouter
from routing.context_manager import ContextManager
from routing.fallback_handler import FallbackHandler

# Create components
context_manager = ContextManager()
fallback_handler = FallbackHandler()
router = IntentRouter(registry, context_manager, fallback_handler)

# Create session
context = context_manager.create_session(user_id="user123")

# Route intent
result = await router.route(
    intent,
    context=context,
    user_authenticated=True
)

print(f"Success: {result.success}")
print(f"Response: {result.response}")
```

### 5. Use API Endpoints

```python
from fastapi import FastAPI
from routing.api import router, init_routing_system

app = FastAPI()

# Initialize on startup
@app.on_event("startup")
async def startup():
    init_routing_system()

# Include routing endpoints
app.include_router(router)

# Now available at:
# POST /routing/classify
# POST /routing/route
# GET /routing/routes
# GET /routing/metrics/summary
# And 20+ more endpoints
```

## Pattern-Based Classification

### Adding Custom Patterns

```python
from routing.intent_classifier import IntentClassifier
from routing.models import IntentPattern, IntentType

classifier = IntentClassifier()

# Create custom pattern
pattern = IntentPattern(
    pattern_id="custom_refund",
    intent_type=IntentType.COMMAND,
    keywords=["refund", "cancel", "return"],
    phrases=["I want a refund", "cancel my order"],
    regex_patterns=[r"refund.*order", r"cancel.*(?:order|subscription)"],
    keyword_weight=0.3,
    phrase_weight=0.5,
    regex_weight=0.2,
    entity_patterns={
        "order_id": r"order[:\s]+(\w+)",
        "reason": r"because\s+(.+)"
    }
)

# Add pattern
classifier.add_pattern(pattern)

# Use classifier
intent = classifier.classify("I want a refund for order ABC123 because it's defective")
print(f"Entities: {intent.entities}")
# Output: {"order_id": "ABC123", "reason": "it's defective"}
```

### Pre-loaded Patterns

The classifier comes with 12 pre-loaded patterns:

1. **GREETING** - hello, hi, hey
2. **QUESTION** - what, how, why, questions with ?
3. **COMMAND** - do, make, create, update, delete
4. **LOAN_APPLICATION** - loan, apply, borrow (extracts loan_type, amount)
5. **COLLATERAL_CHECK** - collateral, asset, security (extracts asset_type)
6. **CREDIT_HISTORY** - credit, score, history
7. **DOCUMENT_UPLOAD** - upload, document, file (extracts document_type)
8. **PROFILE_ANALYSIS** - profile, analyze, linkedin
9. **JOB_MATCHING** - job, match, recommend (extracts job_type)
10. **SKILL_RECOMMENDATION** - skill, learn, recommend
11. **HELP** - help, assist, support
12. **STATUS** - status, progress, track

## Context-Aware Routing

### Session Context

```python
from routing.context_manager import ContextManager

manager = ContextManager(session_timeout_minutes=30)

# Create session
context = manager.create_session(
    user_id="user123",
    language="en",
    preferences={"theme": "dark", "notifications": True}
)

# Update context
manager.update_session(
    session_id=context.session_id,
    context_data={"last_action": "applied_for_loan"},
    topic="loan_application"
)

# Get conversation history
history = manager.get_conversation_history(context.session_id, n=5)

# Set user preference
manager.set_user_preference(context.session_id, "currency", "USD")

# Get statistics
stats = manager.get_statistics()
```

### Context Bonuses

The classifier applies context-aware bonuses:

- **Topic Continuity** (+10% confidence) - When intent matches current topic
- **User Preferences** (+5% confidence) - When intent matches frequent user intents

```python
# Example with context bonus
context = IntentContext(
    session_id="session123",
    user_id="user123",
    current_topic="loan_application",
    conversation_history=[
        Intent(intent_type=IntentType.LOAN_APPLICATION, ...),
        Intent(intent_type=IntentType.LOAN_APPLICATION, ...)
    ]
)

# This will get bonus for topic continuity
intent = classifier.classify("How much can I borrow?", context=context)
# Base confidence: 0.7 → With bonus: 0.77 (10% boost)
```

## Multi-Intent Handling

### Detection and Execution

```python
# Detect multiple intents
multi_result = classifier.classify_multi(
    "Check my credit score and help me apply for a business loan of $50,000"
)

print(f"Primary: {multi_result.primary_intent.intent_type}")
# Output: CREDIT_HISTORY (confidence 0.85)

print(f"Secondary: {[i.intent_type for i in multi_result.secondary_intents]}")
# Output: [LOAN_APPLICATION] (confidence 0.82)

print(f"Execution order: {multi_result.execution_order}")
# Output: [intent_id_1, intent_id_2]

print(f"Needs clarification: {multi_result.requires_clarification}")
# Output: False (score difference > 0.15)

# Route multiple intents
results = await router.route_multi(
    multi_result,
    context=context,
    user_authenticated=True
)

for result in results:
    print(f"{result.intent.intent_type}: {result.success}")
```

### Clarification Detection

When intent scores are close (difference < 0.15), the system flags for clarification:

```python
multi_result = classifier.classify_multi("I need help with my application")

if multi_result.requires_clarification:
    print("Multiple possible meanings detected:")
    for intent in multi_result.all_intents:
        print(f"- {intent.intent_type} (confidence: {intent.confidence})")
```

## Fallback Handling

### Strategy Selection

```python
from routing.fallback_handler import FallbackHandler, FallbackStrategy

handler = FallbackHandler(
    default_strategy=FallbackStrategy.ASK_CLARIFICATION,
    enable_history_fallback=True,
    enable_escalation=True
)

# Handle unclear intent
fallback_result = await handler.handle(unclear_intent, context)

print(f"Strategy used: {fallback_result.strategy_used}")
print(f"Response: {fallback_result.response}")
print(f"Clarification options: {fallback_result.clarification_options}")
print(f"Suggested actions: {fallback_result.suggested_actions}")
```

### Custom Default Responses

```python
# Set custom default response for intent type
handler.set_default_response(
    IntentType.LOAN_APPLICATION,
    "I can help you apply for a loan. What type of loan are you interested in?"
)
```

## Route Management

### Route Configuration

```python
from routing.models import Route, IntentType

route = Route(
    route_id="secure_loan_app",
    intent_type=IntentType.LOAN_APPLICATION,
    handler_name="handle_secure_loan",
    priority=1,  # 1 = highest priority
    requires_auth=True,  # Requires authentication
    requires_context=["user_profile", "credit_score"],  # Required context keys
    min_confidence=0.75,  # Minimum confidence threshold
    max_concurrent=10,  # Max concurrent executions
    rate_limit=100,  # Rate limit per minute
    description="Handle secure loan applications",
    tags=["loan", "secure", "business"],
    enabled=True
)
```

### Priority-Based Routing

Routes are executed in priority order (1 = highest):

```python
# Register multiple routes for same intent type
registry.register_route(
    Route(
        route_id="premium_loan",
        intent_type=IntentType.LOAN_APPLICATION,
        priority=1,  # Tried first
        requires_auth=True,
        min_confidence=0.9
    ),
    handle_premium_loan
)

registry.register_route(
    Route(
        route_id="standard_loan",
        intent_type=IntentType.LOAN_APPLICATION,
        priority=2,  # Tried second
        requires_auth=True,
        min_confidence=0.7
    ),
    handle_standard_loan
)

registry.register_route(
    Route(
        route_id="basic_loan_info",
        intent_type=IntentType.LOAN_APPLICATION,
        priority=3,  # Tried third
        requires_auth=False,
        min_confidence=0.5
    ),
    handle_basic_loan_info
)
```

### Dynamic Route Control

```python
# Enable/disable routes
registry.enable_route("premium_loan")
registry.disable_route("standard_loan")

# Get route metrics
metrics = registry.get_metrics("premium_loan")
print(f"Executions: {metrics.total_executions}")
print(f"Success rate: {metrics.success_rate}%")
print(f"Avg time: {metrics.avg_execution_time_ms}ms")

# Get top routes
top_routes = registry.get_top_routes(n=10, by="success_rate")
```

## Intent History & Analytics

### Track and Analyze

```python
from routing.intent_history_tracker import IntentHistoryTracker

tracker = IntentHistoryTracker(max_history_size=10000)

# Track intent
tracker.track(intent, user_id="user123")

# Get frequency
frequency = tracker.get_frequency(user_id="user123", since=datetime.now() - timedelta(days=7))

# Get top intents
top_intents = tracker.get_top_intents(n=10, user_id="user123")

# Get confidence statistics
conf_stats = tracker.get_confidence_stats(intent_type=IntentType.LOAN_APPLICATION)

# Get hourly volume
volume = tracker.get_hourly_volume(hours=24)

# Get user patterns
patterns = tracker.get_user_patterns("user123")
print(f"Most active hour: {patterns['most_active_hour']}")
print(f"Top intents: {patterns['top_intents']}")
print(f"Avg confidence: {patterns['avg_confidence']}")

# Get overall summary
summary = tracker.get_summary()
```

## API Endpoints Reference

### Classification

```bash
# Classify single intent
POST /routing/classify
{
  "user_input": "I want to apply for a business loan",
  "session_id": "session123",
  "user_id": "user123",
  "detect_multiple": false
}

# Classify multiple intents
POST /routing/classify-multi
{
  "user_input": "Check my credit and apply for a loan",
  "session_id": "session123",
  "user_id": "user123"
}
```

### Routing

```bash
# Route intent (classify + route)
POST /routing/route
{
  "user_input": "I need a $50,000 business loan",
  "session_id": "session123",
  "user_id": "user123",
  "user_authenticated": true
}
```

### Route Management

```bash
# List routes
GET /routing/routes?intent_type=LOAN_APPLICATION&enabled_only=true

# Get route
GET /routing/routes/{route_id}

# Enable route
POST /routing/routes/{route_id}/enable

# Disable route
POST /routing/routes/{route_id}/disable

# Get route metrics
GET /routing/routes/{route_id}/metrics

# Get metrics summary
GET /routing/metrics/summary

# Get top routes
GET /routing/metrics/top-routes?n=10&by=success_rate
```

### Session Management

```bash
# Create session
POST /routing/sessions?user_id=user123&language=en

# Get session
GET /routing/sessions/{session_id}

# End session
DELETE /routing/sessions/{session_id}

# Get session history
GET /routing/sessions/{session_id}/history?n=10
```

### History & Analytics

```bash
# Get intent history
GET /routing/history?user_id=user123&hours=24&limit=100

# Get frequency
GET /routing/history/frequency?user_id=user123&hours=24

# Get top intents
GET /routing/history/top-intents?n=10&hours=24

# Get confidence stats
GET /routing/history/confidence-stats?intent_type=LOAN_APPLICATION&hours=24

# Get hourly volume
GET /routing/history/hourly-volume?hours=24

# Get user patterns
GET /routing/history/user-patterns/{user_id}

# Get history summary
GET /routing/history/summary

# Get classifier statistics
GET /routing/classifier/statistics
```

### Health Check

```bash
GET /routing/health
```

## Integration Examples

### With FastAPI Application

```python
from fastapi import FastAPI
from routing.api import router, init_routing_system

app = FastAPI(title="AI Agent System")

@app.on_event("startup")
async def startup():
    init_routing_system()
    # Register custom routes here

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### With Monitoring (Prometheus)

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
intent_classifications = Counter(
    "intent_classifications_total",
    "Total intent classifications",
    ["intent_type", "confidence_level"]
)

classification_duration = Histogram(
    "intent_classification_duration_seconds",
    "Intent classification duration"
)

route_executions = Counter(
    "route_executions_total",
    "Total route executions",
    ["route_id", "success"]
)

active_sessions = Gauge(
    "active_sessions",
    "Number of active sessions"
)

# Track in handlers
@classification_duration.time()
def classify_with_metrics(user_input, context):
    intent = classifier.classify(user_input, context)
    
    intent_classifications.labels(
        intent_type=intent.intent_type.value,
        confidence_level=intent.confidence_level.value
    ).inc()
    
    return intent
```

### With Security (PART 3)

```python
from fastapi import Depends
from app.security import get_current_user, require_permission

@router.post("/route-secure")
async def route_with_auth(
    request: RouteRequest,
    current_user = Depends(get_current_user),
    _= Depends(require_permission("route:execute"))
):
    # User is authenticated and authorized
    result = await router.route(
        intent,
        context=context,
        user_authenticated=True
    )
    return result
```

### With Cost Tracking (PART 5)

```python
from app.cost_analysis import track_usage

async def route_with_cost_tracking(request: RouteRequest):
    # Track classification cost
    track_usage(
        service="intent_classification",
        tokens=len(request.user_input.split()),
        cost_per_token=0.0001
    )
    
    result = await router.route(intent, context)
    
    # Track routing cost
    if result.tokens_used:
        track_usage(
            service="intent_routing",
            tokens=result.tokens_used,
            cost_per_token=0.0002
        )
    
    return result
```

## Best Practices

### 1. Pattern Design

- Use specific keywords for high-confidence matches
- Include phrases for context-specific matches
- Use regex for complex patterns
- Set appropriate weights based on reliability

### 2. Route Priority

- Assign priority 1 to most specific/secure routes
- Higher priorities for authenticated routes
- Lower priorities for fallback routes

### 3. Confidence Thresholds

- Set higher thresholds (0.8+) for critical operations
- Medium thresholds (0.6-0.7) for standard operations
- Lower thresholds (0.4-0.5) for informational routes

### 4. Session Management

- Create sessions on first interaction
- Update context after each interaction
- Set appropriate timeout (30 minutes default)
- Clean up expired sessions regularly

### 5. Fallback Strategy

- Use ASK_CLARIFICATION for very low confidence
- Use HISTORY for returning users
- Escalate after 3 failed attempts
- Provide options for unknown intents

### 6. Monitoring

- Track route metrics regularly
- Monitor confidence trends
- Analyze user patterns
- Alert on high error rates

## Performance Considerations

- Pattern matching is O(n*m) where n=patterns, m=input length
- Use redis for session storage in production
- Implement caching for frequent classifications
- Set reasonable history limits (10,000 default)
- Clean up expired sessions periodically

## Troubleshooting

### Low Confidence Classifications

1. Add more patterns for the intent type
2. Increase pattern weights
3. Check for typos in keywords
4. Add more phrases for context

### Multi-Intent Not Detecting

1. Lower multi_intent_threshold (default 0.6)
2. Add patterns for secondary intent
3. Check if scores are too close (< 0.15 difference)

### Route Not Executing

1. Check route is enabled
2. Verify confidence meets minimum
3. Check authentication requirements
4. Verify context requirements met

### Session Expired

1. Increase session timeout
2. Implement session refresh on activity
3. Use persistent session storage

## Advanced Topics

### Custom Entity Extractors

```python
def extract_currency_amount(text):
    import re
    match = re.search(r'[$£€]\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
    if match:
        amount = match.group(1).replace(',', '')
        return float(amount)
    return None

# Add to pattern
pattern.entity_patterns["amount_extracted"] = extract_currency_amount
```

### Machine Learning Integration

```python
from transformers import pipeline

classifier_ml = pipeline("text-classification", model="intent-model")

def hybrid_classify(user_input, context):
    # Pattern-based (fast)
    pattern_intent = classifier.classify(user_input, context)
    
    # ML-based (accurate)
    ml_result = classifier_ml(user_input)[0]
    ml_intent = IntentType(ml_result['label'])
    ml_confidence = ml_result['score']
    
    # Combine scores (weighted average)
    if pattern_intent.intent_type == ml_intent:
        # Agreement - boost confidence
        combined_confidence = 0.3 * pattern_intent.confidence + 0.7 * ml_confidence
    else:
        # Disagreement - use ML if high confidence
        if ml_confidence > 0.9:
            return Intent(intent_type=ml_intent, confidence=ml_confidence, ...)
    
    return Intent(intent_type=pattern_intent.intent_type, confidence=combined_confidence, ...)
```

### A/B Testing Routes

```python
import random

def ab_test_route(intent, context):
    if random.random() < 0.5:
        # Variant A
        return await router.route(intent, context, strategy="conservative")
    else:
        # Variant B
        return await router.route(intent, context, strategy="aggressive")
```

## Conclusion

The Polymorphic Intent Routing System provides a production-ready foundation for intelligent conversation management. It combines pattern-based classification, context awareness, and graceful fallback handling to enable robust AI agent interactions.

For additional support:
- GitHub Issues: [Project Repository]
- Documentation: [Full API Reference]
- Examples: See `examples/routing_demo.py`
