# Example API Requests

This file contains example API requests for testing the AI Agent Workflow system.

## Basic Greeting

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/handle" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-001",
    "text": "Hello! How are you?"
  }'
```

## Question with RAG

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/handle" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-001",
    "text": "What is machine learning and how does it work?",
    "use_web": false,
    "use_linkedin": false
  }'
```

## Question with Web Search

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/handle" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-001",
    "text": "What are the latest trends in AI for 2026?",
    "use_web": true,
    "use_linkedin": false
  }'
```

## Command Request

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/handle" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-001",
    "text": "Create a summary of neural networks",
    "use_web": false,
    "use_linkedin": false
  }'
```

## Get Conversation History

```bash
curl "http://127.0.0.1:8000/api/v1/history/user-001?limit=10"
```

## Health Check

```bash
curl "http://127.0.0.1:8000/health"
```

## Root Endpoint (API Info)

```bash
curl "http://127.0.0.1:8000/"
```

## Python Requests Examples

### Using Python requests library

```python
import requests
import json

# Configuration
BASE_URL = "http://127.0.0.1:8000"
USER_ID = "user-001"

# Send a message
def send_message(text, use_web=False, use_linkedin=False):
    response = requests.post(
        f"{BASE_URL}/api/v1/handle",
        json={
            "user_id": USER_ID,
            "text": text,
            "use_web": use_web,
            "use_linkedin": use_linkedin
        }
    )
    return response.json()

# Get history
def get_history(user_id, limit=10):
    response = requests.get(
        f"{BASE_URL}/api/v1/history/{user_id}",
        params={"limit": limit}
    )
    return response.json()

# Examples
if __name__ == "__main__":
    # Greeting
    result = send_message("Hello!")
    print("Greeting:", json.dumps(result, indent=2))
    
    # Question
    result = send_message("What is Python?")
    print("Question:", json.dumps(result, indent=2))
    
    # History
    history = get_history(USER_ID)
    print("History:", json.dumps(history, indent=2))
```

## httpie Examples

If you have httpie installed:

```bash
# Greeting
http POST http://127.0.0.1:8000/api/v1/handle \
  user_id="user-001" \
  text="Hello!"

# Question
http POST http://127.0.0.1:8000/api/v1/handle \
  user_id="user-001" \
  text="What is AI?" \
  use_web:=false \
  use_linkedin:=false

# History
http GET http://127.0.0.1:8000/api/v1/history/user-001 limit==10
```

## Testing Different Intents

### Greeting Intent
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/handle" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "text": "Hi there!"}'
```

### Question Intent
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/handle" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "text": "How does RAG work?"}'
```

### Command Intent
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/handle" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "text": "Build a summary of the document"}'
```

### Unclear Intent
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/handle" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "text": "asdf qwerty"}'
```
