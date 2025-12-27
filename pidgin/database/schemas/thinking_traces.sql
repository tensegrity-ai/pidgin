-- Thinking traces table for extended thinking/reasoning
CREATE TABLE IF NOT EXISTS thinking_traces (
    conversation_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    agent_id TEXT NOT NULL,
    thinking_content TEXT NOT NULL,
    thinking_tokens INTEGER,
    duration_ms INTEGER,
    timestamp TIMESTAMP DEFAULT now(),

    PRIMARY KEY (conversation_id, turn_number, agent_id)
);

-- Index for efficient joins with messages
CREATE INDEX IF NOT EXISTS idx_thinking_traces_lookup
ON thinking_traces (conversation_id, turn_number, agent_id);

-- Index for finding all thinking in a conversation
CREATE INDEX IF NOT EXISTS idx_thinking_traces_conversation
ON thinking_traces (conversation_id);
