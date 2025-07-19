"""Deserialize JSONL events back to Event dataclasses."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Type

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
    TokenUsageEvent,
    Turn,
    TurnCompleteEvent,
    TurnStartEvent,
)
from ..core.types import Message
from ..io.logger import get_logger

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
        # Handle legacy names
        "ConversationCreated": ConversationStartEvent,
    }

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

            # Build event based on type
            if event_type == "ConversationStartEvent":
                return cls._build_conversation_start(event_data, timestamp)
            elif event_type == "ConversationEndEvent":
                return cls._build_conversation_end(event_data, timestamp)
            elif event_type == "TurnStartEvent":
                return cls._build_turn_start(event_data, timestamp)
            elif event_type == "TurnCompleteEvent":
                return cls._build_turn_complete(event_data, timestamp)
            elif event_type == "MessageRequestEvent":
                return cls._build_message_request(event_data, timestamp)
            elif event_type == "MessageChunkEvent":
                return cls._build_message_chunk(event_data, timestamp)
            elif event_type == "MessageCompleteEvent":
                return cls._build_message_complete(event_data, timestamp)
            elif event_type == "SystemPromptEvent":
                return cls._build_system_prompt(event_data, timestamp)
            elif event_type == "ErrorEvent":
                return cls._build_error(event_data, timestamp)
            elif event_type == "APIErrorEvent":
                return cls._build_api_error(event_data, timestamp)
            elif event_type == "ProviderTimeoutEvent":
                return cls._build_provider_timeout(event_data, timestamp)
            elif event_type == "InterruptRequestEvent":
                return cls._build_interrupt_request(event_data, timestamp)
            elif event_type == "ConversationPausedEvent":
                return cls._build_conversation_paused(event_data, timestamp)
            elif event_type == "ConversationResumedEvent":
                return cls._build_conversation_resumed(event_data, timestamp)
            elif event_type == "RateLimitPaceEvent":
                return cls._build_rate_limit_pace(event_data, timestamp)
            elif event_type == "TokenUsageEvent":
                return cls._build_token_usage(event_data, timestamp)
            elif event_type == "ContextTruncationEvent":
                return cls._build_context_truncation(event_data, timestamp)
            elif event_type == "ConversationBranchedEvent":
                return cls._build_conversation_branched(event_data, timestamp)
            elif event_type == "ExperimentCompleteEvent":
                return cls._build_experiment_complete(event_data, timestamp)
            elif event_type == "PostProcessingStartEvent":
                return cls._build_post_processing_start(event_data, timestamp)
            elif event_type == "PostProcessingCompleteEvent":
                return cls._build_post_processing_complete(event_data, timestamp)
            else:
                logger.warning(f"No builder for event type: {event_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to deserialize {event_type}: {e}")
            return None

    @staticmethod
    def _parse_timestamp(timestamp_str: str) -> datetime:
        """Parse ISO timestamp string to datetime."""
        try:
            # Handle timezone-aware timestamps
            if "+" in timestamp_str or timestamp_str.endswith("Z"):
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError, AttributeError):
            # Fallback to now if parsing fails (invalid format, None, or not a string)
            return datetime.now()

    @classmethod
    def _build_conversation_start(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationStartEvent:
        """Build ConversationStartEvent from JSON data."""
        event = ConversationStartEvent(
            conversation_id=data.get("conversation_id", ""),
            agent_a_model=data.get("agent_a_model", ""),
            agent_b_model=data.get("agent_b_model", ""),
            initial_prompt=data.get("initial_prompt", ""),
            max_turns=data.get("max_turns", 0),
            agent_a_display_name=data.get("agent_a_display_name"),
            agent_b_display_name=data.get("agent_b_display_name"),
            temperature_a=data.get("temperature_a"),
            temperature_b=data.get("temperature_b"),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_conversation_end(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationEndEvent:
        """Build ConversationEndEvent from JSON data."""
        event = ConversationEndEvent(
            conversation_id=data.get("conversation_id", ""),
            reason=data.get("reason", "unknown"),
            total_turns=data.get("total_turns", 0),
            duration_ms=data.get("duration_ms", 0),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_turn_start(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> TurnStartEvent:
        """Build TurnStartEvent from JSON data."""
        event = TurnStartEvent(
            conversation_id=data.get("conversation_id", ""),
            turn_number=data.get("turn_number", 0),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_turn_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> TurnCompleteEvent:
        """Build TurnCompleteEvent from JSON data."""
        turn_data = data.get("turn", {})

        # Extract messages from turn data
        msg_a_data = turn_data.get("agent_a_message", {})
        msg_b_data = turn_data.get("agent_b_message", {})

        msg_a = Message(
            role="assistant",
            content=msg_a_data.get("content", ""),
            agent_id="agent_a",
            timestamp=(
                cls._parse_timestamp(msg_a_data.get("timestamp", ""))
                if msg_a_data.get("timestamp")
                else timestamp
            ),
        )

        msg_b = Message(
            role="assistant",
            content=msg_b_data.get("content", ""),
            agent_id="agent_b",
            timestamp=(
                cls._parse_timestamp(msg_b_data.get("timestamp", ""))
                if msg_b_data.get("timestamp")
                else timestamp
            ),
        )

        turn = Turn(agent_a_message=msg_a, agent_b_message=msg_b)

        event = TurnCompleteEvent(
            conversation_id=data.get("conversation_id", ""),
            turn_number=data.get("turn_number", 0),
            turn=turn,
            convergence_score=data.get("convergence_score"),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_message_request(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> MessageRequestEvent:
        """Build MessageRequestEvent from JSON data."""
        # Parse conversation history
        conversation_history = []
        for msg_data in data.get("conversation_history", []):
            message = Message(
                role=msg_data.get("role", "user"),
                content=msg_data.get("content", ""),
                agent_id=msg_data.get("agent_id", ""),
                timestamp=(
                    cls._parse_timestamp(msg_data.get("timestamp", ""))
                    if msg_data.get("timestamp")
                    else timestamp
                ),
            )
            conversation_history.append(message)

        event = MessageRequestEvent(
            conversation_id=data.get("conversation_id", ""),
            agent_id=data.get("agent_id", ""),
            turn_number=data.get("turn_number", 0),
            conversation_history=conversation_history,
            temperature=data.get("temperature"),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_message_chunk(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> MessageChunkEvent:
        """Build MessageChunkEvent from JSON data."""
        event = MessageChunkEvent(
            conversation_id=data.get("conversation_id", ""),
            agent_id=data.get("agent_id", ""),
            chunk=data.get("chunk", ""),
            chunk_index=data.get("chunk_index", 0),
            elapsed_ms=data.get("elapsed_ms", 0),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_message_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> MessageCompleteEvent:
        """Build MessageCompleteEvent from JSON data."""
        msg_data = data.get("message", {})

        message = Message(
            role=msg_data.get("role", "assistant"),
            content=msg_data.get("content", ""),
            agent_id=data.get("agent_id", ""),
            timestamp=(
                cls._parse_timestamp(msg_data.get("timestamp", ""))
                if msg_data.get("timestamp")
                else timestamp
            ),
        )

        event = MessageCompleteEvent(
            conversation_id=data.get("conversation_id", ""),
            agent_id=data.get("agent_id", ""),
            message=message,
            tokens_used=data.get("tokens_used", 0),
            duration_ms=data.get("duration_ms", 0),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_system_prompt(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> SystemPromptEvent:
        """Build SystemPromptEvent from JSON data."""
        event = SystemPromptEvent(
            conversation_id=data.get("conversation_id", ""),
            agent_id=data.get("agent_id", ""),
            prompt=data.get("prompt", ""),
            agent_display_name=data.get("agent_display_name"),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_error(cls, data: Dict[str, Any], timestamp: datetime) -> ErrorEvent:
        """Build ErrorEvent from JSON data."""
        event = ErrorEvent(
            conversation_id=data.get("conversation_id", ""),
            error_type=data.get("error_type", "unknown"),
            error_message=data.get("error_message", ""),
            context=data.get("context"),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_api_error(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> APIErrorEvent:
        """Build APIErrorEvent from JSON data."""
        event = APIErrorEvent(
            conversation_id=data.get("conversation_id", ""),
            error_type=data.get("error_type", "unknown"),
            error_message=data.get("error_message", ""),
            agent_id=data.get("agent_id", ""),
            provider=data.get("provider", ""),
            context=data.get("context"),
            retryable=data.get("retryable", False),
            retry_count=data.get("retry_count", 0),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_provider_timeout(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ProviderTimeoutEvent:
        """Build ProviderTimeoutEvent from JSON data."""
        event = ProviderTimeoutEvent(
            conversation_id=data.get("conversation_id", ""),
            error_type=data.get("error_type", "timeout"),
            error_message=data.get("error_message", ""),
            agent_id=data.get("agent_id", ""),
            timeout_seconds=data.get("timeout_seconds", 0.0),
            context=data.get("context"),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_interrupt_request(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> InterruptRequestEvent:
        """Build InterruptRequestEvent from JSON data."""
        event = InterruptRequestEvent(
            conversation_id=data.get("conversation_id", ""),
            turn_number=data.get("turn_number", 0),
            interrupt_source=data.get("interrupt_source", "user"),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_conversation_paused(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationPausedEvent:
        """Build ConversationPausedEvent from JSON data."""
        event = ConversationPausedEvent(
            conversation_id=data.get("conversation_id", ""),
            turn_number=data.get("turn_number", 0),
            paused_during=data.get("paused_during", ""),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_conversation_resumed(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationResumedEvent:
        """Build ConversationResumedEvent from JSON data."""
        event = ConversationResumedEvent(
            conversation_id=data.get("conversation_id", ""),
            turn_number=data.get("turn_number", 0),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_rate_limit_pace(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> RateLimitPaceEvent:
        """Build RateLimitPaceEvent from JSON data."""
        event = RateLimitPaceEvent(
            conversation_id=data.get("conversation_id", ""),
            provider=data.get("provider", ""),
            wait_time=data.get("wait_time", 0.0),
            reason=data.get("reason", ""),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_token_usage(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> TokenUsageEvent:
        """Build TokenUsageEvent from JSON data."""
        event = TokenUsageEvent(
            conversation_id=data.get("conversation_id", ""),
            provider=data.get("provider", ""),
            tokens_used=data.get("tokens_used", 0),
            tokens_per_minute_limit=data.get("tokens_per_minute_limit", 0),
            current_usage_rate=data.get("current_usage_rate", 0.0),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_context_truncation(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ContextTruncationEvent:
        """Build ContextTruncationEvent from JSON data."""
        event = ContextTruncationEvent(
            conversation_id=data.get("conversation_id", ""),
            agent_id=data.get("agent_id", ""),
            provider=data.get("provider", ""),
            model=data.get("model", ""),
            turn_number=data.get("turn_number", 0),
            original_message_count=data.get("original_message_count", 0),
            truncated_message_count=data.get("truncated_message_count", 0),
            messages_dropped=data.get("messages_dropped", 0),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_conversation_branched(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationBranchedEvent:
        """Build ConversationBranchedEvent from JSON data."""
        event = ConversationBranchedEvent(
            conversation_id=data.get("conversation_id", ""),
            source_conversation_id=data.get("source_conversation_id", ""),
            branch_point=data.get("branch_point", 0),
            parameter_changes=data.get("parameter_changes", {}),
            experiment_id=data.get("experiment_id"),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_experiment_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ExperimentCompleteEvent:
        """Build ExperimentCompleteEvent from JSON data."""
        event = ExperimentCompleteEvent(
            experiment_id=data.get("experiment_id", ""),
            total_conversations=data.get("total_conversations", 0),
            completed_conversations=data.get("completed_conversations", 0),
            failed_conversations=data.get("failed_conversations", 0),
            status=data.get("status", ""),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_post_processing_start(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> PostProcessingStartEvent:
        """Build PostProcessingStartEvent from JSON data."""
        event = PostProcessingStartEvent(
            experiment_id=data.get("experiment_id", ""),
            tasks=data.get("tasks", []),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def _build_post_processing_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> PostProcessingCompleteEvent:
        """Build PostProcessingCompleteEvent from JSON data."""
        event = PostProcessingCompleteEvent(
            experiment_id=data.get("experiment_id", ""),
            tasks_completed=data.get("tasks_completed", []),
            tasks_failed=data.get("tasks_failed", []),
            duration_ms=data.get("duration_ms", 0),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event

    @classmethod
    def read_jsonl_events(cls, jsonl_path: Path):
        """Generator that reads and deserializes events from a JSONL file.

        Args:
            jsonl_path: Path to JSONL file

        Yields:
            (line_number, event) tuples
        """
        with open(jsonl_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    if not line.strip():
                        continue

                    event_data = json.loads(line)
                    event = cls.deserialize_event(event_data)

                    if event:
                        yield line_num, event

                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Invalid JSON at line {line_num} in {jsonl_path}: {e}"
                    )
                    continue
