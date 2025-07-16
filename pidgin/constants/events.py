"""Event type and field name constants."""


# Event types
class EventTypes:
    # Conversation lifecycle
    CONVERSATION_START = "ConversationStartEvent"
    CONVERSATION_END = "ConversationEndEvent"

    # Turn lifecycle
    TURN_START = "TurnStartEvent"
    TURN_COMPLETE = "TurnCompleteEvent"

    # Message lifecycle
    MESSAGE_REQUEST = "MessageRequestEvent"
    MESSAGE_CHUNK = "MessageChunkEvent"
    MESSAGE_COMPLETE = "MessageCompleteEvent"

    # System events
    SYSTEM_PROMPT = "SystemPromptEvent"
    RATE_LIMIT = "RateLimitEvent"
    TOKEN_USAGE = "TokenUsageEvent"

    # Error events
    API_ERROR = "APIErrorEvent"
    PROVIDER_ERROR = "ProviderErrorEvent"

    # Analysis events
    CONVERGENCE_DETECTED = "ConvergenceDetectedEvent"

    # Agent events
    AGENT_NAME_CHOSEN = "AgentNameChosenEvent"
    AGENT_THINKING = "AgentThinkingEvent"


# Event field names
class EventFields:
    # Common fields
    EVENT_TYPE = "event_type"
    EVENT_ID = "event_id"
    TIMESTAMP = "timestamp"
    CONVERSATION_ID = "conversation_id"
    EXPERIMENT_ID = "experiment_id"

    # Turn/message fields
    TURN_NUMBER = "turn_number"
    AGENT_ID = "agent_id"
    MESSAGE = "message"
    CONTENT = "content"
    CHUNK = "chunk"

    # Error fields
    ERROR = "error"
    ERROR_TYPE = "error_type"
    ERROR_MESSAGE = "error_message"
    RETRY_COUNT = "retry_count"

    # Metrics fields
    METRICS = "metrics"
    CONVERGENCE_SCORE = "convergence_score"

    # Usage fields
    USAGE = "usage"
    PROMPT_TOKENS = "prompt_tokens"
    COMPLETION_TOKENS = "completion_tokens"
    TOTAL_TOKENS = "total_tokens"

    # Timing fields
    DURATION_MS = "duration_ms"
    RESPONSE_TIME_MS = "response_time_ms"


# Collections
ALL_EVENT_TYPES = [
    EventTypes.CONVERSATION_START,
    EventTypes.CONVERSATION_END,
    EventTypes.TURN_START,
    EventTypes.TURN_COMPLETE,
    EventTypes.MESSAGE_REQUEST,
    EventTypes.MESSAGE_CHUNK,
    EventTypes.MESSAGE_COMPLETE,
    EventTypes.SYSTEM_PROMPT,
    EventTypes.RATE_LIMIT,
    EventTypes.TOKEN_USAGE,
    EventTypes.API_ERROR,
    EventTypes.PROVIDER_ERROR,
    EventTypes.CONVERGENCE_DETECTED,
    EventTypes.AGENT_NAME_CHOSEN,
    EventTypes.AGENT_THINKING,
]
