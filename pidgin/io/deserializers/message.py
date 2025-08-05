"""Deserializers for message events."""

from datetime import datetime
from typing import Any, Dict

from ...core.events import (
    MessageChunkEvent,
    MessageCompleteEvent,
    MessageRequestEvent,
    SystemPromptEvent,
)
from ...core.types import Message
from .base import BaseDeserializer


class MessageDeserializer(BaseDeserializer):
    """Deserialize message events."""

    @classmethod
    def build_message_request(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> MessageRequestEvent:
        """Build MessageRequestEvent from data."""
        # Reconstruct messages list
        messages = []
        if "messages" in data:
            for msg_data in data["messages"]:
                if isinstance(msg_data, dict):
                    messages.append(
                        Message(
                            role=msg_data.get("role", "user"),
                            content=msg_data.get("content", ""),
                        )
                    )

        return MessageRequestEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            agent_id=data["agent_id"],
            turn_number=data.get("turn_number", 0),
            messages=messages,
            model=data.get("model"),
            temperature=data.get("temperature"),
        )

    @classmethod
    def build_message_chunk(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> MessageChunkEvent:
        """Build MessageChunkEvent from data."""
        return MessageChunkEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            agent_id=data["agent_id"],
            turn_number=data.get("turn_number", 0),
            chunk=data.get("chunk", ""),
            chunk_index=data.get("chunk_index", 0),
        )

    @classmethod
    def build_message_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> MessageCompleteEvent:
        """Build MessageCompleteEvent from data."""
        # Reconstruct message
        message = Message(
            role=data.get("role", "assistant"),
            content=data.get("content", data.get("message", "")),
        )

        return MessageCompleteEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            agent_id=data["agent_id"],
            turn_number=data.get("turn_number", 0),
            message=message,
            model=data.get("model"),
            tokens_used=data.get("tokens_used", 0),
            duration_ms=data.get("duration_ms", 0),
        )

    @classmethod
    def build_system_prompt(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> SystemPromptEvent:
        """Build SystemPromptEvent from data."""
        return SystemPromptEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            agent_id=data["agent_id"],
            prompt=data["prompt"],
            agent_display_name=data.get("agent_display_name"),
        )