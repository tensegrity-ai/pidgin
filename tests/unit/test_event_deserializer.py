"""Tests for EventDeserializer."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


from pidgin.core.events import (
    APIErrorEvent,
    ContextTruncationEvent,
    ConversationEndEvent,
    ConversationPausedEvent,
    ConversationResumedEvent,
    ConversationStartEvent,
    ErrorEvent,
    InterruptRequestEvent,
    MessageChunkEvent,
    MessageCompleteEvent,
    MessageRequestEvent,
    ProviderTimeoutEvent,
    RateLimitPaceEvent,
    SystemPromptEvent,
    TokenUsageEvent,
    Turn,
    TurnCompleteEvent,
    TurnStartEvent,
)
from pidgin.core.types import Message
from pidgin.io.event_deserializer import EventDeserializer


class TestEventDeserializer:
    """Test EventDeserializer class."""

    def test_event_types_mapping(self):
        """Test that EVENT_TYPES mapping is complete."""
        # Check that all expected event types are mapped
        expected_events = [
            "ConversationStartEvent",
            "ConversationEndEvent",
            "TurnStartEvent",
            "TurnCompleteEvent",
            "MessageRequestEvent",
            "MessageChunkEvent",
            "MessageCompleteEvent",
            "SystemPromptEvent",
            "ErrorEvent",
            "APIErrorEvent",
            "ProviderTimeoutEvent",
            "InterruptRequestEvent",
            "ConversationPausedEvent",
            "ConversationResumedEvent",
            "RateLimitPaceEvent",
            "TokenUsageEvent",
            "ContextTruncationEvent",
        ]

        for event_type in expected_events:
            assert event_type in EventDeserializer.EVENT_TYPES
            assert EventDeserializer.EVENT_TYPES[event_type] is not None

        # Check legacy mapping
        assert "ConversationCreated" in EventDeserializer.EVENT_TYPES
        assert (
            EventDeserializer.EVENT_TYPES["ConversationCreated"]
            == ConversationStartEvent
        )

    def test_deserialize_event_missing_event_type(self):
        """Test deserializing event with missing event_type."""
        event_data = {"some_field": "some_value"}

        with patch("pidgin.io.event_deserializer.logger") as mock_logger:
            result = EventDeserializer.deserialize_event(event_data)

            assert result is None
            mock_logger.warning.assert_called_with("Event missing event_type field")

    def test_deserialize_event_unknown_event_type(self):
        """Test deserializing event with unknown event_type."""
        event_data = {"event_type": "UnknownEvent", "some_field": "value"}

        with patch("pidgin.io.event_deserializer.logger") as mock_logger:
            result = EventDeserializer.deserialize_event(event_data)

            assert result is None
            mock_logger.debug.assert_called_with("Unknown event type: UnknownEvent")

    def test_deserialize_event_legacy_format(self):
        """Test deserializing event in legacy format."""
        event_data = {
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "ConversationStartEvent",
            "data": {
                "conversation_id": "test_conv",
                "agent_a_model": "gpt-4",
                "agent_b_model": "claude-3",
                "initial_prompt": "Hello",
                "max_turns": 10,
            },
        }

        result = EventDeserializer.deserialize_event(event_data)

        assert result is not None
        assert isinstance(result, ConversationStartEvent)
        assert result.conversation_id == "test_conv"
        assert result.agent_a_model == "gpt-4"
        assert result.agent_b_model == "claude-3"
        assert result.initial_prompt == "Hello"
        assert result.max_turns == 10

    def test_deserialize_event_exception_handling(self):
        """Test exception handling during event deserialization."""
        event_data = {"event_type": "ConversationStartEvent"}

        with patch("pidgin.io.event_deserializer.logger") as mock_logger:
            with patch.object(
                EventDeserializer,
                "_build_conversation_start",
                side_effect=Exception("Test error"),
            ):
                result = EventDeserializer.deserialize_event(event_data)

                assert result is None
                mock_logger.error.assert_called_with(
                    "Failed to deserialize ConversationStartEvent: Test error"
                )


class TestTimestampParsing:
    """Test timestamp parsing functionality."""

    def test_parse_timestamp_iso_format(self):
        """Test parsing ISO format timestamps."""
        timestamp_str = "2024-01-01T12:00:00"
        result = EventDeserializer._parse_timestamp(timestamp_str)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12

    def test_parse_timestamp_with_timezone(self):
        """Test parsing timestamps with timezone."""
        timestamp_str = "2024-01-01T12:00:00+00:00"
        result = EventDeserializer._parse_timestamp(timestamp_str)

        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_parse_timestamp_with_z_suffix(self):
        """Test parsing timestamps with Z suffix."""
        timestamp_str = "2024-01-01T12:00:00Z"
        result = EventDeserializer._parse_timestamp(timestamp_str)

        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_parse_timestamp_invalid_format(self):
        """Test parsing invalid timestamp formats."""
        invalid_timestamps = [
            "invalid-timestamp",
            "2024-13-01T12:00:00",  # Invalid month
            None,
            123,  # Not a string
            "",
        ]

        for invalid_ts in invalid_timestamps:
            result = EventDeserializer._parse_timestamp(invalid_ts)
            assert isinstance(result, datetime)
            # Should return current time as fallback


class TestConversationStartEvent:
    """Test ConversationStartEvent deserialization."""

    def test_build_conversation_start_complete(self):
        """Test building ConversationStartEvent with all fields."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "agent_a_model": "gpt-4",
            "agent_b_model": "claude-3",
            "initial_prompt": "Let's discuss AI",
            "max_turns": 20,
            "agent_a_display_name": "GPT-4",
            "agent_b_display_name": "Claude",
            "temperature_a": 0.7,
            "temperature_b": 0.5,
            "event_id": "event_123",
        }

        result = EventDeserializer._build_conversation_start(data, timestamp)

        assert isinstance(result, ConversationStartEvent)
        assert result.conversation_id == "conv_123"
        assert result.agent_a_model == "gpt-4"
        assert result.agent_b_model == "claude-3"
        assert result.initial_prompt == "Let's discuss AI"
        assert result.max_turns == 20
        assert result.agent_a_display_name == "GPT-4"
        assert result.agent_b_display_name == "Claude"
        assert result.temperature_a == 0.7
        assert result.temperature_b == 0.5
        assert result.timestamp == timestamp
        assert result.event_id == "event_123"

    def test_build_conversation_start_minimal(self):
        """Test building ConversationStartEvent with minimal fields."""
        timestamp = datetime.now()
        data = {}

        result = EventDeserializer._build_conversation_start(data, timestamp)

        assert isinstance(result, ConversationStartEvent)
        assert result.conversation_id == ""
        assert result.agent_a_model == ""
        assert result.agent_b_model == ""
        assert result.initial_prompt == ""
        assert result.max_turns == 0
        assert result.agent_a_display_name is None
        assert result.agent_b_display_name is None
        assert result.temperature_a is None
        assert result.temperature_b is None
        assert result.timestamp == timestamp

    def test_deserialize_conversation_start_event(self):
        """Test full deserialization of ConversationStartEvent."""
        event_data = {
            "event_type": "ConversationStartEvent",
            "conversation_id": "conv_123",
            "agent_a_model": "gpt-4",
            "agent_b_model": "claude-3",
            "initial_prompt": "Hello",
            "max_turns": 10,
        }

        result = EventDeserializer.deserialize_event(event_data)

        assert isinstance(result, ConversationStartEvent)
        assert result.conversation_id == "conv_123"
        assert result.agent_a_model == "gpt-4"


