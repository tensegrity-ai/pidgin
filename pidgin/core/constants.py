"""Core constants for the Pidgin application."""


# Nord color scheme for console output
class Colors:
    """Nord color scheme constants."""

    GREEN = "#a3be8c"
    RED = "#bf616a"
    YELLOW = "#ebcb8b"
    BLUE = "#5e81ac"
    DIM = "#4c566a"


# Status strings
class ConversationStatus:
    """Conversation status constants."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class EndReason:
    """Conversation end reason constants."""

    HIGH_CONVERGENCE = "high_convergence"
    INTERRUPTED = "interrupted"
    MAX_TURNS = "max_turns"
    ERROR = "error"


# Rate limiting constants
class RateLimits:
    """Rate limiting constants."""

    DEFAULT_RESPONSE_TOKENS = 500  # Conservative estimate for response
    TOKEN_CHAR_RATIO = 4  # Roughly 4 chars per token
    TOKEN_OVERHEAD_MULTIPLIER = 1.1  # 10% overhead for metadata
    RATE_LIMIT_WAIT_THRESHOLD = 0.1  # Seconds before showing pacing indicator
    INTERRUPT_CHECK_INTERVAL = 0.1  # How often to check for interrupts (seconds)
    SAFETY_MARGIN = 0.9  # Use 90% of rate limit to be safe


# System defaults
class SystemDefaults:
    """System-wide default values."""

    MAX_EVENT_HISTORY = 1000  # Maximum events to keep in memory
    DEFAULT_TIMEOUT = 60.0  # Default message timeout in seconds
    MAX_RETRIES = 10  # Maximum retry attempts
    DB_RETRY_ATTEMPTS = 3  # Database operation retry attempts
    DB_RETRY_ATTEMPTS_READONLY = 1  # Fewer retries for read-only operations
