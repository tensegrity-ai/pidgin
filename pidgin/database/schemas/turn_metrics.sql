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