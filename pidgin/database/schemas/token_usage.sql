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