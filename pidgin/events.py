"""Event types for the event-driven conversation system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from .types import Message


@dataclass
class Event:
    """Base event with timestamp and ID."""
    timestamp: datetime = field(default_factory=datetime.now, init=False)
    event_id: str = field(default_factory=lambda: uuid4().hex[:8], init=False)


@dataclass
class Turn:
    """The 2+1 tuple - core conversation unit."""
    agent_a_message: Message
    agent_b_message: Message
    intervention: Optional[Message] = None


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


@dataclass
class MessageRequestEvent(Event):
    """Request for an agent to generate a message."""
    conversation_id: str
    agent_id: str
    turn_number: int
    conversation_history: List[Message]


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


@dataclass
class ConversationEndEvent(Event):
    """Conversation has ended."""
    conversation_id: str
    reason: str  # "max_turns", "pause", "error", "attractor"
    total_turns: int
    duration_ms: int