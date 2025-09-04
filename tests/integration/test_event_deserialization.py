"""Test event deserialization actually works end-to-end.

This is a regression test for the bug introduced in commit 760bf45 where
events couldn't be deserialized due to incorrect field passing.
"""

import json
import tempfile
from pathlib import Path

from pidgin.core.events import (
    ConversationEndEvent,
    ConversationStartEvent,
    MessageRequestEvent,
    SystemPromptEvent,
    TurnCompleteEvent,
    TurnStartEvent,
)
from pidgin.io.event_deserializer import EventDeserializer


def test_conversation_start_event_deserialization():
    """Test that ConversationStartEvent can be deserialized from JSONL."""
    # Create a sample event as it would be written to JSONL
    event_data = {
        "event_type": "ConversationStartEvent",
        "timestamp": "2024-01-01T12:00:00",
        "conversation_id": "test-conv-123",
        "agent_a": {"id": "agent_a", "model": "gpt-4"},
        "agent_b": {"id": "agent_b", "model": "claude-3"},
        "experiment_id": "exp-123",
        "config": {
            "initial_prompt": "Let's have a conversation",
            "max_turns": 10,
            "temperature_a": 0.7,
            "temperature_b": 0.8,
        },
    }

    # Deserialize the event
    deserializer = EventDeserializer()
    event = deserializer.deserialize_event(event_data)

    # Verify the event was deserialized correctly
    assert event is not None, "Event should not be None"
    assert isinstance(event, ConversationStartEvent)
    assert event.conversation_id == "test-conv-123"
    assert event.agent_a["model"] == "gpt-4"
    assert event.agent_b["model"] == "claude-3"
    assert event.config["initial_prompt"] == "Let's have a conversation"
    assert event.config["max_turns"] == 10


def test_turn_complete_event_deserialization():
    """Test that TurnCompleteEvent can be deserialized from JSONL."""
    event_data = {
        "event_type": "TurnCompleteEvent",
        "timestamp": "2024-01-01T12:00:05",
        "conversation_id": "test-conv-123",
        "turn_number": 1,
        "convergence_score": 0.75,
        "agent_a_message": "Hello there!",
        "agent_b_message": "Hi! Nice to meet you.",
        "agent_a_tokens": 10,
        "agent_b_tokens": 15,
    }

    deserializer = EventDeserializer()
    event = deserializer.deserialize_event(event_data)

    assert event is not None, "Event should not be None"
    assert isinstance(event, TurnCompleteEvent)
    assert event.conversation_id == "test-conv-123"
    assert event.turn_number == 1
    assert event.convergence_score == 0.75


def test_system_prompt_event_deserialization():
    """Test that SystemPromptEvent can be deserialized from JSONL."""
    event_data = {
        "event_type": "SystemPromptEvent",
        "timestamp": "2024-01-01T12:00:01",
        "conversation_id": "test-conv-123",
        "agent_id": "agent_a",
        "prompt": "You are a helpful assistant.",
        "agent_display_name": "Assistant A",
    }

    deserializer = EventDeserializer()
    event = deserializer.deserialize_event(event_data)

    assert event is not None, "Event should not be None"
    assert isinstance(event, SystemPromptEvent)
    assert event.conversation_id == "test-conv-123"
    assert event.agent_id == "agent_a"
    assert event.prompt == "You are a helpful assistant."
    assert event.agent_display_name == "Assistant A"


def test_message_request_event_deserialization():
    """Test that MessageRequestEvent can be deserialized from JSONL."""
    event_data = {
        "event_type": "MessageRequestEvent",
        "timestamp": "2024-01-01T12:00:02",
        "conversation_id": "test-conv-123",
        "agent_id": "agent_a",
        "turn_number": 1,
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ],
        "model": "gpt-4",
        "temperature": 0.7,
    }

    deserializer = EventDeserializer()
    event = deserializer.deserialize_event(event_data)

    assert event is not None, "Event should not be None"
    assert isinstance(event, MessageRequestEvent)
    assert event.conversation_id == "test-conv-123"
    assert event.agent_id == "agent_a"
    assert event.turn_number == 1
    # Note: MessageRequestEvent doesn't have a model field
    assert event.temperature == 0.7
    assert len(event.conversation_history) == 2


