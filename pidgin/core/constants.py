"""Core constants for the Pidgin application."""


class ConversationStatus:
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class EndReason:
    HIGH_CONVERGENCE = "high_convergence"
    INTERRUPTED = "interrupted"
    CONTEXT_LIMIT_REACHED = "context_limit_reached"
    MAX_TURNS = "max_turns"
    ERROR = "error"
    MAX_TURNS_REACHED = "max_turns_reached"
    CONVERGENCE_THRESHOLD = "convergence_threshold"
    USER_INTERRUPT = "user_interrupt"
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    EXCEPTION = "exception"


class RateLimits:
    DEFAULT_RESPONSE_TOKENS = 500  # Conservative estimate for response
    TOKEN_CHAR_RATIO = 4  # Roughly 4 chars per token
    TOKEN_OVERHEAD_MULTIPLIER = 1.1  # 10% overhead for metadata
    RATE_LIMIT_WAIT_THRESHOLD = 0.1  # Seconds before showing pacing indicator
    INTERRUPT_CHECK_INTERVAL = 0.1  # How often to check for interrupts (seconds)
    SAFETY_MARGIN = 0.9  # Use 90% of rate limit to be safe


class SystemDefaults:
    MAX_EVENT_HISTORY = 1000  # Maximum events to keep in memory
    DEFAULT_TIMEOUT = 60.0  # Default message timeout in seconds
    MAX_RETRIES = 10  # Maximum retry attempts
    DB_RETRY_ATTEMPTS = 3  # Database operation retry attempts
    DB_RETRY_ATTEMPTS_READONLY = 1  # Fewer retries for read-only operations


class ExperimentStatus:
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_FAILURES = "completed_with_failures"
    POST_PROCESSING = "post_processing"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class ProviderNames:
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    XAI = "xai"
    OLLAMA = "ollama"
    LOCAL = "local"
    SILENT = "silent"


class EnvVars:
    ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"
    OPENAI_API_KEY = "OPENAI_API_KEY"
    GOOGLE_API_KEY = "GOOGLE_API_KEY"
    GEMINI_API_KEY = "GEMINI_API_KEY"
    XAI_API_KEY = "XAI_API_KEY"
    GROK_API_KEY = "GROK_API_KEY"
