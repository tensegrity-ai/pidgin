"""DuckDB schema definitions leveraging advanced types."""

# Event sourcing schema
EVENT_SCHEMA = """
-- Events table as source of truth
CREATE TABLE IF NOT EXISTS events (
    event_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT now(),
    event_type TEXT NOT NULL,
    conversation_id TEXT,
    experiment_id TEXT,
    event_data JSON,
    -- Date for partitioning (will be populated via trigger or manually)
    event_date DATE DEFAULT CAST(now() AS DATE),
    -- Sequence number for ordering events
    sequence INTEGER
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_conversation ON events(conversation_id);
CREATE INDEX IF NOT EXISTS idx_events_experiment ON events(experiment_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);
"""

# Experiments schema with native types
EXPERIMENTS_SCHEMA = """
-- Experiments table
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'created',
    
    -- Configuration as JSON for now (STRUCT syntax issues)
    config JSON,
    
    -- Progress tracking
    total_conversations INTEGER DEFAULT 0,
    completed_conversations INTEGER DEFAULT 0,
    failed_conversations INTEGER DEFAULT 0,
    
    -- Metadata as JSON for flexibility
    metadata JSON
);

-- Index for status queries
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
"""

# Conversations schema with rich types
CONVERSATIONS_SCHEMA = """
-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'created',
    
    -- Agent configuration
    agent_a_model TEXT,
    agent_a_provider TEXT,
    agent_a_temperature DOUBLE,
    agent_a_chosen_name TEXT,
    agent_b_model TEXT,
    agent_b_provider TEXT,
    agent_b_temperature DOUBLE,
    agent_b_chosen_name TEXT,
    
    -- Conversation settings
    initial_prompt TEXT,
    max_turns INTEGER,
    first_speaker TEXT DEFAULT 'agent_a',
    
    -- Final metrics
    total_turns INTEGER DEFAULT 0,
    final_convergence_score DOUBLE,
    convergence_reason TEXT,
    duration_ms INTEGER,
    
    -- Error information if failed
    error_message TEXT,
    error_type TEXT,
    error_timestamp TIMESTAMP,
    
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);

-- Indexes for queries
CREATE INDEX IF NOT EXISTS idx_conversations_experiment ON conversations(experiment_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
"""

# Turn metrics with MAP types for word frequencies
TURN_METRICS_SCHEMA = """
-- Turn metrics with JSON for complex types
CREATE TABLE IF NOT EXISTS turn_metrics (
    conversation_id TEXT,
    turn_number INTEGER,
    timestamp TIMESTAMP DEFAULT now(),
    
    -- Core convergence metrics
    convergence_score DOUBLE,
    vocabulary_overlap DOUBLE,
    structural_similarity DOUBLE,
    topic_similarity DOUBLE,
    style_match DOUBLE,
    
    -- Word frequencies as JSON (MAP syntax issues)
    word_frequencies_a JSON,
    word_frequencies_b JSON,
    shared_vocabulary JSON,
    
    -- Message metrics
    message_a_length INTEGER,
    message_a_word_count INTEGER,
    message_a_unique_words INTEGER,
    message_a_type_token_ratio DOUBLE,
    message_a_avg_word_length DOUBLE,
    message_a_response_time_ms INTEGER,
    
    message_b_length INTEGER,
    message_b_word_count INTEGER,
    message_b_unique_words INTEGER,
    message_b_type_token_ratio DOUBLE,
    message_b_avg_word_length DOUBLE,
    message_b_response_time_ms INTEGER,
    
    -- Timing information
    turn_start_time TIMESTAMP,
    turn_end_time TIMESTAMP,
    duration_ms INTEGER,
    
    -- Extended metrics as JSON
    extended_metrics JSON,
    
    PRIMARY KEY (conversation_id, turn_number),
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
);

-- Indexes for analytics
CREATE INDEX IF NOT EXISTS idx_turn_metrics_conversation ON turn_metrics(conversation_id);
CREATE INDEX IF NOT EXISTS idx_turn_metrics_convergence ON turn_metrics(convergence_score);
"""

# Messages table for full-text search
MESSAGES_SCHEMA = """
-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    conversation_id TEXT,
    turn_number INTEGER,
    agent_id TEXT,
    content TEXT,
    timestamp TIMESTAMP DEFAULT now(),
    
    -- Token information
    token_count INTEGER,
    model_reported_tokens INTEGER,
    
    PRIMARY KEY (conversation_id, turn_number, agent_id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
);

-- Full-text index (if supported by DuckDB version)
-- CREATE FULLTEXT INDEX IF NOT EXISTS idx_messages_content ON messages(content);
"""

