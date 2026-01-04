"""Deserialize JSONL events back to Event dataclasses."""

import json
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type

from ..core.events import (
    APIErrorEvent,
    ContextTruncationEvent,
    ConversationBranchedEvent,
    ConversationEndEvent,
    ConversationPausedEvent,
    ConversationResumedEvent,
    ConversationStartEvent,
    ErrorEvent,
    Event,
    ExperimentCompleteEvent,
    InterruptRequestEvent,
    MessageChunkEvent,
    MessageCompleteEvent,
    MessageRequestEvent,
    PostProcessingCompleteEvent,
    PostProcessingStartEvent,
    ProviderTimeoutEvent,
    RateLimitPaceEvent,
    SystemPromptEvent,
    ThinkingCompleteEvent,
    TokenUsageEvent,
    TurnCompleteEvent,
    TurnStartEvent,
)
from ..io.logger import get_logger
from .deserializers import (
    ConversationDeserializer,
    ErrorDeserializer,
    MessageDeserializer,
    SystemDeserializer,
)

logger = get_logger("event_deserializer")


class EventDeserializer:
    """Deserialize JSON events back to Event dataclasses."""

    # Map event type strings to event classes
    EVENT_TYPES: Dict[str, Type[Event]] = {
        "ConversationStartEvent": ConversationStartEvent,
        "ConversationEndEvent": ConversationEndEvent,
        "TurnStartEvent": TurnStartEvent,
        "TurnCompleteEvent": TurnCompleteEvent,
        "MessageRequestEvent": MessageRequestEvent,
        "MessageChunkEvent": MessageChunkEvent,
        "MessageCompleteEvent": MessageCompleteEvent,
        "SystemPromptEvent": SystemPromptEvent,
        "ErrorEvent": ErrorEvent,
        "APIErrorEvent": APIErrorEvent,
        "ProviderTimeoutEvent": ProviderTimeoutEvent,
        "InterruptRequestEvent": InterruptRequestEvent,
        "ConversationPausedEvent": ConversationPausedEvent,
        "ConversationResumedEvent": ConversationResumedEvent,
        "RateLimitPaceEvent": RateLimitPaceEvent,
        "TokenUsageEvent": TokenUsageEvent,
        "ContextTruncationEvent": ContextTruncationEvent,
        "ConversationBranchedEvent": ConversationBranchedEvent,
        "ExperimentCompleteEvent": ExperimentCompleteEvent,
        "PostProcessingStartEvent": PostProcessingStartEvent,
        "PostProcessingCompleteEvent": PostProcessingCompleteEvent,
        "ThinkingCompleteEvent": ThinkingCompleteEvent,
        # Handle legacy names
        "ConversationCreated": ConversationStartEvent,
    }

    # Initialize deserializers
    conversation = ConversationDeserializer()
    message = MessageDeserializer()
    error = ErrorDeserializer()
    system = SystemDeserializer()

    @classmethod
    def deserialize_event(cls, event_data: Dict[str, Any]) -> Optional[Event]:
        """Deserialize a JSON event to its corresponding Event dataclass.

        Args:
            event_data: JSON event data

        Returns:
            Event instance or None if unknown event type
        """
        # Handle legacy format where event data is nested under "data" key
        if "data" in event_data and "event_type" in event_data:
            # Legacy format: {"timestamp": "...", "event_type": "...", "data": {...}}
            data_payload = event_data["data"]
            # Copy event_type and timestamp to data payload for consistent processing
            data_payload["event_type"] = event_data["event_type"]
            if "timestamp" in event_data:
                data_payload["timestamp"] = event_data["timestamp"]
            event_data = data_payload

        event_type = event_data.get("event_type")
        if not event_type:
            logger.warning("Event missing event_type field")
            return None

        event_class = cls.EVENT_TYPES.get(event_type)
        if not event_class:
            # Unknown event type - log but don't fail
            logger.debug(f"Unknown event type: {event_type}")
            return None

        try:
            # Parse timestamp if present
            timestamp_str = event_data.get("timestamp")
            timestamp = (
                cls._parse_timestamp(timestamp_str) if timestamp_str else datetime.now()
            )

            # Route to appropriate deserializer based on event type
            if event_type in [
                "ConversationStartEvent",
                "ConversationEndEvent",
                "TurnStartEvent",
                "TurnCompleteEvent",
                "ConversationPausedEvent",
                "ConversationResumedEvent",
                "ConversationBranchedEvent",
                "ExperimentCompleteEvent",
                "PostProcessingStartEvent",
                "PostProcessingCompleteEvent",
            ]:
                return cls._deserialize_conversation_event(
                    event_type, event_data, timestamp
                )
            elif event_type in [
                "MessageRequestEvent",
                "MessageChunkEvent",
                "MessageCompleteEvent",
                "SystemPromptEvent",
                "ThinkingCompleteEvent",
            ]:
                return cls._deserialize_message_event(event_type, event_data, timestamp)
            elif event_type in ["ErrorEvent", "APIErrorEvent", "ProviderTimeoutEvent"]:
                return cls._deserialize_error_event(event_type, event_data, timestamp)
            elif event_type in [
                "InterruptRequestEvent",
                "RateLimitPaceEvent",
                "TokenUsageEvent",
                "ContextTruncationEvent",
            ]:
                return cls._deserialize_system_event(event_type, event_data, timestamp)
            else:
                logger.warning(f"No deserializer for event type: {event_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to deserialize event {event_type}: {e}")
            return None

    @classmethod
    def _deserialize_conversation_event(
        cls, event_type: str, data: Dict[str, Any], timestamp: datetime
    ) -> Optional[Event]:
        """Deserialize conversation events."""
        if event_type == "ConversationStartEvent":
            return cls.conversation.build_conversation_start(data, timestamp)
        elif event_type == "ConversationEndEvent":
            return cls.conversation.build_conversation_end(data, timestamp)
        elif event_type == "TurnStartEvent":
            return cls.conversation.build_turn_start(data, timestamp)
        elif event_type == "TurnCompleteEvent":
            return cls.conversation.build_turn_complete(data, timestamp)
        elif event_type == "ConversationPausedEvent":
            return cls.conversation.build_conversation_paused(data, timestamp)
        elif event_type == "ConversationResumedEvent":
            return cls.conversation.build_conversation_resumed(data, timestamp)
        elif event_type == "ConversationBranchedEvent":
            return cls.conversation.build_conversation_branched(data, timestamp)
        elif event_type == "ExperimentCompleteEvent":
            return cls.conversation.build_experiment_complete(data, timestamp)
        elif event_type == "PostProcessingStartEvent":
            return cls.conversation.build_post_processing_start(data, timestamp)
        elif event_type == "PostProcessingCompleteEvent":
            return cls.conversation.build_post_processing_complete(data, timestamp)
        return None

    @classmethod
    def _deserialize_message_event(
        cls, event_type: str, data: Dict[str, Any], timestamp: datetime
    ) -> Optional[Event]:
        """Deserialize message events."""
        if event_type == "MessageRequestEvent":
            return cls.message.build_message_request(data, timestamp)
        elif event_type == "MessageChunkEvent":
            return cls.message.build_message_chunk(data, timestamp)
        elif event_type == "MessageCompleteEvent":
            return cls.message.build_message_complete(data, timestamp)
        elif event_type == "SystemPromptEvent":
            return cls.message.build_system_prompt(data, timestamp)
        elif event_type == "ThinkingCompleteEvent":
            return cls.message.build_thinking_complete(data, timestamp)
        return None

    @classmethod
    def _deserialize_error_event(
        cls, event_type: str, data: Dict[str, Any], timestamp: datetime
    ) -> Optional[Event]:
        """Deserialize error events."""
        if event_type == "ErrorEvent":
            return cls.error.build_error(data, timestamp)
        elif event_type == "APIErrorEvent":
            return cls.error.build_api_error(data, timestamp)
        elif event_type == "ProviderTimeoutEvent":
            return cls.error.build_provider_timeout(data, timestamp)
        return None

    @classmethod
    def _deserialize_system_event(
        cls, event_type: str, data: Dict[str, Any], timestamp: datetime
    ) -> Optional[Event]:
        """Deserialize system events."""
        if event_type == "InterruptRequestEvent":
            return cls.system.build_interrupt_request(data, timestamp)
        elif event_type == "RateLimitPaceEvent":
            return cls.system.build_rate_limit_pace(data, timestamp)
        elif event_type == "TokenUsageEvent":
            return cls.system.build_token_usage(data, timestamp)
        elif event_type == "ContextTruncationEvent":
            return cls.system.build_context_truncation(data, timestamp)
        return None

    @staticmethod
    def _parse_timestamp(timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime.

        Args:
            timestamp_str: ISO format timestamp string

        Returns:
            Parsed datetime object
        """
        # Delegate to base deserializer
        from .deserializers.base import BaseDeserializer

        return BaseDeserializer.parse_timestamp(timestamp_str)

    def read_jsonl_events(
        self, jsonl_file: Path
    ) -> Generator[Tuple[int, Optional[Event]], None, None]:
        """Read and deserialize events from a JSONL file.

        Args:
            jsonl_file: Path to JSONL file

        Yields:
            Tuple of (line_number, event) where event may be None if deserialization fails
        """
        with open(jsonl_file) as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    event_data = json.loads(line)
                    event = self.deserialize_event(event_data)
                    yield line_num, event
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to deserialize line {line_num}: {e}")
                    yield line_num, None