def test_full_conversation_deserialization():
    """Test deserializing a complete conversation from JSONL file."""
    # Create a temporary JSONL file with a full conversation
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        # Write a series of events that represent a conversation
        events = [
            {
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00",
                "conversation_id": "test-conv-full",
                "agent_a": {"id": "agent_a", "model": "gpt-4"},
                "agent_b": {"id": "agent_b", "model": "claude-3"},
                "config": {
                    "initial_prompt": "Discuss the weather",
                    "max_turns": 2,
                },
            },
            {
                "event_type": "SystemPromptEvent",
                "timestamp": "2024-01-01T12:00:01",
                "conversation_id": "test-conv-full",
                "agent_id": "agent_a",
                "prompt": "You are agent A",
            },
            {
                "event_type": "SystemPromptEvent",
                "timestamp": "2024-01-01T12:00:02",
                "conversation_id": "test-conv-full",
                "agent_id": "agent_b",
                "prompt": "You are agent B",
            },
            {
                "event_type": "TurnStartEvent",
                "timestamp": "2024-01-01T12:00:03",
                "conversation_id": "test-conv-full",
                "turn_number": 1,
            },
            {
                "event_type": "MessageRequestEvent",
                "timestamp": "2024-01-01T12:00:04",
                "conversation_id": "test-conv-full",
                "agent_id": "agent_a",
                "turn_number": 1,
                "messages": [],
            },
            {
                "event_type": "MessageRequestEvent",
                "timestamp": "2024-01-01T12:00:06",
                "conversation_id": "test-conv-full",
                "agent_id": "agent_b",
                "turn_number": 1,
                "messages": [],
            },
            {
                "event_type": "TurnCompleteEvent",
                "timestamp": "2024-01-01T12:00:08",
                "conversation_id": "test-conv-full",
                "turn_number": 1,
                "convergence_score": 0.5,
            },
            {
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:00:10",
                "conversation_id": "test-conv-full",
                "total_turns": 2,
                "status": "completed",
                "reason": "max_turns",
                "duration_ms": 10000,
            },
        ]

        for event in events:
            json.dump(event, f)
            f.write("\n")

        jsonl_path = Path(f.name)

    try:
        # Read and deserialize all events
        deserializer = EventDeserializer()
        deserialized_events = []
        errors = []

        for line_num, event in deserializer.read_jsonl_events(jsonl_path):
            if event is None:
                errors.append(f"Failed to deserialize line {line_num}")
            else:
                deserialized_events.append(event)

        # Verify all events were deserialized successfully
        assert len(errors) == 0, f"Deserialization errors: {errors}"
        assert len(deserialized_events) == len(events), (
            f"Expected {len(events)} events, got {len(deserialized_events)}"
        )

        # Verify event types
        assert isinstance(deserialized_events[0], ConversationStartEvent)
        assert isinstance(deserialized_events[1], SystemPromptEvent)
        assert isinstance(deserialized_events[2], SystemPromptEvent)
        assert isinstance(deserialized_events[3], TurnStartEvent)
        assert isinstance(deserialized_events[4], MessageRequestEvent)
        assert isinstance(deserialized_events[5], MessageRequestEvent)
        assert isinstance(deserialized_events[6], TurnCompleteEvent)
        assert isinstance(deserialized_events[7], ConversationEndEvent)

        # Verify key fields
        assert all(e.conversation_id == "test-conv-full" for e in deserialized_events)

    finally:
        # Clean up
        jsonl_path.unlink()


