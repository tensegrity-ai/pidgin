"""DuckDB schema definitions leveraging advanced types."""

# Optimized wide-table schema for conversation turns
CONVERSATION_TURNS_SCHEMA = """
-- Optimized DuckDB Schema for Pidgin Conversation Metrics
-- Designed for 150+ metrics with wide-table optimization

-- Main conversation turns table
CREATE TABLE IF NOT EXISTS conversation_turns (
    -- Primary identifiers (12 bytes)
    experiment_id VARCHAR NOT NULL,
    conversation_id VARCHAR NOT NULL,
    turn_number SMALLINT NOT NULL,

    -- Temporal (8 bytes)
    timestamp TIMESTAMP NOT NULL,

    -- Model and experimental context (variable, ~100 bytes)
    agent_a_model VARCHAR NOT NULL,
    agent_b_model VARCHAR NOT NULL,
    awareness_a VARCHAR,  -- 'none', 'basic', 'research', or YAML path
    awareness_b VARCHAR,
    temperature_a DOUBLE,
    temperature_b DOUBLE,
    initial_prompt TEXT,

    -- Message content and hashes (variable, ~1-2KB typical)
    agent_a_message TEXT,
    agent_b_message TEXT,
    a_message_hash VARCHAR(64),  -- SHA256 for deduplication
    b_message_hash VARCHAR(64),

    -- Token usage for cost tracking (16 bytes)
    a_prompt_tokens INTEGER,
    a_completion_tokens INTEGER,
    b_prompt_tokens INTEGER,
    b_completion_tokens INTEGER,

    -- ========== AGENT A METRICS ========== --

    -- Basic text metrics (22 bytes)
    a_message_length INTEGER NOT NULL DEFAULT 0,
    a_character_count SMALLINT NOT NULL DEFAULT 0,
    a_word_count SMALLINT NOT NULL DEFAULT 0,
    a_sentence_count TINYINT NOT NULL DEFAULT 0,
    a_paragraph_count TINYINT NOT NULL DEFAULT 0,
    a_avg_sentence_length DOUBLE NOT NULL DEFAULT 0.0,

    -- Lexical diversity (36 bytes)
    a_vocabulary_size SMALLINT NOT NULL DEFAULT 0,
    a_unique_words SMALLINT NOT NULL DEFAULT 0,
    a_ttr DOUBLE NOT NULL DEFAULT 0.0,  -- Type-token ratio
    a_hapax_ratio DOUBLE NOT NULL DEFAULT 0.0,  -- Words appearing once
    a_ldi DOUBLE NOT NULL DEFAULT 0.0,  -- Lexical diversity index
    a_repeated_bigrams SMALLINT NOT NULL DEFAULT 0,
    a_repeated_trigrams SMALLINT NOT NULL DEFAULT 0,
    a_self_repetition DOUBLE NOT NULL DEFAULT 0.0,

    -- Information theory (32 bytes)
    a_word_entropy DOUBLE NOT NULL DEFAULT 0.0,
    a_character_entropy DOUBLE NOT NULL DEFAULT 0.0,
    a_bigram_entropy DOUBLE NOT NULL DEFAULT 0.0,
    a_compression_ratio DOUBLE NOT NULL DEFAULT 0.0,

    -- Symbol & punctuation (9 bytes + 8 for density)
    a_symbol_density DOUBLE NOT NULL DEFAULT 0.0,
    a_emoji_count TINYINT NOT NULL DEFAULT 0,
    a_arrow_count TINYINT NOT NULL DEFAULT 0,
    a_math_symbol_count TINYINT NOT NULL DEFAULT 0,
    a_punctuation_diversity TINYINT NOT NULL DEFAULT 0,
    a_special_char_count SMALLINT NOT NULL DEFAULT 0,
    a_number_count TINYINT NOT NULL DEFAULT 0,
    a_proper_noun_count TINYINT NOT NULL DEFAULT 0,

    -- Linguistic patterns (8 bytes + 48 for doubles)
    a_question_count TINYINT NOT NULL DEFAULT 0,
    a_exclamation_count TINYINT NOT NULL DEFAULT 0,
    a_question_density DOUBLE NOT NULL DEFAULT 0.0,
    a_hedge_density DOUBLE NOT NULL DEFAULT 0.0,
    a_hedge_words TINYINT NOT NULL DEFAULT 0,
    a_agreement_markers TINYINT NOT NULL DEFAULT 0,
    a_disagreement_markers TINYINT NOT NULL DEFAULT 0,
    a_politeness_markers TINYINT NOT NULL DEFAULT 0,
    a_certainty_words TINYINT NOT NULL DEFAULT 0,
    a_tentative_words TINYINT NOT NULL DEFAULT 0,
    a_formality_score DOUBLE NOT NULL DEFAULT 0.0,
    a_emotional_intensity DOUBLE NOT NULL DEFAULT 0.0,

    -- Pronoun usage (12 bytes)
    a_first_person_singular TINYINT NOT NULL DEFAULT 0,
    a_first_person_plural TINYINT NOT NULL DEFAULT 0,
    a_second_person TINYINT NOT NULL DEFAULT 0,
    a_third_person TINYINT NOT NULL DEFAULT 0,
    a_passive_voice TINYINT NOT NULL DEFAULT 0,
    a_active_voice TINYINT NOT NULL DEFAULT 0,

    -- Advanced linguistic (56 bytes)
    a_syntactic_complexity DOUBLE NOT NULL DEFAULT 0.0,
    a_semantic_density DOUBLE NOT NULL DEFAULT 0.0,
    a_coherence_score DOUBLE NOT NULL DEFAULT 0.0,
    a_readability_score DOUBLE NOT NULL DEFAULT 0.0,
    a_cognitive_load DOUBLE NOT NULL DEFAULT 0.0,
    a_information_density DOUBLE NOT NULL DEFAULT 0.0,
    a_discourse_markers TINYINT NOT NULL DEFAULT 0,

    -- Research-specific patterns (10 bytes)
    a_gratitude_markers TINYINT NOT NULL DEFAULT 0,
    a_existential_language TINYINT NOT NULL DEFAULT 0,
    a_compression_indicators TINYINT NOT NULL DEFAULT 0,
    a_novel_symbols TINYINT NOT NULL DEFAULT 0,
    a_meta_commentary TINYINT NOT NULL DEFAULT 0,

    -- Repetition and novelty (8 bytes)
    a_turn_repetition DOUBLE NOT NULL DEFAULT 0.0,
    a_new_words INTEGER NOT NULL DEFAULT 0,

    -- ========== AGENT B METRICS ========== --
    -- (Identical structure to Agent A)

    b_message_length INTEGER NOT NULL DEFAULT 0,
    b_character_count SMALLINT NOT NULL DEFAULT 0,
    b_word_count SMALLINT NOT NULL DEFAULT 0,
    b_sentence_count TINYINT NOT NULL DEFAULT 0,
    b_paragraph_count TINYINT NOT NULL DEFAULT 0,
    b_avg_sentence_length DOUBLE NOT NULL DEFAULT 0.0,

    b_vocabulary_size SMALLINT NOT NULL DEFAULT 0,
    b_unique_words SMALLINT NOT NULL DEFAULT 0,
    b_ttr DOUBLE NOT NULL DEFAULT 0.0,
    b_hapax_ratio DOUBLE NOT NULL DEFAULT 0.0,
    b_ldi DOUBLE NOT NULL DEFAULT 0.0,
    b_repeated_bigrams SMALLINT NOT NULL DEFAULT 0,
    b_repeated_trigrams SMALLINT NOT NULL DEFAULT 0,
    b_self_repetition DOUBLE NOT NULL DEFAULT 0.0,

    b_word_entropy DOUBLE NOT NULL DEFAULT 0.0,
    b_character_entropy DOUBLE NOT NULL DEFAULT 0.0,
    b_bigram_entropy DOUBLE NOT NULL DEFAULT 0.0,
    b_compression_ratio DOUBLE NOT NULL DEFAULT 0.0,

    b_symbol_density DOUBLE NOT NULL DEFAULT 0.0,
    b_emoji_count TINYINT NOT NULL DEFAULT 0,
    b_arrow_count TINYINT NOT NULL DEFAULT 0,
    b_math_symbol_count TINYINT NOT NULL DEFAULT 0,
    b_punctuation_diversity TINYINT NOT NULL DEFAULT 0,
    b_special_char_count SMALLINT NOT NULL DEFAULT 0,
    b_number_count TINYINT NOT NULL DEFAULT 0,
    b_proper_noun_count TINYINT NOT NULL DEFAULT 0,

    b_question_count TINYINT NOT NULL DEFAULT 0,
    b_exclamation_count TINYINT NOT NULL DEFAULT 0,
    b_question_density DOUBLE NOT NULL DEFAULT 0.0,
    b_hedge_density DOUBLE NOT NULL DEFAULT 0.0,
    b_hedge_words TINYINT NOT NULL DEFAULT 0,
    b_agreement_markers TINYINT NOT NULL DEFAULT 0,
    b_disagreement_markers TINYINT NOT NULL DEFAULT 0,
    b_politeness_markers TINYINT NOT NULL DEFAULT 0,
    b_certainty_words TINYINT NOT NULL DEFAULT 0,
    b_tentative_words TINYINT NOT NULL DEFAULT 0,
    b_formality_score DOUBLE NOT NULL DEFAULT 0.0,
    b_emotional_intensity DOUBLE NOT NULL DEFAULT 0.0,

    b_first_person_singular TINYINT NOT NULL DEFAULT 0,
    b_first_person_plural TINYINT NOT NULL DEFAULT 0,
    b_second_person TINYINT NOT NULL DEFAULT 0,
    b_third_person TINYINT NOT NULL DEFAULT 0,
    b_passive_voice TINYINT NOT NULL DEFAULT 0,
    b_active_voice TINYINT NOT NULL DEFAULT 0,

    b_syntactic_complexity DOUBLE NOT NULL DEFAULT 0.0,
    b_semantic_density DOUBLE NOT NULL DEFAULT 0.0,
    b_coherence_score DOUBLE NOT NULL DEFAULT 0.0,
    b_readability_score DOUBLE NOT NULL DEFAULT 0.0,
    b_cognitive_load DOUBLE NOT NULL DEFAULT 0.0,
    b_information_density DOUBLE NOT NULL DEFAULT 0.0,
    b_discourse_markers TINYINT NOT NULL DEFAULT 0,

    b_gratitude_markers TINYINT NOT NULL DEFAULT 0,
    b_existential_language TINYINT NOT NULL DEFAULT 0,
    b_compression_indicators TINYINT NOT NULL DEFAULT 0,
    b_novel_symbols TINYINT NOT NULL DEFAULT 0,
    b_meta_commentary TINYINT NOT NULL DEFAULT 0,

    b_turn_repetition DOUBLE NOT NULL DEFAULT 0.0,
    b_new_words INTEGER NOT NULL DEFAULT 0,

    -- ========== CONVERGENCE METRICS ========== --
    -- (Measured between agents, 160 bytes)

    vocabulary_overlap DOUBLE NOT NULL DEFAULT 0.0,
    length_convergence DOUBLE NOT NULL DEFAULT 0.0,
    style_similarity DOUBLE NOT NULL DEFAULT 0.0,
    structural_similarity DOUBLE NOT NULL DEFAULT 0.0,
    semantic_similarity DOUBLE NOT NULL DEFAULT 0.0,
    mimicry_score_a_to_b DOUBLE NOT NULL DEFAULT 0.0,
    mimicry_score_b_to_a DOUBLE NOT NULL DEFAULT 0.0,
    sentiment_convergence DOUBLE NOT NULL DEFAULT 0.0,
    formality_convergence DOUBLE NOT NULL DEFAULT 0.0,
    rhythm_convergence DOUBLE NOT NULL DEFAULT 0.0,
    overall_convergence DOUBLE NOT NULL DEFAULT 0.0,
    convergence_velocity DOUBLE NOT NULL DEFAULT 0.0,
    turn_taking_balance DOUBLE NOT NULL DEFAULT 0.0,
    topic_consistency DOUBLE NOT NULL DEFAULT 0.0,
    phrase_alignment DOUBLE NOT NULL DEFAULT 0.0,
    syntactic_convergence DOUBLE NOT NULL DEFAULT 0.0,
    lexical_entrainment DOUBLE NOT NULL DEFAULT 0.0,
    prosodic_alignment DOUBLE NOT NULL DEFAULT 0.0,
    discourse_coherence DOUBLE NOT NULL DEFAULT 0.0,
    cumulative_convergence DOUBLE NOT NULL DEFAULT 0.0,

    -- ========== TEMPORAL & META ========== --
    -- (64 bytes)

    response_time_a DOUBLE,  -- Can be NULL if not measured
    response_time_b DOUBLE,
    processing_time_ms INTEGER,
    api_latency_a DOUBLE,
    api_latency_b DOUBLE,
    turn_duration_ms INTEGER,
    conversation_velocity DOUBLE NOT NULL DEFAULT 0.0,
    adaptation_rate DOUBLE NOT NULL DEFAULT 0.0,

    -- Primary key
    PRIMARY KEY (experiment_id, conversation_id, turn_number)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_conversation_turns_timestamp ON conversation_turns(timestamp);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_experiment_timestamp ON conversation_turns(experiment_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_convergence ON conversation_turns(overall_convergence);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_models ON conversation_turns(agent_a_model, agent_b_model);
"""

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
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_exp_conv ON events(experiment_id, conversation_id);
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
"""

# Turn metrics with comprehensive columns
TURN_METRICS_SCHEMA = """
-- Turn metrics with all ~80 metrics as columns
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

    -- Additional convergence metrics
    cumulative_overlap DOUBLE,
    cross_repetition DOUBLE,
    mimicry_a_to_b DOUBLE,
    mimicry_b_to_a DOUBLE,
    mutual_mimicry DOUBLE,

    -- Message metrics for Agent A
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

    -- Message metrics for Agent B
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

    -- Word frequencies as JSON (variable size data)
    word_frequencies_a JSON,
    word_frequencies_b JSON,
    shared_vocabulary JSON,

    -- Timing information
    turn_start_time TIMESTAMP,
    turn_end_time TIMESTAMP,
    duration_ms INTEGER,

    PRIMARY KEY (conversation_id, turn_number)
    -- DuckDB limitation: Removing foreign keys due to UPDATE issues
    -- FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
);

