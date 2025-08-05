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

    PRIMARY KEY (conversation_id, turn_number, agent_id)
    -- DuckDB limitation: Removing foreign keys due to UPDATE issues
    -- FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
);

-- Indexes for message queries
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_turn ON messages(turn_number);
CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);

-- Full-text index (if supported by DuckDB version)
-- CREATE FULLTEXT INDEX IF NOT EXISTS idx_messages_content ON messages(content);