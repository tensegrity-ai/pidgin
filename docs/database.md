# Pidgin Database Documentation

## Overview

Pidgin uses DuckDB as its analytical database, storing all conversation data, metrics, and events in a single file at `./pidgin_output/experiments.duckdb`. The database is automatically created on first use and employs an event-sourcing architecture for complete auditability.

## Why DuckDB?

- **Analytical Optimized**: Columnar storage perfect for metrics analysis
- **Zero Configuration**: Single file, no server required
- **Fast Queries**: 10-100x faster than SQLite for analytical workloads
- **Rich SQL**: Window functions, CTEs, and advanced analytics
- **Pandas Integration**: Direct DataFrame support for data science

## Database Schema

### Core Tables

#### 1. `events` - Event Sourcing Table
The foundation of our event-sourcing architecture. Every significant action creates an event.

```sql
CREATE TABLE events (
    event_id UUID PRIMARY KEY,
    timestamp TIMESTAMP,
    event_type TEXT NOT NULL,         -- e.g., 'ConversationStartEvent', 'TurnCompleteEvent'
    conversation_id TEXT,
    experiment_id TEXT,
    event_data JSON,                  -- Full event payload
    event_date DATE DEFAULT CAST(now() AS DATE),  -- For partitioning
    sequence INTEGER                  -- Sequence number for ordering events
)
```

#### 2. `experiments` - Experiment Metadata
Tracks batch runs of multiple conversations.

```sql
CREATE TABLE experiments (
    experiment_id TEXT PRIMARY KEY,   -- e.g., 'exp_a1b2c3d4'
    name TEXT,                        -- Human-readable name
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'created',    -- 'created', 'running', 'completed', 'failed'
    config JSON,                      -- Full experiment configuration
    total_conversations INTEGER,
    completed_conversations INTEGER,
    failed_conversations INTEGER,
    metadata JSON
)
```

#### 3. `conversations` - Individual Conversations
Each AI-to-AI conversation within an experiment.

```sql
CREATE TABLE conversations (
    conversation_id TEXT PRIMARY KEY,  -- e.g., 'conv_e5f6g7h8'
    experiment_id TEXT NOT NULL,
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'created',
    
    -- Agent configuration
    agent_a_model TEXT,               -- e.g., 'claude-3-5-sonnet'
    agent_a_provider TEXT,            -- e.g., 'anthropic'
    agent_a_temperature DOUBLE,
    agent_a_chosen_name TEXT,         -- Name agent chose for itself
    
    agent_b_model TEXT,
    agent_b_provider TEXT,
    agent_b_temperature DOUBLE,
    agent_b_chosen_name TEXT,
    
    -- Conversation settings
    initial_prompt TEXT,
    max_turns INTEGER,
    
    -- Results
    total_turns INTEGER DEFAULT 0,
    final_convergence_score DOUBLE,
    convergence_reason TEXT,          -- Why conversation ended
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
)
```

#### 4. `conversation_turns` - Wide-Table Metrics (New)
Optimized wide-table format with 150+ columns for efficient analytical queries. This replaces the normalized turn_metrics table.

```sql
CREATE TABLE conversation_turns (
    -- Primary identifiers
    experiment_id VARCHAR NOT NULL,
    conversation_id VARCHAR NOT NULL,
    turn_number SMALLINT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- Model context
    agent_a_model VARCHAR NOT NULL,
    agent_b_model VARCHAR NOT NULL,
    awareness_a VARCHAR,
    awareness_b VARCHAR,
    temperature_a DOUBLE,
    temperature_b DOUBLE,
    
    -- Message content
    agent_a_message TEXT,
    agent_b_message TEXT,
    
    -- 60+ metrics per agent (prefixed with a_ or b_)
    a_message_length INTEGER,
    a_word_count SMALLINT,
    a_vocabulary_size SMALLINT,
    -- ... many more
    
    -- 30+ convergence metrics (no prefix)
    vocabulary_overlap DOUBLE,
    structural_similarity DOUBLE,
    overall_convergence DOUBLE,
    -- ... many more
    
    PRIMARY KEY (conversation_id, turn_number)
)
```

Key benefits of wide-table format:
- Single row per turn (no joins needed)
- Optimized for DuckDB's columnar storage
- 10-100x faster analytical queries
- All metrics pre-calculated during import