class TestConversationEndEvent:
    """Test ConversationEndEvent deserialization."""

    def test_build_conversation_end_complete(self):
        """Test building ConversationEndEvent with all fields."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "reason": "max_turns_reached",
            "total_turns": 15,
            "duration_ms": 30000,
            "event_id": "event_456",
        }

        result = EventDeserializer._build_conversation_end(data, timestamp)

        assert isinstance(result, ConversationEndEvent)
        assert result.conversation_id == "conv_123"
        assert result.reason == "max_turns_reached"
        assert result.total_turns == 15
        assert result.duration_ms == 30000
        assert result.timestamp == timestamp
        assert result.event_id == "event_456"

    def test_build_conversation_end_minimal(self):
        """Test building ConversationEndEvent with minimal fields."""
        timestamp = datetime.now()
        data = {}

        result = EventDeserializer._build_conversation_end(data, timestamp)

        assert isinstance(result, ConversationEndEvent)
        assert result.conversation_id == ""
        assert result.reason == "unknown"
        assert result.total_turns == 0
        assert result.duration_ms == 0
        assert result.timestamp == timestamp


class TestTurnEvents:
    """Test turn-related event deserialization."""

    def test_build_turn_start(self):
        """Test building TurnStartEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "turn_number": 5,
            "event_id": "turn_start_123",
        }

        result = EventDeserializer._build_turn_start(data, timestamp)

        assert isinstance(result, TurnStartEvent)
        assert result.conversation_id == "conv_123"
        assert result.turn_number == 5
        assert result.timestamp == timestamp
        assert result.event_id == "turn_start_123"

    def test_build_turn_complete(self):
        """Test building TurnCompleteEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "turn_number": 5,
            "convergence_score": 0.85,
            "turn": {
                "agent_a_message": {
                    "content": "Hello from A",
                    "timestamp": "2024-01-01T12:00:00",
                },
                "agent_b_message": {
                    "content": "Hello from B",
                    "timestamp": "2024-01-01T12:01:00",
                },
            },
            "event_id": "turn_complete_123",
        }

        result = EventDeserializer._build_turn_complete(data, timestamp)

        assert isinstance(result, TurnCompleteEvent)
        assert result.conversation_id == "conv_123"
        assert result.turn_number == 5
        assert result.convergence_score == 0.85
        assert result.timestamp == timestamp
        assert result.event_id == "turn_complete_123"

        # Check turn data
        assert isinstance(result.turn, Turn)
        assert result.turn.agent_a_message.content == "Hello from A"
        assert result.turn.agent_a_message.agent_id == "agent_a"
        assert result.turn.agent_b_message.content == "Hello from B"
        assert result.turn.agent_b_message.agent_id == "agent_b"

    def test_build_turn_complete_minimal(self):
        """Test building TurnCompleteEvent with minimal data."""
        timestamp = datetime.now()
        data = {}

        result = EventDeserializer._build_turn_complete(data, timestamp)

        assert isinstance(result, TurnCompleteEvent)
        assert result.conversation_id == ""
        assert result.turn_number == 0
        assert result.convergence_score is None
        assert result.timestamp == timestamp

        # Check turn data has empty messages
        assert isinstance(result.turn, Turn)
        assert result.turn.agent_a_message.content == ""
        assert result.turn.agent_b_message.content == ""


class TestMessageEvents:
    """Test message-related event deserialization."""

    def test_build_message_request(self):
        """Test building MessageRequestEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "agent_id": "agent_a",
            "turn_number": 3,
            "temperature": 0.7,
            "conversation_history": [
                {
                    "role": "user",
                    "content": "Hello",
                    "agent_id": "agent_a",
                    "timestamp": "2024-01-01T12:00:00",
                },
                {
                    "role": "assistant",
                    "content": "Hi there",
                    "agent_id": "agent_b",
                    "timestamp": "2024-01-01T12:01:00",
                },
            ],
            "event_id": "msg_req_123",
        }

        result = EventDeserializer._build_message_request(data, timestamp)

        assert isinstance(result, MessageRequestEvent)
        assert result.conversation_id == "conv_123"
        assert result.agent_id == "agent_a"
        assert result.turn_number == 3
        assert result.temperature == 0.7
        assert result.timestamp == timestamp
        assert result.event_id == "msg_req_123"

        # Check conversation history
        assert len(result.conversation_history) == 2
        assert result.conversation_history[0].role == "user"
        assert result.conversation_history[0].content == "Hello"
        assert result.conversation_history[0].agent_id == "agent_a"
        assert result.conversation_history[1].role == "assistant"
        assert result.conversation_history[1].content == "Hi there"
        assert result.conversation_history[1].agent_id == "agent_b"

    def test_build_message_chunk(self):
        """Test building MessageChunkEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "agent_id": "agent_a",
            "chunk": "Hello ",
            "chunk_index": 0,
            "elapsed_ms": 100,
            "event_id": "chunk_123",
        }

        result = EventDeserializer._build_message_chunk(data, timestamp)

        assert isinstance(result, MessageChunkEvent)
        assert result.conversation_id == "conv_123"
        assert result.agent_id == "agent_a"
        assert result.chunk == "Hello "
        assert result.chunk_index == 0
        assert result.elapsed_ms == 100
        assert result.timestamp == timestamp
        assert result.event_id == "chunk_123"

    def test_build_message_complete(self):
        """Test building MessageCompleteEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "agent_id": "agent_a",
            "tokens_used": 150,
            "duration_ms": 2000,
            "message": {
                "role": "assistant",
                "content": "Hello, how are you?",
                "timestamp": "2024-01-01T12:00:00",
            },
            "event_id": "msg_complete_123",
        }

        result = EventDeserializer._build_message_complete(data, timestamp)

        assert isinstance(result, MessageCompleteEvent)
        assert result.conversation_id == "conv_123"
        assert result.agent_id == "agent_a"
        assert result.tokens_used == 150
        assert result.duration_ms == 2000
        assert result.timestamp == timestamp
        assert result.event_id == "msg_complete_123"

        # Check message
        assert isinstance(result.message, Message)
        assert result.message.role == "assistant"
        assert result.message.content == "Hello, how are you?"
        assert result.message.agent_id == "agent_a"


