"""Metric names and default configuration constants."""


# Convergence metric component names
class ConvergenceComponents:
    CONTENT = "content"
    STRUCTURE = "structure"
    SENTENCES = "sentences"
    LENGTH = "length"
    PUNCTUATION = "punctuation"


# Default convergence profiles
class ConvergenceProfiles:
    BALANCED = "balanced"
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    STRICT = "strict"
    CUSTOM = "custom"


# Default convergence weights
DEFAULT_CONVERGENCE_WEIGHTS = {
    ConvergenceProfiles.BALANCED: {
        ConvergenceComponents.CONTENT: 0.4,
        ConvergenceComponents.STRUCTURE: 0.15,
        ConvergenceComponents.SENTENCES: 0.2,
        ConvergenceComponents.LENGTH: 0.15,
        ConvergenceComponents.PUNCTUATION: 0.1,
    },
    ConvergenceProfiles.STRUCTURAL: {
        ConvergenceComponents.CONTENT: 0.25,
        ConvergenceComponents.STRUCTURE: 0.35,
        ConvergenceComponents.SENTENCES: 0.2,
        ConvergenceComponents.LENGTH: 0.1,
        ConvergenceComponents.PUNCTUATION: 0.1,
    },
    ConvergenceProfiles.SEMANTIC: {
        ConvergenceComponents.CONTENT: 0.6,
        ConvergenceComponents.STRUCTURE: 0.1,
        ConvergenceComponents.SENTENCES: 0.15,
        ConvergenceComponents.LENGTH: 0.1,
        ConvergenceComponents.PUNCTUATION: 0.05,
    },
    ConvergenceProfiles.STRICT: {
        ConvergenceComponents.CONTENT: 0.5,
        ConvergenceComponents.STRUCTURE: 0.25,
        ConvergenceComponents.SENTENCES: 0.15,
        ConvergenceComponents.LENGTH: 0.05,
        ConvergenceComponents.PUNCTUATION: 0.05,
    },
}


# Metric thresholds
class MetricThresholds:
    HIGH_CONVERGENCE = 0.8
    MEDIUM_CONVERGENCE = 0.6
    LOW_CONVERGENCE = 0.4
    SYMBOL_DENSITY_HIGH = 0.1
    TTR_COLLAPSE = 0.3
    ENGAGEMENT_THRESHOLD = 0.7


# Database column names for metrics
class MetricColumns:
    # Core convergence metrics
    CONVERGENCE_SCORE = "convergence_score"
    VOCABULARY_OVERLAP = "vocabulary_overlap"
    STRUCTURAL_SIMILARITY = "structural_similarity"
    TOPIC_SIMILARITY = "topic_similarity"
    STYLE_MATCH = "style_match"

    # Additional convergence metrics
    CUMULATIVE_OVERLAP = "cumulative_overlap"
    CROSS_REPETITION = "cross_repetition"
    MIMICRY_A_TO_B = "mimicry_a_to_b"
    MIMICRY_B_TO_A = "mimicry_b_to_a"
    MUTUAL_MIMICRY = "mutual_mimicry"

    # Message metrics prefix
    MESSAGE_PREFIX_A = "message_a_"
    MESSAGE_PREFIX_B = "message_b_"

    # Common message metric suffixes
    LENGTH = "length"
    WORD_COUNT = "word_count"
    UNIQUE_WORDS = "unique_words"
    TYPE_TOKEN_RATIO = "type_token_ratio"
    AVG_WORD_LENGTH = "avg_word_length"
    SENTENCE_COUNT = "sentence_count"
    ENTROPY = "entropy"
    COMPRESSION_RATIO = "compression_ratio"


# Convergence actions
class ConvergenceActions:
    STOP = "stop"
    WARN = "warn"
    NOTIFY = "notify"
    CONTINUE = "continue"


# Default configuration
DEFAULT_CONVERGENCE_THRESHOLD = 0.85
DEFAULT_CONVERGENCE_ACTION = ConvergenceActions.STOP
DEFAULT_CONVERGENCE_PROFILE = ConvergenceProfiles.STRUCTURAL
