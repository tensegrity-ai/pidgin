"""Deserializers for message events."""

from datetime import datetime
from typing import Any, Dict

from ...core.events import (
    MessageChunkEvent,
    MessageCompleteEvent,
    MessageRequestEvent,
    SystemPromptEvent,
    ThinkingCompleteEvent,
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
                            agent_id=msg_data.get("agent_id", "unknown"),
                        )
                    )

        event = MessageRequestEvent(
            conversation_id=data["conversation_id"],
            agent_id=data["agent_id"],
            turn_number=data.get("turn_number", 0),
            conversation_history=messages,  # Note: field is conversation_history, not messages
            temperature=data.get("temperature"),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_message_chunk(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> MessageChunkEvent:
        """Build MessageChunkEvent from data."""
        event = MessageChunkEvent(
            conversation_id=data["conversation_id"],
            agent_id=data["agent_id"],
            chunk=data.get("chunk", ""),
            chunk_index=data.get("chunk_index", 0),
            elapsed_ms=data.get("elapsed_ms", 0),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_message_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> MessageCompleteEvent:
        """Build MessageCompleteEvent from data."""
        # Reconstruct message - handle both nested and flat structures
        if "message" in data and isinstance(data["message"], dict):
            # Message is nested as an object
            msg_data = data["message"]
            message = Message(
                role=msg_data.get("role", "assistant"),
                content=msg_data.get("content", ""),
                agent_id=msg_data.get("agent_id", data.get("agent_id", "unknown")),
            )
        else:
            # Message fields are flat in data
            message = Message(
                role=data.get("role", "assistant"),
                content=data.get("content", data.get("message", "")),
                agent_id=data.get("agent_id", "unknown"),
            )

        event = MessageCompleteEvent(
            conversation_id=data["conversation_id"],
            agent_id=data["agent_id"],
            message=message,
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            duration_ms=data.get("duration_ms", 0),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_system_prompt(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> SystemPromptEvent:
        """Build SystemPromptEvent from data."""
        event = SystemPromptEvent(
            conversation_id=data["conversation_id"],
            agent_id=data["agent_id"],
            prompt=data["prompt"],
            agent_display_name=data.get("agent_display_name"),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_thinking_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ThinkingCompleteEvent:
        """Build ThinkingCompleteEvent from data."""
        event = ThinkingCompleteEvent(
            conversation_id=data["conversation_id"],
            turn_number=data.get("turn_number", 0),
            agent_id=data["agent_id"],
            thinking_content=data.get("thinking_content", ""),
            thinking_tokens=data.get("thinking_tokens"),
            duration_ms=data.get("duration_ms"),
        )
        event.timestamp = timestamp
        return event
