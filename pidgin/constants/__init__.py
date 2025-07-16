"""Constants package for Pidgin.

This package provides centralized constant definitions to eliminate magic strings
and improve code maintainability.
"""

# Agent constants
from .agents import (
    AGENT_A,
    AGENT_B,
    ALL_AGENT_IDS,
    ALL_ROLES,
    DEFAULT_AGENT_A_NAME,
    DEFAULT_AGENT_B_NAME,
    ROLE_ASSISTANT,
    ROLE_SYSTEM,
    ROLE_USER,
)

# Conversation constants
from .conversations import (
    ACTIVE_STATUSES,
    ALL_CONVERSATION_STATUSES,
    TERMINAL_STATUSES,
    ConversationStatus,
    EndReason,
)

# Event constants
from .events import ALL_EVENT_TYPES, EventFields, EventTypes

# Experiment constants
from .experiments import (
    ALL_EXPERIMENT_STATUSES,
    DEFAULT_MAX_PARALLEL,
    DEFAULT_MAX_TURNS,
    DEFAULT_REPETITIONS,
    TERMINAL_EXPERIMENT_STATUSES,
    ExperimentStatus,
    ExperimentType,
)

# File constants
from .files import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_DB_NAME,
    DEFAULT_OUTPUT_DIR,
    DirectoryNames,
    FileExtensions,
    FilePatterns,
    SpecialFiles,
)

# Linguistic constants
from .linguistic import (
    ACKNOWLEDGMENT_PATTERNS,
    AGREEMENT_MARKERS,
    ALL_PRONOUNS,
    DISAGREEMENT_MARKERS,
    EMAIL_PATTERN,
    EXCLAMATION_PATTERN,
    FIRST_PERSON_PLURAL,
    FIRST_PERSON_SINGULAR,
    HEDGE_WORDS,
    POLITENESS_MARKERS,
    QUESTION_PATTERN,
    SECOND_PERSON,
    SENTENCE_ENDINGS_PATTERN,
    THIRD_PERSON_PLURAL,
    THIRD_PERSON_SINGULAR,
    URL_PATTERN,
)

# Manifest constants
from .manifests import (
    DEFAULT_MANIFEST_VALUES,
    MANIFEST_VERSION,
    REQUIRED_MANIFEST_FIELDS,
    ManifestFields,
)

# Metrics constants
from .metrics import (
    DEFAULT_CONVERGENCE_ACTION,
    DEFAULT_CONVERGENCE_PROFILE,
    DEFAULT_CONVERGENCE_THRESHOLD,
    DEFAULT_CONVERGENCE_WEIGHTS,
    ConvergenceActions,
    ConvergenceComponents,
    ConvergenceProfiles,
    MetricColumns,
    MetricThresholds,
)

# Provider constants
from .providers import (
    ALL_PROVIDERS,
    API_PROVIDERS,
    LOCAL_PROVIDERS,
    EnvVars,
    ModelPrefixes,
    ProviderNames,
    SpecialModels,
)

# Symbol constants
from .symbols import (
    ALL_SPECIAL_SYMBOLS,
    ARROWS,
    ASCII_ARROWS,
    BOX_DRAWING,
    BULLETS,
    EMOJI_RANGES,
    MATH_SYMBOLS,
    SEPARATORS,
)

__all__ = [
    # Agents
    "AGENT_A",
    "AGENT_B",
    "ROLE_ASSISTANT",
    "ROLE_USER",
    "ROLE_SYSTEM",
    "DEFAULT_AGENT_A_NAME",
    "DEFAULT_AGENT_B_NAME",
    "ALL_AGENT_IDS",
    "ALL_ROLES",
    # Conversations
    "ConversationStatus",
    "EndReason",
    "ALL_CONVERSATION_STATUSES",
    "TERMINAL_STATUSES",
    "ACTIVE_STATUSES",
    # Experiments
    "ExperimentStatus",
    "ExperimentType",
    "DEFAULT_MAX_TURNS",
    "DEFAULT_MAX_PARALLEL",
    "DEFAULT_REPETITIONS",
    "ALL_EXPERIMENT_STATUSES",
    "TERMINAL_EXPERIMENT_STATUSES",
    # Files
    "FileExtensions",
    "DirectoryNames",
    "FilePatterns",
    "SpecialFiles",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_DB_NAME",
    "DEFAULT_CONFIG_FILE",
    # Manifests
    "ManifestFields",
    "MANIFEST_VERSION",
    "REQUIRED_MANIFEST_FIELDS",
    "DEFAULT_MANIFEST_VALUES",
    # Providers
    "ProviderNames",
    "ModelPrefixes",
    "SpecialModels",
    "EnvVars",
    "ALL_PROVIDERS",
    "API_PROVIDERS",
    "LOCAL_PROVIDERS",
    # Events
    "EventTypes",
    "EventFields",
    "ALL_EVENT_TYPES",
    # Metrics
    "ConvergenceComponents",
    "ConvergenceProfiles",
    "ConvergenceActions",
    "DEFAULT_CONVERGENCE_WEIGHTS",
    "MetricThresholds",
    "MetricColumns",
    "DEFAULT_CONVERGENCE_THRESHOLD",
    "DEFAULT_CONVERGENCE_ACTION",
    "DEFAULT_CONVERGENCE_PROFILE",
    # Linguistic
    "HEDGE_WORDS",
    "AGREEMENT_MARKERS",
    "DISAGREEMENT_MARKERS",
    "POLITENESS_MARKERS",
    "FIRST_PERSON_SINGULAR",
    "FIRST_PERSON_PLURAL",
    "SECOND_PERSON",
    "THIRD_PERSON_SINGULAR",
    "THIRD_PERSON_PLURAL",
    "ALL_PRONOUNS",
    "SENTENCE_ENDINGS_PATTERN",
    "QUESTION_PATTERN",
    "EXCLAMATION_PATTERN",
    "URL_PATTERN",
    "EMAIL_PATTERN",
    "ACKNOWLEDGMENT_PATTERNS",
    # Symbols
    "ARROWS",
    "MATH_SYMBOLS",
    "BOX_DRAWING",
    "BULLETS",
    "ALL_SPECIAL_SYMBOLS",
    "EMOJI_RANGES",
    "ASCII_ARROWS",
    "SEPARATORS",
]
