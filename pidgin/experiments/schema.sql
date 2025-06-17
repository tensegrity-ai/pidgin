-- Pidgin Experiments Database Schema
-- SQLite database for storing AI conversation experiments and metrics

-- Experiments table: top-level experiment runs
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'created' CHECK (status IN ('created', 'running', 'completed', 'failed')),
    config JSON NOT NULL,  -- Full experiment configuration
    total_conversations INTEGER NOT NULL,
    completed_conversations INTEGER DEFAULT 0,
    failed_conversations INTEGER DEFAULT 0,
    metadata JSON  -- Additional experiment-level data
);

-- Conversations table: individual conversations within experiments
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'created' CHECK (status IN ('created', 'running', 'completed', 'failed', 'interrupted')),
    config JSON NOT NULL,  -- Conversation-specific config
    first_speaker TEXT DEFAULT 'agent_a' CHECK (first_speaker IN ('agent_a', 'agent_b')),
    agent_a_model TEXT NOT NULL,
    agent_b_model TEXT NOT NULL,
    agent_a_chosen_name TEXT,  -- If choose-names enabled
    agent_b_chosen_name TEXT,
    total_turns INTEGER DEFAULT 0,
    convergence_reason TEXT,  -- Why conversation ended
    final_convergence_score REAL,
    error_message TEXT,  -- If failed
    metadata JSON,  -- Additional conversation-level data
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);

-- Turns table: comprehensive metrics for each turn
CREATE TABLE IF NOT EXISTS turns (
    conversation_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,  -- 0-indexed
    speaker TEXT NOT NULL CHECK (speaker IN ('agent_a', 'agent_b')),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Message content (inline storage)
    message TEXT NOT NULL,
    
    -- Basic metrics
    message_length INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    sentence_count INTEGER NOT NULL,
    
    -- Lexical diversity metrics
    vocabulary_size INTEGER NOT NULL,  -- Unique words in this message
    type_token_ratio REAL NOT NULL,  -- vocabulary_size / word_count
    hapax_legomena_count INTEGER NOT NULL,  -- Words appearing once
    hapax_ratio REAL NOT NULL,  -- hapax_count / vocabulary_size
    
    -- Convergence metrics (calculated after both agents speak in a turn)
    convergence_score REAL,  -- Overall convergence score
    vocabulary_overlap REAL,  -- Jaccard similarity of vocabularies
    length_ratio REAL,  -- Ratio of message lengths
    structural_similarity REAL,  -- Sentence structure similarity
    
    -- Linguistic markers
    question_count INTEGER DEFAULT 0,
    exclamation_count INTEGER DEFAULT 0,
    hedge_count INTEGER DEFAULT 0,  -- "maybe", "perhaps", etc.
    agreement_marker_count INTEGER DEFAULT 0,  -- "yes", "agreed", etc.
    disagreement_marker_count INTEGER DEFAULT 0,  -- "no", "but", etc.
    politeness_marker_count INTEGER DEFAULT 0,  -- "please", "thank you", etc.
    
    -- Symbol usage
    emoji_count INTEGER DEFAULT 0,
    emoji_density REAL DEFAULT 0.0,  -- emojis per word
    arrow_count INTEGER DEFAULT 0,  -- →, ←, ↔, etc.
    math_symbol_count INTEGER DEFAULT 0,  -- ≈, ≡, ≠, etc.
    other_symbol_count INTEGER DEFAULT 0,  -- Other Unicode symbols
    
    -- Pronoun usage
    first_person_singular_count INTEGER DEFAULT 0,  -- I, me, my
    first_person_plural_count INTEGER DEFAULT 0,  -- we, us, our
    second_person_count INTEGER DEFAULT 0,  -- you, your
    
    -- Repetition metrics
    repeated_bigrams INTEGER DEFAULT 0,  -- From previous message
    repeated_trigrams INTEGER DEFAULT 0,
    self_repetition_score REAL DEFAULT 0.0,  -- Within same message
    cross_repetition_score REAL DEFAULT 0.0,  -- From other agent
    
    -- Information theory metrics
    word_entropy REAL,  -- Shannon entropy at word level
    character_entropy REAL,  -- Shannon entropy at character level
    perplexity REAL,  -- If we calculate it
    
    -- Sentiment and tone (if we add it later)
    sentiment_score REAL,
    formality_score REAL,
    
    -- Response characteristics
    response_time_ms INTEGER,  -- Time to generate (may be rate-limited)
    starts_with_acknowledgment BOOLEAN DEFAULT FALSE,
    ends_with_question BOOLEAN DEFAULT FALSE,
    
    -- Additional metrics as JSON for flexibility
    additional_metrics JSON,
    
    PRIMARY KEY (conversation_id, turn_number),
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
);

