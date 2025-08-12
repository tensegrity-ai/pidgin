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

    -- Final metrics
    total_turns INTEGER DEFAULT 0,
    final_convergence_score DOUBLE,
    convergence_reason TEXT,
    duration_ms INTEGER,

    -- Error information if failed
    error_message TEXT,
    error_type TEXT,
    error_timestamp TIMESTAMP,

    -- Context truncation flag
    had_truncation BOOLEAN DEFAULT FALSE

    -- DuckDB limitation: Removing foreign keys due to UPDATE issues
    -- See: https://github.com/duckdb/duckdb/issues/10574
    -- FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);

-- Indexes for queries
CREATE INDEX IF NOT EXISTS idx_conversations_experiment ON conversations(experiment_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_started_at ON conversations(started_at);
CREATE INDEX IF NOT EXISTS idx_conversations_exp_status ON conversations(experiment_id, status);