def test_handles_missing_optional_fields():
    """Test that deserialization handles missing optional fields gracefully."""
    # Minimal event data
    event_data = {
        "event_type": "ConversationStartEvent",
        "timestamp": "2024-01-01T12:00:00",
        "conversation_id": "minimal",
        "agent_a": {"id": "agent_a", "model": "model-a"},
        "agent_b": {"id": "agent_b", "model": "model-b"},
        # experiment_id and config are optional
    }

    deserializer = EventDeserializer()
    event = deserializer.deserialize_event(event_data)

    assert event is not None
    assert isinstance(event, ConversationStartEvent)
    assert event.experiment_id is None
    assert event.config == {}  # Should default to empty dict


def test_handles_extra_fields():
    """Test that deserialization ignores extra fields that don't belong."""
    event_data = {
        "event_type": "TurnStartEvent",
        "timestamp": "2024-01-01T12:00:00",
        "conversation_id": "test",
        "turn_number": 1,
        # These fields don't belong on TurnStartEvent
        "experiment_id": "should-be-ignored",
        "extra_field": "also-ignored",
        "random_data": 12345,
    }

    deserializer = EventDeserializer()
    event = deserializer.deserialize_event(event_data)

    # Should deserialize successfully, ignoring extra fields
    assert event is not None
    assert isinstance(event, TurnStartEvent)
    assert event.conversation_id == "test"
    assert event.turn_number == 1
    # These fields should not exist on the event
    assert not hasattr(event, "experiment_id")
    assert not hasattr(event, "extra_field")
    assert not hasattr(event, "random_data")


def test_system_events_deserialization():
    """Test that system events like TokenUsageEvent deserialize correctly."""
    from pidgin.core.events import (
        ContextTruncationEvent,
        InterruptRequestEvent,
        RateLimitPaceEvent,
        TokenUsageEvent,
    )

    deserializer = EventDeserializer()

    # Test TokenUsageEvent
    token_event_data = {
        "event_type": "TokenUsageEvent",
        "timestamp": "2024-01-01T00:00:00",
        "conversation_id": "test-123",
        "provider": "openai",
        "tokens_used": 150,
        "total_tokens": 150,  # Alternative field name
        "tokens_per_minute_limit": 10000,
        "current_usage_rate": 2.5,
    }

    event = deserializer.deserialize_event(token_event_data)
    assert event is not None
    assert isinstance(event, TokenUsageEvent)
    assert event.conversation_id == "test-123"
    assert event.provider == "openai"
    assert event.tokens_used == 150

    # Test RateLimitPaceEvent
    rate_limit_data = {
        "event_type": "RateLimitPaceEvent",
        "timestamp": "2024-01-01T00:00:00",
        "conversation_id": "test-123",
        "provider": "anthropic",
        "wait_time": 5.0,
        "wait_seconds": 5.0,  # Alternative field name
        "reason": "request_rate",
    }

    event = deserializer.deserialize_event(rate_limit_data)
    assert event is not None
    assert isinstance(event, RateLimitPaceEvent)
    assert event.conversation_id == "test-123"
    assert event.wait_time == 5.0

    # Test InterruptRequestEvent
    interrupt_data = {
        "event_type": "InterruptRequestEvent",
        "timestamp": "2024-01-01T00:00:00",
        "conversation_id": "test-123",
        "turn_number": 5,
        "interrupt_source": "user",
        "source": "user",  # Alternative field name
    }

    event = deserializer.deserialize_event(interrupt_data)
    assert event is not None
    assert isinstance(event, InterruptRequestEvent)
    assert event.conversation_id == "test-123"
    assert event.interrupt_source == "user"

    # Test ContextTruncationEvent
    truncation_data = {
        "event_type": "ContextTruncationEvent",
        "timestamp": "2024-01-01T00:00:00",
        "conversation_id": "test-123",
        "agent_id": "agent_a",
        "provider": "openai",
        "model": "gpt-4",
        "turn_number": 10,
        "original_message_count": 20,
        "messages_before": 20,  # Alternative field name
        "truncated_message_count": 15,
        "messages_after": 15,  # Alternative field name
        "messages_dropped": 5,
    }

    event = deserializer.deserialize_event(truncation_data)
    assert event is not None
    assert isinstance(event, ContextTruncationEvent)
    assert event.conversation_id == "test-123"
    assert event.messages_dropped == 5
