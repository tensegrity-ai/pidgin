"""Event types for the event-driven conversation system."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .types import Message


@dataclass
class Event:
    """Base event with timestamp and ID."""

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), init=False
    )
    event_id: str = field(default_factory=lambda: uuid4().hex[:8], init=False)


@dataclass
class Turn:
    """A conversation turn between two agents."""

    agent_a_message: Message
    agent_b_message: Message


@dataclass
class TurnStartEvent(Event):
    """Signals the beginning of a new turn."""

    conversation_id: str
    turn_number: int


@dataclass
class TurnCompleteEvent(Event):
    """Signals a turn has completed with all messages."""

    conversation_id: str
    turn_number: int
    turn: Turn
    convergence_score: Optional[float] = None


@dataclass
class MessageRequestEvent(Event):
    """Request for an agent to generate a message."""

    conversation_id: str
    agent_id: str
    turn_number: int
    conversation_history: List[Message]
    temperature: Optional[float] = None
    allow_truncation: bool = False


@dataclass
class SystemPromptEvent(Event):
    """System prompt given to an agent."""

    conversation_id: str
    agent_id: str
    prompt: str
    agent_display_name: Optional[str] = None


@dataclass
class MessageChunkEvent(Event):
    """A chunk of streaming message content."""

    conversation_id: str
    agent_id: str
    chunk: str
    chunk_index: int
    elapsed_ms: int


@dataclass
class MessageCompleteEvent(Event):
    """A message has been fully generated."""

    conversation_id: str
    agent_id: str
    message: Message
    tokens_used: int
    duration_ms: int


@dataclass
class ConversationStartEvent(Event):
    """Conversation is beginning."""

    conversation_id: str
    agent_a_model: str
    agent_b_model: str
    initial_prompt: str
    max_turns: int
    agent_a_display_name: Optional[str] = None
    agent_b_display_name: Optional[str] = None
    temperature_a: Optional[float] = None
    temperature_b: Optional[float] = None


@dataclass
class ConversationEndEvent(Event):
    """Conversation has ended."""

    conversation_id: str
    reason: str  # "max_turns", "pause", "error", "high_convergence"
    total_turns: int
    duration_ms: int


@dataclass
class ErrorEvent(Event):
    """Base error event."""

    conversation_id: str
    error_type: str
    error_message: str
    context: Optional[str] = None


@dataclass
class APIErrorEvent(Event):
    """API call error event."""

    conversation_id: str
    error_type: str
    error_message: str
    agent_id: str
    provider: str
    context: Optional[str] = None
    retryable: bool = False
    retry_count: int = 0


@dataclass
class ProviderTimeoutEvent(Event):
    """Provider timeout event."""

    conversation_id: str
    error_type: str
    error_message: str
    agent_id: str
    timeout_seconds: float
    context: Optional[str] = None


@dataclass
class InterruptRequestEvent(Event):
    """User requested to pause the conversation."""

    conversation_id: str
    turn_number: int
    interrupt_source: str = "user"  # "user", "convergence", "context_limit"


@dataclass
class ConversationPausedEvent(Event):
    """Conversation has been paused."""

    conversation_id: str
    turn_number: int
    paused_during: str  # "waiting_for_agent_a", "waiting_for_agent_b", "between_turns"


@dataclass
class ConversationResumedEvent(Event):
    """Conversation has been resumed."""

    conversation_id: str
    turn_number: int


@dataclass
class RateLimitPaceEvent(Event):
    """Emitted when we pause for rate limits."""

    conversation_id: str
    provider: str
    wait_time: float
    reason: str  # "request_rate" or "token_rate"


@dataclass
class TokenUsageEvent(Event):
    """Track token consumption."""

    conversation_id: str
    provider: str
    tokens_used: int
    tokens_per_minute_limit: int
    current_usage_rate: float


@dataclass
class ContextTruncationEvent(Event):
    """Emitted when messages are truncated to fit context window."""

    conversation_id: str
    agent_id: str
    provider: str
    model: str
    turn_number: int
    original_message_count: int
    truncated_message_count: int
    messages_dropped: int


@dataclass
class ContextLimitEvent(Event):
    """Emitted when a context window limit is reached, ending the conversation naturally."""

    conversation_id: str
    agent_id: str
    turn_number: int
    error_message: str
    provider: str


@dataclass
class ConversationBranchedEvent(Event):
    """Emitted when a conversation is branched from another."""

    conversation_id: str  # New conversation ID
    source_conversation_id: str  # Original conversation ID
    branch_point: int  # Turn number where branch occurred
    parameter_changes: Dict[str, Any]  # What parameters were changed
    experiment_id: Optional[str] = None  # New experiment ID


@dataclass
class ExperimentCompleteEvent(Event):
    """Emitted when all conversations in an experiment are complete."""

    experiment_id: str
    total_conversations: int
    completed_conversations: int
    failed_conversations: int
    status: str  # completed, failed, interrupted


@dataclass
class PostProcessingStartEvent(Event):
    """Emitted when post-experiment processing begins."""

    experiment_id: str
    tasks: List[str]  # List of tasks to perform (e.g., ["readme", "notebook", "database", "transcripts"])


@dataclass
class PostProcessingCompleteEvent(Event):
    """Emitted when all post-experiment processing is complete."""

    experiment_id: str
    tasks_completed: List[str]  # Tasks that were successfully completed
    tasks_failed: List[str]  # Tasks that failed
    duration_ms: int