# Token usage tracking
TOKEN_USAGE_SCHEMA = """
-- Token usage for cost tracking
CREATE TABLE IF NOT EXISTS token_usage (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT now(),
    conversation_id TEXT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    
    -- Usage details
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    
    -- Rate limit info
    requests_per_minute INTEGER,
    tokens_per_minute INTEGER,
    current_rpm_usage DOUBLE,
    current_tpm_usage DOUBLE,
    
    -- Cost tracking (in cents)
    prompt_cost DOUBLE,
    completion_cost DOUBLE,
    total_cost DOUBLE
);

-- Indexes for aggregation
CREATE INDEX IF NOT EXISTS idx_token_usage_provider ON token_usage(provider);
CREATE INDEX IF NOT EXISTS idx_token_usage_timestamp ON token_usage(timestamp);
"""

# Materialized views for dashboards
MATERIALIZED_VIEWS = """
-- Real-time experiment dashboard
CREATE OR REPLACE VIEW experiment_dashboard AS
SELECT 
    e.experiment_id,
    e.name,
    e.status,
    e.created_at,
    e.total_conversations as total_convs,
    e.completed_conversations as completed,
    e.failed_conversations as failed,
    
    -- Progress percentage
    CASE 
        WHEN e.total_conversations > 0 
        THEN e.completed_conversations * 100.0 / e.total_conversations 
        ELSE 0 
    END as progress_pct,
    
    -- Aggregate metrics from conversations
    COUNT(DISTINCT c.conversation_id) as actual_convs,
    AVG(c.final_convergence_score) as avg_convergence,
    MEDIAN(c.final_convergence_score) as median_convergence,
    STDDEV(c.final_convergence_score) as stddev_convergence,
    
    -- Duration stats
    AVG(c.duration_ms) / 1000.0 as avg_duration_sec,
    SUM(c.total_turns) as total_turns,
    
    -- Token usage
    COALESCE(SUM(tu.total_tokens), 0) as total_tokens,
    COALESCE(SUM(tu.total_cost), 0) / 100.0 as total_cost_usd
    
FROM experiments e
LEFT JOIN conversations c ON e.experiment_id = c.experiment_id
LEFT JOIN (
    SELECT conversation_id, 
           SUM(total_tokens) as total_tokens,
           SUM(total_cost) as total_cost
    FROM token_usage
    GROUP BY conversation_id
) tu ON c.conversation_id = tu.conversation_id
GROUP BY e.experiment_id, e.name, e.status, e.created_at, 
         e.total_conversations, e.completed_conversations, 
         e.failed_conversations;

-- Convergence trends view
CREATE OR REPLACE VIEW convergence_trends AS
SELECT 
    tm.conversation_id,
    tm.turn_number,
    tm.convergence_score,
    
    -- Rolling averages
    AVG(tm.convergence_score) OVER (
        PARTITION BY tm.conversation_id 
        ORDER BY tm.turn_number 
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) as rolling_avg_5,
    
    AVG(tm.convergence_score) OVER (
        PARTITION BY tm.conversation_id 
        ORDER BY tm.turn_number 
        ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ) as rolling_avg_10,
    
    -- Rate of change
    tm.convergence_score - LAG(tm.convergence_score, 1) OVER (
        PARTITION BY tm.conversation_id ORDER BY tm.turn_number
    ) as convergence_delta,
    
    -- Message length trends
    tm.message_a_length as msg_length_a,
    tm.message_b_length as msg_length_b
    
FROM turn_metrics tm;

-- Simple vocabulary analysis view
CREATE OR REPLACE VIEW vocabulary_analysis AS
SELECT 
    conversation_id,
    turn_number,
    message_a_unique_words as vocab_size_a,
    message_b_unique_words as vocab_size_b,
    message_a_unique_words + message_b_unique_words as total_vocab_size
FROM turn_metrics;
"""

# Helper functions for schema creation
def get_all_schemas():
    """Get all schema definitions in order."""
    return [
        EVENT_SCHEMA,
        EXPERIMENTS_SCHEMA,
        CONVERSATIONS_SCHEMA,
        TURN_METRICS_SCHEMA,
        MESSAGES_SCHEMA,
        TOKEN_USAGE_SCHEMA
        # MATERIALIZED_VIEWS removed - views can be created manually when needed
    ]

def get_drop_all_sql():
    """Get SQL to drop all tables (for clean migrations)."""
    return """
    DROP VIEW IF EXISTS vocabulary_analysis CASCADE;
    DROP VIEW IF EXISTS convergence_trends CASCADE;
    DROP VIEW IF EXISTS experiment_dashboard CASCADE;
    DROP TABLE IF EXISTS token_usage CASCADE;
    DROP TABLE IF EXISTS messages CASCADE;
    DROP TABLE IF EXISTS turn_metrics CASCADE;
    DROP TABLE IF EXISTS conversations CASCADE;
    DROP TABLE IF EXISTS experiments CASCADE;
    DROP TABLE IF EXISTS events CASCADE;
    """