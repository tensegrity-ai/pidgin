"""Constants for tail display."""

from ...core.events import (
    APIErrorEvent,
    ContextTruncationEvent,
    ConversationEndEvent,
    ConversationPausedEvent,
    ConversationResumedEvent,
    ConversationStartEvent,
    InterruptRequestEvent,
    MessageChunkEvent,
    MessageCompleteEvent,
    MessageRequestEvent,
    ProviderTimeoutEvent,
    RateLimitPaceEvent,
    SystemPromptEvent,
    TokenUsageEvent,
    TurnCompleteEvent,
    TurnStartEvent,
)

# Nord color palette - duplicate values to avoid circular imports
NORD_GREEN = "#a3be8c"
NORD_RED = "#bf616a"
NORD_BLUE = "#88c0d0"
NORD_CYAN = "#8fbcbb"
NORD_YELLOW = "#ebcb8b"
NORD_ORANGE = "#d08770"
NORD_PURPLE = "#b48ead"
NORD_GRAY = "#4c566a"
NORD_LIGHT = "#eceff4"

EVENT_COLORS = {
    ConversationStartEvent: NORD_GREEN,
    ConversationEndEvent: NORD_RED,
    TurnStartEvent: NORD_BLUE,
    TurnCompleteEvent: NORD_BLUE,
    MessageRequestEvent: NORD_YELLOW,
    MessageCompleteEvent: NORD_CYAN,
    SystemPromptEvent: NORD_GRAY,
    APIErrorEvent: NORD_RED,
    ContextTruncationEvent: NORD_ORANGE,
    RateLimitPaceEvent: NORD_PURPLE,
    TokenUsageEvent: NORD_CYAN,
    ProviderTimeoutEvent: NORD_ORANGE,
    InterruptRequestEvent: NORD_RED,
    ConversationPausedEvent: NORD_YELLOW,
    ConversationResumedEvent: NORD_GREEN,
}

EVENT_GLYPHS = {
    ConversationStartEvent: "◆",
    ConversationEndEvent: "◇",
    TurnStartEvent: "▶",
    TurnCompleteEvent: "■",
    MessageRequestEvent: "→",
    MessageCompleteEvent: "✓",
    MessageChunkEvent: "·",
    SystemPromptEvent: "⚙",
    APIErrorEvent: "✗",
    ContextTruncationEvent: "⚠",
    RateLimitPaceEvent: "⧖",
    TokenUsageEvent: "◉",
    ProviderTimeoutEvent: "⟡",
    InterruptRequestEvent: "⚡",
    ConversationPausedEvent: "⏸",
    ConversationResumedEvent: "▶",
}
