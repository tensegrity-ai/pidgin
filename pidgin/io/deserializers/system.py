"""Deserializers for system events."""

from datetime import datetime
from typing import Any, Dict

from ...core.events import (
    ContextTruncationEvent,
    InterruptRequestEvent,
    RateLimitPaceEvent,
    TokenUsageEvent,
)
from .base import BaseDeserializer


class SystemDeserializer(BaseDeserializer):
    """Deserialize system events."""

    @classmethod
    def build_interrupt_request(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> InterruptRequestEvent:
        """Build InterruptRequestEvent from data."""
        event = InterruptRequestEvent(
            conversation_id=data.get("conversation_id"),
            turn_number=data.get("turn_number", 0),
            interrupt_source=data.get("interrupt_source", data.get("source", "user")),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_rate_limit_pace(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> RateLimitPaceEvent:
        """Build RateLimitPaceEvent from data."""
        event = RateLimitPaceEvent(
            conversation_id=data.get("conversation_id"),
            provider=data["provider"],
            wait_time=data.get("wait_time", data.get("wait_seconds", 0)),
            reason=data.get("reason", "rate_limit"),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_token_usage(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> TokenUsageEvent:
        """Build TokenUsageEvent from data."""
        event = TokenUsageEvent(
            conversation_id=data.get("conversation_id"),
            provider=data["provider"],
            tokens_used=data.get("tokens_used", data.get("total_tokens", 0)),
            tokens_per_minute_limit=data.get("tokens_per_minute_limit", 0),
            current_usage_rate=data.get("current_usage_rate", 0.0),
            agent_id=data.get("agent_id"),
            model=data.get("model"),
            prompt_tokens=data.get("prompt_tokens"),
            completion_tokens=data.get("completion_tokens"),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_context_truncation(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ContextTruncationEvent:
        """Build ContextTruncationEvent from data."""
        event = ContextTruncationEvent(
            conversation_id=data["conversation_id"],
            agent_id=data["agent_id"],
            provider=data.get("provider", "unknown"),
            model=data.get("model", "unknown"),
            turn_number=data["turn_number"],
            original_message_count=data.get(
                "original_message_count", data.get("messages_before", 0)
            ),
            truncated_message_count=data.get(
                "truncated_message_count", data.get("messages_after", 0)
            ),
            messages_dropped=data.get("messages_dropped", 0),
        )
        event.timestamp = timestamp
        return event
