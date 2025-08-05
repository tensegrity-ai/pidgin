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