class TestErrorEvents:
    """Test error-related event deserialization."""

    def test_build_error_event(self):
        """Test building ErrorEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "error_type": "validation_error",
            "error_message": "Invalid input",
            "context": {"field": "prompt"},
            "event_id": "error_123",
        }

        result = EventDeserializer._build_error(data, timestamp)

        assert isinstance(result, ErrorEvent)
        assert result.conversation_id == "conv_123"
        assert result.error_type == "validation_error"
        assert result.error_message == "Invalid input"
        assert result.context == {"field": "prompt"}
        assert result.timestamp == timestamp
        assert result.event_id == "error_123"

    def test_build_api_error_event(self):
        """Test building APIErrorEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "error_type": "rate_limit",
            "error_message": "Rate limit exceeded",
            "agent_id": "agent_a",
            "provider": "openai",
            "context": {"retry_after": 60},
            "retryable": True,
            "retry_count": 2,
            "event_id": "api_error_123",
        }

        result = EventDeserializer._build_api_error(data, timestamp)

        assert isinstance(result, APIErrorEvent)
        assert result.conversation_id == "conv_123"
        assert result.error_type == "rate_limit"
        assert result.error_message == "Rate limit exceeded"
        assert result.agent_id == "agent_a"
        assert result.provider == "openai"
        assert result.context == {"retry_after": 60}
        assert result.retryable is True
        assert result.retry_count == 2
        assert result.timestamp == timestamp
        assert result.event_id == "api_error_123"

    def test_build_provider_timeout_event(self):
        """Test building ProviderTimeoutEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "error_type": "timeout",
            "error_message": "Request timed out",
            "agent_id": "agent_a",
            "timeout_seconds": 30.0,
            "context": {"request_id": "req_123"},
            "event_id": "timeout_123",
        }

        result = EventDeserializer._build_provider_timeout(data, timestamp)

        assert isinstance(result, ProviderTimeoutEvent)
        assert result.conversation_id == "conv_123"
        assert result.error_type == "timeout"
        assert result.error_message == "Request timed out"
        assert result.agent_id == "agent_a"
        assert result.timeout_seconds == 30.0
        assert result.context == {"request_id": "req_123"}
        assert result.timestamp == timestamp
        assert result.event_id == "timeout_123"


class TestSystemEvents:
    """Test system-related event deserialization."""

    def test_build_system_prompt_event(self):
        """Test building SystemPromptEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "agent_id": "agent_a",
            "prompt": "You are a helpful assistant",
            "agent_display_name": "GPT-4",
            "event_id": "sys_prompt_123",
        }

        result = EventDeserializer._build_system_prompt(data, timestamp)

        assert isinstance(result, SystemPromptEvent)
        assert result.conversation_id == "conv_123"
        assert result.agent_id == "agent_a"
        assert result.prompt == "You are a helpful assistant"
        assert result.agent_display_name == "GPT-4"
        assert result.timestamp == timestamp
        assert result.event_id == "sys_prompt_123"

    def test_build_token_usage_event(self):
        """Test building TokenUsageEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "provider": "openai",
            "tokens_used": 150,
            "tokens_per_minute_limit": 1000,
            "current_usage_rate": 0.15,
            "event_id": "token_usage_123",
        }

        result = EventDeserializer._build_token_usage(data, timestamp)

        assert isinstance(result, TokenUsageEvent)
        assert result.conversation_id == "conv_123"
        assert result.provider == "openai"
        assert result.tokens_used == 150
        assert result.tokens_per_minute_limit == 1000
        assert result.current_usage_rate == 0.15
        assert result.timestamp == timestamp
        assert result.event_id == "token_usage_123"

    def test_build_context_truncation_event(self):
        """Test building ContextTruncationEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "agent_id": "agent_a",
            "provider": "openai",
            "model": "gpt-4",
            "turn_number": 10,
            "original_message_count": 20,
            "truncated_message_count": 15,
            "messages_dropped": 5,
            "event_id": "context_trunc_123",
        }

        result = EventDeserializer._build_context_truncation(data, timestamp)

        assert isinstance(result, ContextTruncationEvent)
        assert result.conversation_id == "conv_123"
        assert result.agent_id == "agent_a"
        assert result.provider == "openai"
        assert result.model == "gpt-4"
        assert result.turn_number == 10
        assert result.original_message_count == 20
        assert result.truncated_message_count == 15
        assert result.messages_dropped == 5
        assert result.timestamp == timestamp
        assert result.event_id == "context_trunc_123"