**Note on Placeholder Metrics**: Some advanced metrics are stored as placeholders (0.0 values):
- `semantic_similarity` - Requires sentence transformers
- `sentiment_convergence` - Requires sentiment analysis libraries
- `emotional_intensity` - Requires emotion lexicons
- `topic_consistency` - Requires topic modeling

These can be calculated post-hoc using the message text. See the auto-generated Jupyter notebooks for examples.

#### 5. `turn_metrics` - Legacy Per-Turn Metrics (Deprecated)
The previous normalized format. Still supported but will be removed in future versions.

```sql
CREATE TABLE turn_metrics (
    conversation_id TEXT,
    turn_number INTEGER,
    timestamp TIMESTAMP,
    
    -- Core convergence metrics
    convergence_score DOUBLE,         -- 0.0 to 1.0
    vocabulary_overlap DOUBLE,
    structural_similarity DOUBLE,
    topic_similarity DOUBLE,
    style_match DOUBLE,
    
    -- Additional convergence metrics
    cumulative_overlap DOUBLE,
    cross_repetition DOUBLE,
    mimicry_a_to_b DOUBLE,
    mimicry_b_to_a DOUBLE,
    mutual_mimicry DOUBLE,
    
    -- Word frequencies (stored as JSON)
    word_frequencies_a JSON,          -- {"hello": 2, "world": 1, ...}
    word_frequencies_b JSON,
    shared_vocabulary JSON,
    
    -- Message metrics for agent A
    message_a_length INTEGER,
    message_a_word_count INTEGER,
    message_a_unique_words INTEGER,
    message_a_type_token_ratio DOUBLE,
    message_a_avg_word_length DOUBLE,
    message_a_response_time_ms INTEGER,
    message_a_sentence_count INTEGER,
    message_a_paragraph_count INTEGER,
    message_a_avg_sentence_length DOUBLE,
    message_a_question_count INTEGER,
    message_a_exclamation_count INTEGER,
    message_a_special_symbol_count INTEGER,
    message_a_number_count INTEGER,
    message_a_proper_noun_count INTEGER,
    message_a_entropy DOUBLE,
    message_a_compression_ratio DOUBLE,
    message_a_lexical_diversity DOUBLE,
    message_a_punctuation_diversity DOUBLE,
    message_a_self_repetition DOUBLE,
    message_a_turn_repetition DOUBLE,
    message_a_formality_score DOUBLE,
    message_a_starts_with_ack BOOLEAN,
    message_a_new_words INTEGER,
    
    -- Linguistic markers for Agent A
    message_a_hedge_words INTEGER,
    message_a_agreement_markers INTEGER,
    message_a_disagreement_markers INTEGER,
    message_a_politeness_markers INTEGER,
    message_a_first_person_singular INTEGER,
    message_a_first_person_plural INTEGER,
    message_a_second_person INTEGER,
    
    -- Message metrics for agent B (same fields as Agent A)
    message_b_length INTEGER,
    message_b_word_count INTEGER,
    message_b_unique_words INTEGER,
    message_b_type_token_ratio DOUBLE,
    message_b_avg_word_length DOUBLE,
    message_b_response_time_ms INTEGER,
    message_b_sentence_count INTEGER,
    message_b_paragraph_count INTEGER,
    message_b_avg_sentence_length DOUBLE,
    message_b_question_count INTEGER,
    message_b_exclamation_count INTEGER,
    message_b_special_symbol_count INTEGER,
    message_b_number_count INTEGER,
    message_b_proper_noun_count INTEGER,
    message_b_entropy DOUBLE,
    message_b_compression_ratio DOUBLE,
    message_b_lexical_diversity DOUBLE,
    message_b_punctuation_diversity DOUBLE,
    message_b_self_repetition DOUBLE,
    message_b_turn_repetition DOUBLE,
    message_b_formality_score DOUBLE,
    message_b_starts_with_ack BOOLEAN,
    message_b_new_words INTEGER,
    
    -- Linguistic markers for Agent B
    message_b_hedge_words INTEGER,
    message_b_agreement_markers INTEGER,
    message_b_disagreement_markers INTEGER,
    message_b_politeness_markers INTEGER,
    message_b_first_person_singular INTEGER,
    message_b_first_person_plural INTEGER,
    message_b_second_person INTEGER,
    
    -- Timing information
    turn_start_time TIMESTAMP,
    turn_end_time TIMESTAMP,
    duration_ms INTEGER,
    
    PRIMARY KEY (conversation_id, turn_number)
    -- DuckDB limitation: Removing foreign keys due to UPDATE issues
    -- FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
)
```

