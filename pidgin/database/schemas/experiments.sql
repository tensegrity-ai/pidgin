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