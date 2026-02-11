# System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI AGENT WORKFLOW SYSTEM                          │
│                        (LangFlow-Compatible Architecture)                   │
└─────────────────────────────────────────────────────────────────────────────┘

                                   USER INPUT
                                       │
                                       ▼
                        ┌──────────────────────────┐
                        │   FastAPI Entry Point    │
                        │  POST /api/v1/handle     │
                        └──────────────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────┐
                        │     ORCHESTRATOR         │
                        │  (Intent Classifier)     │
                        │                          │
                        │  • Gemini Classification │
                        │  • Confidence Scoring    │
                        │  • Keyword Fallback      │
                        └──────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
              [Greeting?]                           [Question/
           confidence ≥ 0.6                      Command/Unclear]
                    │                                     │
                    ▼                                     ▼
         ┌────────────────────┐              ┌────────────────────┐
         │  GREETING AGENT    │              │  CHECK CACHE       │
         │                    │              │  (SQLite)          │
         │  • Quick Response  │              └────────────────────┘
         │  • Save to DB      │                       │
         └────────────────────┘              Cache Hit?│ Cache Miss
                    │                                  │
                    │                          ┌───────┴────────┐
                    │                          │                │
                    │                       [Use]            [Run]
                    │                      Cache            Search
                    │                          │                │
                    │                          └───────┬────────┘
                    │                                  ▼
                    │                      ┌────────────────────┐
                    │                      │   RAG PIPELINE     │
                    │                      │  (Parallel Async)  │
                    │                      ├────────────────────┤
                    │                      │ • Vector Search    │
                    │                      │ • Web Search (opt) │
                    │                      │ • LinkedIn (opt)   │
                    │                      └────────────────────┘
                    │                                  │
                    │                                  ▼
                    │                      ┌────────────────────┐
                    │                      │ Context Aggregator │
                    │                      │  • Merge Results   │
                    │                      │  • Rank & Filter   │
                    │                      └────────────────────┘
                    │                                  │
                    │                                  ▼
                    │                      ┌────────────────────┐
                    │                      │  PLANNER AGENT     │
                    │                      │                    │
                    │                      │  • Gemini LLM      │
                    │                      │  • Context-aware   │
                    │                      │  • Source Citation │
                    │                      └────────────────────┘
                    │                                  │
                    │                                  ▼
                    │                      ┌────────────────────┐
                    │                      │  CRITIQUE AGENT    │
                    │                      │                    │
                    │                      │  • Validate        │
                    │                      │  • Improve         │
                    │                      │  • Max 2 loops     │
                    │                      └────────────────────┘
                    │                                  │
                    │                           Approved?
                    │                                  │
                    └──────────────────────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────┐
                        │   DATABASE PERSISTENCE   │
                        │                          │
                        │  • Conversation Record   │
                        │  • Credit History        │
                        │  • Update Cache          │
                        └──────────────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────┐
                        │    RESPONSE FORMATTER    │
                        │                          │
                        │  • Add metadata          │
                        │  • Confidence disclaimer │
                        │  • Conversation ID       │
                        └──────────────────────────┘
                                       │
                                       ▼
                                  USER RESPONSE


═══════════════════════════════════════════════════════════════════════════════

                              STORAGE LAYER

┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│  SQLite DB      │  │  Vector Store    │  │  Cache Layer    │
│                 │  │                  │  │                 │
│ • Conversations │  │ • Pinecone       │  │ • Query Cache   │
│ • Credit Hist   │  │ • ChromaDB       │  │ • TTL: 1 hour   │
│ • Search Cache  │  │ • In-Memory      │  │ • SHA256 Hash   │
└─────────────────┘  └──────────────────┘  └─────────────────┘


═══════════════════════════════════════════════════════════════════════════════

                           EXTERNAL SERVICES

┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│  Google Gemini  │  │  Web Search API  │  │  LinkedIn API   │
│                 │  │                  │  │                 │
│ • Generation    │  │ • (placeholder)  │  │ • (placeholder) │
│ • Embeddings    │  │ • Ready to wire  │  │ • Ready to wire │
│ • Classification│  └──────────────────┘  └─────────────────┘
└─────────────────┘


═══════════════════════════════════════════════════════════════════════════════

                            LANGFLOW NODES

┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐               │
│  │ Orchestrator │──▶│  RAG Pipeline│──▶│   Intent     │               │
│  │    Node      │   │     Node     │   │ Classifier   │               │
│  └──────────────┘   └──────────────┘   └──────────────┘               │
│                                                                          │
│  Use as custom components OR call via HTTP API                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════

                           DEPLOYMENT OPTIONS

┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│  Docker         │  │  Kubernetes      │  │  Serverless     │
│                 │  │                  │  │                 │
│ • Dockerfile    │  │ • (templates in  │  │ • (adaptable    │
│ • Compose       │  │   NEXT_STEPS)    │  │   architecture) │
│ • Multi-stage   │  └──────────────────┘  └─────────────────┘
└─────────────────┘


═══════════════════════════════════════════════════════════════════════════════

KEY FEATURES:
• Intent Classification with Confidence (greeting/question/command/unclear)
• Multi-Agent Architecture (Greeting/Planner/Critique)
• RAG with Parallel Search (Vector + Web + LinkedIn)
• Conversation Persistence (SQLite with 3 tables)
• Query Caching (1-hour TTL, SHA256 hashing)
• Real Gemini API Integration (2.0-flash-exp, embeddings)
• LangFlow Compatible (custom nodes + API)
• Production Ready (Docker, CI/CD, Tests)

═══════════════════════════════════════════════════════════════════════════════
