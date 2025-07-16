"""Core business logic for pidgin."""

from .event_bus import EventBus
from .events import (
    APIErrorEvent,
    ConversationEndEvent,
    ConversationPausedEvent,
    ConversationResumedEvent,
    ConversationStartEvent,
    ErrorEvent,
    Event,
    InterruptRequestEvent,
    MessageChunkEvent,
    MessageCompleteEvent,
    MessageRequestEvent,
    ProviderTimeoutEvent,
    SystemPromptEvent,
    Turn,
    TurnCompleteEvent,
    TurnStartEvent,
)
from .router import Router
from .types import Agent, Conversation, Message

__all__ = [
    # From event_bus
    "EventBus",
    # From router
    "Router",
    # From events - explicitly list all event types
    "Event",
    "Turn",
    "TurnStartEvent",
    "TurnCompleteEvent",
    "MessageRequestEvent",
    "MessageChunkEvent",
    "MessageCompleteEvent",
    "ConversationStartEvent",
    "ConversationEndEvent",
    "ErrorEvent",
    "APIErrorEvent",
    "ProviderTimeoutEvent",
    "SystemPromptEvent",
    "InterruptRequestEvent",
    "ConversationPausedEvent",
    "ConversationResumedEvent",
    # From types
    "Agent",
    "Message",
    "Conversation",
]