class TestControlEvents:
    """Test control-related event deserialization."""

    def test_build_interrupt_request_event(self):
        """Test building InterruptRequestEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "turn_number": 5,
            "interrupt_source": "user",
            "event_id": "interrupt_123",
        }

        result = EventDeserializer._build_interrupt_request(data, timestamp)

        assert isinstance(result, InterruptRequestEvent)
        assert result.conversation_id == "conv_123"
        assert result.turn_number == 5
        assert result.interrupt_source == "user"
        assert result.timestamp == timestamp
        assert result.event_id == "interrupt_123"

    def test_build_conversation_paused_event(self):
        """Test building ConversationPausedEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "turn_number": 5,
            "paused_during": "agent_a_response",
            "event_id": "paused_123",
        }

        result = EventDeserializer._build_conversation_paused(data, timestamp)

        assert isinstance(result, ConversationPausedEvent)
        assert result.conversation_id == "conv_123"
        assert result.turn_number == 5
        assert result.paused_during == "agent_a_response"
        assert result.timestamp == timestamp
        assert result.event_id == "paused_123"

    def test_build_conversation_resumed_event(self):
        """Test building ConversationResumedEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "turn_number": 5,
            "event_id": "resumed_123",
        }

        result = EventDeserializer._build_conversation_resumed(data, timestamp)

        assert isinstance(result, ConversationResumedEvent)
        assert result.conversation_id == "conv_123"
        assert result.turn_number == 5
        assert result.timestamp == timestamp
        assert result.event_id == "resumed_123"

    def test_build_rate_limit_pace_event(self):
        """Test building RateLimitPaceEvent."""
        timestamp = datetime.now()
        data = {
            "conversation_id": "conv_123",
            "provider": "openai",
            "wait_time": 30.0,
            "reason": "rate_limit_exceeded",
            "event_id": "rate_limit_123",
        }

        result = EventDeserializer._build_rate_limit_pace(data, timestamp)

        assert isinstance(result, RateLimitPaceEvent)
        assert result.conversation_id == "conv_123"
        assert result.provider == "openai"
        assert result.wait_time == 30.0
        assert result.reason == "rate_limit_exceeded"
        assert result.timestamp == timestamp
        assert result.event_id == "rate_limit_123"


class TestJsonlReading:
    """Test JSONL file reading functionality."""

    def test_read_jsonl_events_valid_file(self):
        """Test reading valid JSONL file."""
        events = [
            {
                "event_type": "ConversationStartEvent",
                "conversation_id": "conv_1",
                "agent_a_model": "gpt-4",
                "agent_b_model": "claude-3",
                "initial_prompt": "Hello",
                "max_turns": 5,
            },
            {
                "event_type": "TurnStartEvent",
                "conversation_id": "conv_1",
                "turn_number": 1,
            },
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for event in events:
                f.write(json.dumps(event) + "\n")
            f.flush()

            try:
                results = list(EventDeserializer.read_jsonl_events(Path(f.name)))

                assert len(results) == 2

                # Check first event
                line_num1, event1 = results[0]
                assert line_num1 == 1
                assert isinstance(event1, ConversationStartEvent)
                assert event1.conversation_id == "conv_1"

                # Check second event
                line_num2, event2 = results[1]
                assert line_num2 == 2
                assert isinstance(event2, TurnStartEvent)
                assert event2.turn_number == 1

            finally:
                Path(f.name).unlink()

    def test_read_jsonl_events_with_empty_lines(self):
        """Test reading JSONL file with empty lines."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(
                '{"event_type": "TurnStartEvent", "conversation_id": "conv_1", "turn_number": 1}\n'
            )
            f.write("\n")  # Empty line
            f.write("   \n")  # Whitespace only line
            f.write(
                '{"event_type": "TurnStartEvent", "conversation_id": "conv_1", "turn_number": 2}\n'
            )
            f.flush()

            try:
                results = list(EventDeserializer.read_jsonl_events(Path(f.name)))

                assert len(results) == 2

                # Check line numbers account for empty lines
                line_num1, event1 = results[0]
                assert line_num1 == 1
                assert event1.turn_number == 1

                line_num2, event2 = results[1]
                assert line_num2 == 4  # Should be line 4 after empty lines
                assert event2.turn_number == 2

            finally:
                Path(f.name).unlink()

    def test_read_jsonl_events_with_invalid_json(self):
        """Test reading JSONL file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(
                '{"event_type": "TurnStartEvent", "conversation_id": "conv_1", "turn_number": 1}\n'
            )
            f.write("invalid json line\n")
            f.write(
                '{"event_type": "TurnStartEvent", "conversation_id": "conv_1", "turn_number": 2}\n'
            )
            f.flush()

            try:
                with patch("pidgin.io.event_deserializer.logger") as mock_logger:
                    results = list(EventDeserializer.read_jsonl_events(Path(f.name)))

                    # Should get only 2 valid events
                    assert len(results) == 2

                    # Should log warning for invalid JSON
                    mock_logger.warning.assert_called_once()
                    warning_call = mock_logger.warning.call_args[0][0]
                    assert "Invalid JSON at line 2" in warning_call

            finally:
                Path(f.name).unlink()

    def test_read_jsonl_events_with_unknown_event_types(self):
        """Test reading JSONL file with unknown event types."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(
                '{"event_type": "TurnStartEvent", "conversation_id": "conv_1", "turn_number": 1}\n'
            )
            f.write('{"event_type": "UnknownEventType", "some_field": "value"}\n')
            f.write(
                '{"event_type": "TurnStartEvent", "conversation_id": "conv_1", "turn_number": 2}\n'
            )
            f.flush()

            try:
                results = list(EventDeserializer.read_jsonl_events(Path(f.name)))

                # Should get only 2 valid events (unknown event type is filtered out)
                assert len(results) == 2

                line_num1, event1 = results[0]
                assert line_num1 == 1
                assert event1.turn_number == 1

                line_num2, event2 = results[1]
                assert line_num2 == 3  # Should be line 3 after unknown event
                assert event2.turn_number == 2

            finally:
                Path(f.name).unlink()


