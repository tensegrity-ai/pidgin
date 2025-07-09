"""Constants package for Pidgin.

This package provides centralized constant definitions to eliminate magic strings
and improve code maintainability.
"""

# Agent constants
from .agents import (
    AGENT_A, AGENT_B,
    ROLE_ASSISTANT, ROLE_USER, ROLE_SYSTEM,
    DEFAULT_AGENT_A_NAME, DEFAULT_AGENT_B_NAME,
    ALL_AGENT_IDS, ALL_ROLES
)

# Conversation constants
from .conversations import (
    ConversationStatus, EndReason,
    ALL_CONVERSATION_STATUSES, TERMINAL_STATUSES, ACTIVE_STATUSES
)

# Experiment constants
from .experiments import (
    ExperimentStatus, ExperimentType,
    DEFAULT_MAX_TURNS, DEFAULT_MAX_PARALLEL, DEFAULT_REPETITIONS,
    ALL_EXPERIMENT_STATUSES, TERMINAL_EXPERIMENT_STATUSES
)

# File constants
from .files import (
    FileExtensions, DirectoryNames, FilePatterns, SpecialFiles,
    DEFAULT_OUTPUT_DIR, DEFAULT_DB_NAME, DEFAULT_CONFIG_FILE
)

# Manifest constants
from .manifests import (
    ManifestFields, MANIFEST_VERSION,
    REQUIRED_MANIFEST_FIELDS, DEFAULT_MANIFEST_VALUES
)

# Provider constants
from .providers import (
    ProviderNames, ModelPrefixes, SpecialModels, EnvVars,
    ALL_PROVIDERS, API_PROVIDERS, LOCAL_PROVIDERS
)

# Event constants
from .events import (
    EventTypes, EventFields,
    ALL_EVENT_TYPES
)

# Metrics constants
from .metrics import (
    ConvergenceComponents, ConvergenceProfiles, ConvergenceActions,
    DEFAULT_CONVERGENCE_WEIGHTS, MetricThresholds, MetricColumns,
    DEFAULT_CONVERGENCE_THRESHOLD, DEFAULT_CONVERGENCE_ACTION, DEFAULT_CONVERGENCE_PROFILE
)

# Linguistic constants
from .linguistic import (
    HEDGE_WORDS, AGREEMENT_MARKERS, DISAGREEMENT_MARKERS, POLITENESS_MARKERS,
    FIRST_PERSON_SINGULAR, FIRST_PERSON_PLURAL, SECOND_PERSON,
    THIRD_PERSON_SINGULAR, THIRD_PERSON_PLURAL, ALL_PRONOUNS,
    SENTENCE_ENDINGS_PATTERN, QUESTION_PATTERN, EXCLAMATION_PATTERN,
    URL_PATTERN, EMAIL_PATTERN, ACKNOWLEDGMENT_PATTERNS
)

# Symbol constants
from .symbols import (
    ARROWS, MATH_SYMBOLS, BOX_DRAWING, BULLETS,
    ALL_SPECIAL_SYMBOLS, EMOJI_RANGES, ASCII_ARROWS, SEPARATORS
)

# Legacy imports from core.constants (will be removed after migration)
from pidgin.core.constants import (
    Colors, RateLimits, SystemDefaults
)

__all__ = [
    # Agents
    'AGENT_A', 'AGENT_B', 'ROLE_ASSISTANT', 'ROLE_USER', 'ROLE_SYSTEM',
    'DEFAULT_AGENT_A_NAME', 'DEFAULT_AGENT_B_NAME', 'ALL_AGENT_IDS', 'ALL_ROLES',
    
    # Conversations
    'ConversationStatus', 'EndReason', 'ALL_CONVERSATION_STATUSES',
    'TERMINAL_STATUSES', 'ACTIVE_STATUSES',
    
    # Experiments
    'ExperimentStatus', 'ExperimentType', 'DEFAULT_MAX_TURNS',
    'DEFAULT_MAX_PARALLEL', 'DEFAULT_REPETITIONS',
    'ALL_EXPERIMENT_STATUSES', 'TERMINAL_EXPERIMENT_STATUSES',
    
    # Files
    'FileExtensions', 'DirectoryNames', 'FilePatterns', 'SpecialFiles',
    'DEFAULT_OUTPUT_DIR', 'DEFAULT_DB_NAME', 'DEFAULT_CONFIG_FILE',
    
    # Manifests
    'ManifestFields', 'MANIFEST_VERSION', 'REQUIRED_MANIFEST_FIELDS',
    'DEFAULT_MANIFEST_VALUES',
    
    # Providers
    'ProviderNames', 'ModelPrefixes', 'SpecialModels', 'EnvVars',
    'ALL_PROVIDERS', 'API_PROVIDERS', 'LOCAL_PROVIDERS',
    
    # Events
    'EventTypes', 'EventFields', 'ALL_EVENT_TYPES',
    
    # Metrics
    'ConvergenceComponents', 'ConvergenceProfiles', 'ConvergenceActions',
    'DEFAULT_CONVERGENCE_WEIGHTS', 'MetricThresholds', 'MetricColumns',
    'DEFAULT_CONVERGENCE_THRESHOLD', 'DEFAULT_CONVERGENCE_ACTION',
    'DEFAULT_CONVERGENCE_PROFILE',
    
    # Linguistic
    'HEDGE_WORDS', 'AGREEMENT_MARKERS', 'DISAGREEMENT_MARKERS',
    'POLITENESS_MARKERS', 'FIRST_PERSON_SINGULAR', 'FIRST_PERSON_PLURAL',
    'SECOND_PERSON', 'THIRD_PERSON_SINGULAR', 'THIRD_PERSON_PLURAL',
    'ALL_PRONOUNS', 'SENTENCE_ENDINGS_PATTERN', 'QUESTION_PATTERN',
    'EXCLAMATION_PATTERN', 'URL_PATTERN', 'EMAIL_PATTERN',
    'ACKNOWLEDGMENT_PATTERNS',
    
    # Symbols
    'ARROWS', 'MATH_SYMBOLS', 'BOX_DRAWING', 'BULLETS',
    'ALL_SPECIAL_SYMBOLS', 'EMOJI_RANGES', 'ASCII_ARROWS', 'SEPARATORS',
    
    # Legacy (temporary)
    'Colors', 'RateLimits', 'SystemDefaults',
]