#### 5. `messages` - Raw Message Content
Stores actual message text for full-text search and analysis.

```sql
CREATE TABLE messages (
    conversation_id TEXT,
    turn_number INTEGER,
    agent_id TEXT,                    -- 'agent_a' or 'agent_b'
    content TEXT,                     -- Raw message text
    timestamp TIMESTAMP,
    token_count INTEGER,              -- Estimated tokens
    model_reported_tokens INTEGER,    -- Actual tokens from API
    
    PRIMARY KEY (conversation_id, turn_number, agent_id)
)
```

#### 6. `token_usage` - Cost Tracking
Tracks API token usage and costs.

```sql
CREATE TABLE token_usage (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP,
    conversation_id TEXT,
    provider TEXT,                    -- 'anthropic', 'openai', etc.
    model TEXT,
    
    -- Token counts
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    
    -- Rate limit tracking
    tokens_per_minute INTEGER,
    current_tpm_usage DOUBLE,
    
    -- Cost in cents
    prompt_cost DOUBLE,
    completion_cost DOUBLE,
    total_cost DOUBLE
)
```

### Views for Analysis

#### `experiment_dashboard`
Aggregated view for experiment monitoring.

```sql
CREATE VIEW experiment_dashboard AS
SELECT 
    e.*,
    COUNT(DISTINCT c.conversation_id) as actual_conversations,
    AVG(c.final_convergence_score) as avg_convergence,
    SUM(tu.total_tokens) as total_tokens,
    SUM(tu.total_cost) / 100.0 as total_cost_usd
FROM experiments e
LEFT JOIN conversations c ON e.experiment_id = c.experiment_id
LEFT JOIN (SELECT conversation_id, SUM(total_tokens) as total_tokens, 
           SUM(total_cost) as total_cost
           FROM token_usage GROUP BY conversation_id) tu
    ON c.conversation_id = tu.conversation_id
GROUP BY e.experiment_id;
```

#### `convergence_trends`
Time-series analysis of convergence patterns.

```sql
CREATE VIEW convergence_trends AS
SELECT 
    conversation_id,
    turn_number,
    convergence_score,
    AVG(convergence_score) OVER (
        PARTITION BY conversation_id 
        ORDER BY turn_number 
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) as rolling_avg_5
FROM turn_metrics;
```

## Common Queries

### Get experiment summary
```sql
SELECT * FROM experiment_dashboard 
WHERE experiment_id = 'exp_abc123';
```

### Find high-convergence moments
```sql
SELECT conversation_id, turn_number, convergence_score
FROM turn_metrics
WHERE convergence_score > 0.8
ORDER BY convergence_score DESC;
```

### Analyze vocabulary compression
```sql
SELECT 
    turn_number,
    AVG(message_a_word_count) as avg_words,
    AVG(message_a_unique_words) as avg_unique_words
FROM turn_metrics
GROUP BY turn_number
ORDER BY turn_number;
```

### Calculate experiment costs
```sql
SELECT 
    provider,
    model,
    SUM(total_tokens) as tokens,
    SUM(total_cost) / 100.0 as cost_usd
FROM token_usage
WHERE conversation_id IN (
    SELECT conversation_id FROM conversations 
    WHERE experiment_id = 'exp_abc123'
)
GROUP BY provider, model;
```

## Database Location & Access

- **Default location**: `./pidgin_output/experiments.duckdb`
- **Auto-creation**: Database and tables created automatically on first use
- **Direct access**: `duckdb ./pidgin_output/experiments.duckdb`
- **Python access**: Use DuckDB Python API directly or through the repository classes in `pidgin.database`

## Architecture Notes

1. **Event Sourcing**: All state changes flow through the `events` table, providing a complete audit trail
2. **Synchronous Operations**: Database operations are synchronous for simplicity and reliability
3. **Batch Processing**: Metrics calculations can be batched for performance
4. **JSON Flexibility**: Complex data stored as JSON for schema flexibility
5. **Repository Pattern**: Clean separation of concerns with dedicated repository classes

## Future Enhancements

- **Partitioning**: Events table partitioned by date for faster queries
- **Compression**: Automatic compression of historical data
- **External Tables**: Direct querying of JSON/Parquet files
- **Streaming Updates**: Real-time materialized view updates