-- Word frequencies table: track word usage over time
CREATE TABLE IF NOT EXISTS word_frequencies (
    conversation_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    speaker TEXT NOT NULL CHECK (speaker IN ('agent_a', 'agent_b')),
    word TEXT NOT NULL,
    frequency INTEGER NOT NULL,
    is_new_word BOOLEAN DEFAULT FALSE,  -- First appearance in conversation
    PRIMARY KEY (conversation_id, turn_number, speaker, word),
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
);

-- Agent names table: track chosen names when --choose-names is enabled
CREATE TABLE IF NOT EXISTS agent_names (
    conversation_id TEXT NOT NULL,
    agent_id TEXT NOT NULL CHECK (agent_id IN ('agent_a', 'agent_b')),
    chosen_name TEXT NOT NULL,
    turn_chosen INTEGER NOT NULL,  -- When name was chosen
    name_length INTEGER NOT NULL,
    contains_numbers BOOLEAN DEFAULT FALSE,
    contains_symbols BOOLEAN DEFAULT FALSE,
    contains_spaces BOOLEAN DEFAULT FALSE,
    is_single_word BOOLEAN DEFAULT TRUE,
    starts_with_capital BOOLEAN DEFAULT FALSE,
    all_caps BOOLEAN DEFAULT FALSE,
    
    -- Let patterns emerge, don't categorize
    metadata JSON,  -- Any additional name characteristics
    
    PRIMARY KEY (conversation_id, agent_id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_conversations_experiment ON conversations(experiment_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_turns_conversation ON turns(conversation_id);
CREATE INDEX IF NOT EXISTS idx_turns_speaker ON turns(conversation_id, speaker);
CREATE INDEX IF NOT EXISTS idx_word_frequencies_conversation ON word_frequencies(conversation_id);
CREATE INDEX IF NOT EXISTS idx_agent_names_model ON conversations(agent_a_model, agent_b_model);

-- View for experiment summary
CREATE VIEW IF NOT EXISTS experiment_summary AS
SELECT 
    e.experiment_id,
    e.name,
    e.status,
    e.total_conversations,
    e.completed_conversations,
    e.failed_conversations,
    e.created_at,
    e.completed_at,
    COUNT(DISTINCT c.conversation_id) as actual_conversations,
    AVG(c.total_turns) as avg_turns,
    AVG(c.final_convergence_score) as avg_convergence
FROM experiments e
LEFT JOIN conversations c ON e.experiment_id = c.experiment_id
GROUP BY e.experiment_id;

-- View for name statistics
CREATE VIEW IF NOT EXISTS name_statistics AS
SELECT 
    c.agent_a_model as model,
    'agent_a' as role,
    n.chosen_name,
    n.name_length,
    n.contains_numbers,
    n.contains_symbols,
    COUNT(*) OVER (PARTITION BY c.agent_a_model, n.chosen_name) as name_frequency
FROM conversations c
JOIN agent_names n ON c.conversation_id = n.conversation_id AND n.agent_id = 'agent_a'
UNION ALL
SELECT 
    c.agent_b_model as model,
    'agent_b' as role,
    n.chosen_name,
    n.name_length,
    n.contains_numbers,
    n.contains_symbols,
    COUNT(*) OVER (PARTITION BY c.agent_b_model, n.chosen_name) as name_frequency
FROM conversations c
JOIN agent_names n ON c.conversation_id = n.conversation_id AND n.agent_id = 'agent_b';