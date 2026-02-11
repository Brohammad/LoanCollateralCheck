-- SQLite Schema for AI Agent System
-- Version: 1.0
-- Created: 2026-02-11

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- User Sessions Table
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_metadata TEXT, -- JSON string for additional data
    is_active BOOLEAN DEFAULT 1
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_last_activity ON user_sessions(last_activity);
CREATE INDEX idx_user_sessions_active ON user_sessions(is_active);

-- Conversation History Table
CREATE TABLE IF NOT EXISTS conversation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_message TEXT NOT NULL,
    agent_response TEXT NOT NULL,
    intent TEXT, -- greeting, question, command, etc.
    confidence REAL,
    response_time_ms INTEGER,
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT, -- JSON string for additional context
    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX idx_conversation_session ON conversation_history(session_id);
CREATE INDEX idx_conversation_created ON conversation_history(created_at DESC);
CREATE INDEX idx_conversation_intent ON conversation_history(intent);

-- Credit History Table (Context Storage)
CREATE TABLE IF NOT EXISTS credit_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    context_type TEXT NOT NULL, -- summary, key_fact, entity, etc.
    context_key TEXT NOT NULL,
    context_value TEXT NOT NULL,
    relevance_score REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP, -- For TTL
    metadata TEXT, -- JSON string
    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX idx_credit_session ON credit_history(session_id);
CREATE INDEX idx_credit_type ON credit_history(context_type);
CREATE INDEX idx_credit_key ON credit_history(context_key);
CREATE INDEX idx_credit_relevance ON credit_history(relevance_score DESC);
CREATE INDEX idx_credit_expires ON credit_history(expires_at);
CREATE UNIQUE INDEX idx_credit_unique ON credit_history(session_id, context_key, context_type);

-- Search Cache Table
CREATE TABLE IF NOT EXISTS search_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT UNIQUE NOT NULL, -- Hash of the search query
    query_text TEXT NOT NULL,
    search_type TEXT NOT NULL, -- vector, web, hybrid
    results TEXT NOT NULL, -- JSON string of results
    result_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1,
    ttl_seconds INTEGER DEFAULT 3600, -- 1 hour default
    expires_at TIMESTAMP
);

CREATE INDEX idx_cache_hash ON search_cache(query_hash);
CREATE INDEX idx_cache_type ON search_cache(search_type);
CREATE INDEX idx_cache_expires ON search_cache(expires_at);
CREATE INDEX idx_cache_accessed ON search_cache(accessed_at DESC);

-- Response Cache Table (for Gemini API responses)
CREATE TABLE IF NOT EXISTS response_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input_hash TEXT UNIQUE NOT NULL,
    input_text TEXT NOT NULL,
    model_name TEXT NOT NULL,
    response_text TEXT NOT NULL,
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1,
    ttl_seconds INTEGER DEFAULT 7200, -- 2 hours default
    expires_at TIMESTAMP
);

CREATE INDEX idx_response_hash ON response_cache(input_hash);
CREATE INDEX idx_response_model ON response_cache(model_name);
CREATE INDEX idx_response_expires ON response_cache(expires_at);

-- Critique History Table (for tracking planner-critique iterations)
CREATE TABLE IF NOT EXISTS critique_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    iteration INTEGER NOT NULL,
    planner_response TEXT NOT NULL,
    critique_score REAL,
    accuracy_score REAL,
    completeness_score REAL,
    clarity_score REAL,
    critique_feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversation_history(id) ON DELETE CASCADE
);

CREATE INDEX idx_critique_conversation ON critique_history(conversation_id);
CREATE INDEX idx_critique_iteration ON critique_history(iteration);

-- API Call Logs Table (for monitoring and debugging)
CREATE TABLE IF NOT EXISTS api_call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_name TEXT NOT NULL, -- gemini, serpapi, chromadb, etc.
    endpoint TEXT,
    request_method TEXT,
    request_params TEXT, -- JSON string
    response_status INTEGER,
    response_time_ms INTEGER,
    token_count INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_logs_name ON api_call_logs(api_name);
CREATE INDEX idx_api_logs_created ON api_call_logs(created_at DESC);
CREATE INDEX idx_api_logs_status ON api_call_logs(response_status);

-- Performance Metrics Table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    metric_unit TEXT, -- ms, tokens, count, etc.
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT -- JSON string
);

CREATE INDEX idx_metrics_name ON performance_metrics(metric_name);
CREATE INDEX idx_metrics_created ON performance_metrics(created_at DESC);
CREATE INDEX idx_metrics_session ON performance_metrics(session_id);

-- Create views for common queries

-- Recent conversations view
CREATE VIEW IF NOT EXISTS recent_conversations AS
SELECT 
    ch.id,
    ch.session_id,
    us.user_id,
    ch.user_message,
    ch.agent_response,
    ch.intent,
    ch.confidence,
    ch.response_time_ms,
    ch.token_count,
    ch.created_at
FROM conversation_history ch
JOIN user_sessions us ON ch.session_id = us.session_id
WHERE ch.created_at >= datetime('now', '-7 days')
ORDER BY ch.created_at DESC;

-- Active sessions view
CREATE VIEW IF NOT EXISTS active_sessions AS
SELECT 
    session_id,
    user_id,
    created_at,
    last_activity,
    ROUND((julianday('now') - julianday(last_activity)) * 24 * 60, 2) AS minutes_inactive
FROM user_sessions
WHERE is_active = 1
AND last_activity >= datetime('now', '-1 hour');

-- Cache hit rate view
CREATE VIEW IF NOT EXISTS cache_performance AS
SELECT 
    search_type,
    COUNT(*) as total_entries,
    SUM(access_count) as total_accesses,
    AVG(access_count) as avg_access_per_entry,
    COUNT(CASE WHEN expires_at > datetime('now') THEN 1 END) as valid_entries
FROM search_cache
GROUP BY search_type;
