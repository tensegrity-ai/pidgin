"""Conversation status and lifecycle constants."""


# Conversation statuses
class ConversationStatus:
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


# End reasons
class EndReason:
    MAX_TURNS_REACHED = "max_turns_reached"
    CONVERGENCE_THRESHOLD = "convergence_threshold"
    USER_INTERRUPT = "user_interrupt"
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    EXCEPTION = "exception"

    # Legacy aliases for compatibility during migration
    HIGH_CONVERGENCE = "high_convergence"
    INTERRUPTED = "interrupted"
    MAX_TURNS = "max_turns"
    ERROR = "error"


# Collections
ALL_CONVERSATION_STATUSES = [
    ConversationStatus.CREATED,
    ConversationStatus.RUNNING,
    ConversationStatus.PAUSED,
    ConversationStatus.COMPLETED,
    ConversationStatus.FAILED,
    ConversationStatus.INTERRUPTED,
]

TERMINAL_STATUSES = [
    ConversationStatus.COMPLETED,
    ConversationStatus.FAILED,
    ConversationStatus.INTERRUPTED,
]

ACTIVE_STATUSES = [
    ConversationStatus.RUNNING,
    ConversationStatus.PAUSED,
]
