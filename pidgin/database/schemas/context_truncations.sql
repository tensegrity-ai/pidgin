-- Track when context truncation occurs during conversations
CREATE TABLE IF NOT EXISTS context_truncations (
    conversation_id TEXT NOT NULL,
    experiment_id TEXT,
    agent_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    messages_dropped INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (conversation_id, agent_id, turn_number)
);

-- Indexes for truncation analysis
CREATE INDEX IF NOT EXISTS idx_truncations_conversation ON context_truncations(conversation_id);
CREATE INDEX IF NOT EXISTS idx_truncations_experiment ON context_truncations(experiment_id);