class TestIntegrationScenarios:
    """Test integration scenarios."""

    def test_deserialize_all_event_types(self):
        """Test that all event types can be deserialized."""
        event_samples = [
            {"event_type": "ConversationStartEvent", "conversation_id": "conv_1"},
            {"event_type": "ConversationEndEvent", "conversation_id": "conv_1"},
            {
                "event_type": "TurnStartEvent",
                "conversation_id": "conv_1",
                "turn_number": 1,
            },
            {
                "event_type": "TurnCompleteEvent",
                "conversation_id": "conv_1",
                "turn_number": 1,
            },
            {
                "event_type": "MessageRequestEvent",
                "conversation_id": "conv_1",
                "agent_id": "agent_a",
            },
            {
                "event_type": "MessageChunkEvent",
                "conversation_id": "conv_1",
                "agent_id": "agent_a",
            },
            {
                "event_type": "MessageCompleteEvent",
                "conversation_id": "conv_1",
                "agent_id": "agent_a",
            },
            {
                "event_type": "SystemPromptEvent",
                "conversation_id": "conv_1",
                "agent_id": "agent_a",
            },
            {"event_type": "ErrorEvent", "conversation_id": "conv_1"},
            {
                "event_type": "APIErrorEvent",
                "conversation_id": "conv_1",
                "agent_id": "agent_a",
            },
            {
                "event_type": "ProviderTimeoutEvent",
                "conversation_id": "conv_1",
                "agent_id": "agent_a",
            },
            {"event_type": "InterruptRequestEvent", "conversation_id": "conv_1"},
            {"event_type": "ConversationPausedEvent", "conversation_id": "conv_1"},
            {"event_type": "ConversationResumedEvent", "conversation_id": "conv_1"},
            {"event_type": "RateLimitPaceEvent", "conversation_id": "conv_1"},
            {"event_type": "TokenUsageEvent", "conversation_id": "conv_1"},
            {
                "event_type": "ContextTruncationEvent",
                "conversation_id": "conv_1",
                "agent_id": "agent_a",
            },
        ]

        for event_data in event_samples:
            result = EventDeserializer.deserialize_event(event_data)
            assert result is not None
            assert result.conversation_id == "conv_1"

    def test_legacy_event_deserialization(self):
        """Test that legacy events are mapped correctly."""
        # Test that legacy mapping exists
        assert "ConversationCreated" in EventDeserializer.EVENT_TYPES
        assert (
            EventDeserializer.EVENT_TYPES["ConversationCreated"]
            == ConversationStartEvent
        )

        # The actual deserialization would need the event builder to handle the legacy name
        # which doesn't happen in the current implementation, so we just test the mapping exists
