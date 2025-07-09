"""Experiment status and metadata constants."""

# Experiment statuses
class ExperimentStatus:
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    COMPLETED_WITH_FAILURES = "completed_with_failures"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"

# Experiment types
class ExperimentType:
    SINGLE_CONVERSATION = "single_conversation"
    BATCH_CONVERSATIONS = "batch_conversations"
    PARAMETER_SWEEP = "parameter_sweep"

# Default values
DEFAULT_MAX_TURNS = 50
DEFAULT_MAX_PARALLEL = 1
DEFAULT_REPETITIONS = 1

# Collections
ALL_EXPERIMENT_STATUSES = [
    ExperimentStatus.CREATED,
    ExperimentStatus.RUNNING,
    ExperimentStatus.PAUSED,
    ExperimentStatus.COMPLETED,
    ExperimentStatus.COMPLETED_WITH_FAILURES,
    ExperimentStatus.FAILED,
    ExperimentStatus.CANCELLED,
    ExperimentStatus.INTERRUPTED,
]

TERMINAL_EXPERIMENT_STATUSES = [
    ExperimentStatus.COMPLETED,
    ExperimentStatus.COMPLETED_WITH_FAILURES,
    ExperimentStatus.FAILED,
    ExperimentStatus.CANCELLED,
    ExperimentStatus.INTERRUPTED,
]