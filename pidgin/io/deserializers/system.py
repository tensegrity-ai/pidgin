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
        return InterruptRequestEvent(
            timestamp=timestamp,
            conversation_id=data.get("conversation_id"),
            experiment_id=data.get("experiment_id"),
            source=data.get("source", "user"),
        )

    @classmethod
    def build_rate_limit_pace(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> RateLimitPaceEvent:
        """Build RateLimitPaceEvent from data."""
        return RateLimitPaceEvent(
            timestamp=timestamp,
            conversation_id=data.get("conversation_id"),
            experiment_id=data.get("experiment_id"),
            agent_id=data["agent_id"],
            provider=data["provider"],
            wait_seconds=data["wait_seconds"],
            reason=data.get("reason", "rate_limit"),
        )

    @classmethod
    def build_token_usage(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> TokenUsageEvent:
        """Build TokenUsageEvent from data."""
        return TokenUsageEvent(
            timestamp=timestamp,
            conversation_id=data.get("conversation_id"),
            experiment_id=data.get("experiment_id"),
            agent_id=data["agent_id"],
            provider=data["provider"],
            model=data["model"],
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
        )

    @classmethod
    def build_context_truncation(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ContextTruncationEvent:
        """Build ContextTruncationEvent from data."""
        return ContextTruncationEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            agent_id=data["agent_id"],
            turn_number=data["turn_number"],
            messages_before=data["messages_before"],
            messages_after=data["messages_after"],
            tokens_before=data.get("tokens_before"),
            tokens_after=data.get("tokens_after"),
        )