-- Indexes for analytics
CREATE INDEX IF NOT EXISTS idx_turn_metrics_conversation ON turn_metrics(conversation_id);
CREATE INDEX IF NOT EXISTS idx_turn_metrics_convergence ON turn_metrics(convergence_score);
CREATE INDEX IF NOT EXISTS idx_turn_metrics_turn_number ON turn_metrics(turn_number);
CREATE INDEX IF NOT EXISTS idx_turn_metrics_conv_turn ON turn_metrics(conversation_id, turn_number);
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

# Context truncation tracking
CONTEXT_TRUNCATIONS_SCHEMA = """
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
        CONVERSATION_TURNS_SCHEMA,  # New wide-table schema
        MESSAGES_SCHEMA,
        TOKEN_USAGE_SCHEMA,
        CONTEXT_TRUNCATIONS_SCHEMA,
        # MATERIALIZED_VIEWS removed - views can be created manually when needed
    ]


def get_drop_all_sql():
    """Get SQL to drop all tables (for clean migrations)."""
    return """
    DROP VIEW IF EXISTS vocabulary_analysis CASCADE;
    DROP VIEW IF EXISTS convergence_trends CASCADE;
    DROP VIEW IF EXISTS experiment_dashboard CASCADE;
    DROP TABLE IF EXISTS context_truncations CASCADE;
    DROP TABLE IF EXISTS token_usage CASCADE;
    DROP TABLE IF EXISTS messages CASCADE;
    DROP TABLE IF EXISTS turn_metrics CASCADE;
    DROP TABLE IF EXISTS conversation_turns CASCADE;
    DROP TABLE IF EXISTS conversations CASCADE;
    DROP TABLE IF EXISTS experiments CASCADE;
    DROP TABLE IF EXISTS events CASCADE;
    """
