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
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_exp_conv ON events(experiment_id, conversation_id);