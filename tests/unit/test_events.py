"""Test event types."""
import pytest
from datetime import datetime
from tests.builders import (
    make_message,
    make_conversation_start_event,
    make_conversation_end_event,
    make_turn_start_event,
    make_turn_complete_event,
    make_message_request_event,
    make_message_chunk_event,
    make_message_complete_event,
    make_error_event,
    make_api_error_event,
    make_token_usage_event,
)
from pidgin.core.events import *


class TestConversationEvents:
    """Test conversation lifecycle events."""
    
    def test_conversation_start_event(self):
        """Test ConversationStartEvent creation and serialization."""
        event = make_conversation_start_event(
            conversation_id="test_123",
            agent_a_model="gpt-4",
            agent_b_model="claude-3",
            initial_prompt="Hello",
            max_turns=10
        )
        
        assert event.conversation_id == "test_123"
        assert event.agent_a_model == "gpt-4"
        assert event.agent_b_model == "claude-3"
        assert event.initial_prompt == "Hello"
        assert event.max_turns == 10
        assert hasattr(event, 'timestamp')
        assert hasattr(event, 'event_id')
    
    def test_conversation_end_event(self):
        """Test ConversationEndEvent creation."""
        event = make_conversation_end_event(
            conversation_id="test_123",
            total_turns=7,
            reason="high_convergence",
            duration_ms=5000
        )
        
        assert event.conversation_id == "test_123"
        assert event.total_turns == 7
        assert event.reason == "high_convergence"
        assert event.duration_ms == 5000
        assert hasattr(event, 'timestamp')
        assert hasattr(event, 'event_id')
    
    def test_event_serialization(self):
        """Test event can be serialized to dict."""
        import dataclasses
        event = make_conversation_start_event()
        
        # Test dataclass serialization
        data = dataclasses.asdict(event)
        assert 'event_id' in data
        assert 'timestamp' in data
        assert 'conversation_id' in data
        
        # Note: event_type is added by EventBus when serializing, not by the event itself
    
    def test_event_json_serialization(self):
        """Test event can be serialized to JSON."""
        import json
        import dataclasses
        event = make_conversation_start_event()
        
        # Convert to dict first, handling datetime
        data = dataclasses.asdict(event)
        data['timestamp'] = data['timestamp'].isoformat()
        json_str = json.dumps(data)
        
        assert isinstance(json_str, str)
        assert 'test_conv' in json_str


class TestTurnEvents:
    """Test turn-related events."""
    
    def test_turn_start_event(self):
        """Test TurnStartEvent creation."""
        event = make_turn_start_event(
            conversation_id="test_123",
            turn_number=3
        )
        
        assert event.conversation_id == "test_123"
        assert event.turn_number == 3
        assert hasattr(event, 'timestamp')
        assert hasattr(event, 'event_id')
    
    def test_turn_complete_event(self):
        """Test TurnCompleteEvent creation."""
        event = make_turn_complete_event(
            conversation_id="test_123",
            turn_number=3,
            convergence_score=0.75
        )
        
        assert event.conversation_id == "test_123"
        assert event.turn_number == 3
        assert event.turn is not None
        assert event.turn.agent_a_message is not None
        assert event.turn.agent_b_message is not None
        assert event.convergence_score == 0.75


class TestMessageEvents:
    """Test message-related events."""
    
    def test_message_request_event(self):
        """Test MessageRequestEvent creation."""
        history = [make_message("Hello", "agent_a")]
        event = make_message_request_event(
            conversation_id="test_123",
            agent_id="agent_b",
            turn_number=2,
            conversation_history=history,
            temperature=0.8
        )
        
        assert event.conversation_id == "test_123"
        assert event.agent_id == "agent_b"
        assert event.turn_number == 2
        assert len(event.conversation_history) == 1
        assert event.temperature == 0.8
    
    def test_message_chunk_event(self):
        """Test MessageChunkEvent creation."""
        event = make_message_chunk_event(
            conversation_id="test_123",
            agent_id="agent_a",
            chunk="Hello, ",
            chunk_index=0,
            elapsed_ms=50
        )
        
        assert event.conversation_id == "test_123"
        assert event.agent_id == "agent_a"
        assert event.chunk == "Hello, "
        assert event.chunk_index == 0
        assert event.elapsed_ms == 50
    
    def test_message_complete_event(self):
        """Test MessageCompleteEvent creation."""
        msg = make_message("Test content", "agent_a")
        event = make_message_complete_event(
            conversation_id="test_123",
            agent_id="agent_a",
            message=msg,
            tokens_used=50,
            duration_ms=100
        )
        
        assert event.conversation_id == "test_123"
        assert event.agent_id == "agent_a"
        assert event.message.content == "Test content"
        assert event.tokens_used == 50
        assert event.duration_ms == 100
    
    def test_message_complete_event_serialization(self):
        """Test MessageCompleteEvent with nested Message serialization."""
        from pidgin.core.event_bus import EventBus
        
        event = make_message_complete_event()
        
        # Use EventBus serialization which handles mixed dataclass/pydantic
        bus = EventBus()
        data = bus._serialize_object(event)
        
        assert 'message' in data
        assert isinstance(data['message'], dict)
        assert 'content' in data['message']
        assert 'agent_id' in data['message']


class TestErrorEvent:
    """Test error event."""
    
    def test_error_event_creation(self):
        """Test ErrorEvent creation."""
        event = make_error_event(
            conversation_id="test_123",
            error_type="RateLimitError",
            error_message="Rate limit exceeded"
        )
        
        assert event.conversation_id == "test_123"
        assert event.error_type == "RateLimitError"
        assert event.error_message == "Rate limit exceeded"
    
    def test_error_event_with_context(self):
        """Test ErrorEvent with context."""
        event = ErrorEvent(
            conversation_id="test_123",
            error_type="APIError",
            error_message="Service unavailable",
            context="During message generation"
        )
        
        assert event.context == "During message generation"
    
    def test_api_error_event(self):
        """Test APIErrorEvent creation."""
        event = make_api_error_event(
            conversation_id="test_123",
            error_type="RateLimitError",
            error_message="Rate limit exceeded",
            agent_id="agent_a",
            provider="openai",
            retryable=True,
            retry_count=2
        )
        
        assert event.conversation_id == "test_123"
        assert event.agent_id == "agent_a"
        assert event.provider == "openai"
        assert event.retryable is True
        assert event.retry_count == 2


class TestTokenUsageEvent:
    """Test token usage event."""
    
    def test_token_usage_event_creation(self):
        """Test TokenUsageEvent creation."""
        event = make_token_usage_event(
            conversation_id="test_123",
            provider="openai",
            tokens_used=150,
            tokens_per_minute_limit=10000,
            current_usage_rate=0.15
        )
        
        assert event.conversation_id == "test_123"
        assert event.provider == "openai"
        assert event.tokens_used == 150
        assert event.tokens_per_minute_limit == 10000
        assert event.current_usage_rate == 0.15
    


class TestRateLimitEvent:
    """Test rate limit event."""
    
    def test_rate_limit_pace_event(self):
        """Test RateLimitPaceEvent creation."""
        event = RateLimitPaceEvent(
            conversation_id="test_123",
            provider="openai",
            wait_time=2.5,
            reason="request_rate"
        )
        
        assert event.conversation_id == "test_123"
        assert event.provider == "openai"
        assert event.wait_time == 2.5
        assert event.reason == "request_rate"


class TestEventInheritance:
    """Test event base class behavior."""
    
    def test_all_events_have_base_fields(self):
        """Test that all events have required base fields."""
        events = [
            make_conversation_start_event(),
            make_conversation_end_event(),
            make_turn_start_event(),
            make_turn_complete_event(),
            make_message_request_event(),
            make_message_chunk_event(),
            make_message_complete_event(),
            make_error_event(),
            make_api_error_event(),
            make_token_usage_event()
        ]
        
        for event in events:
            assert hasattr(event, 'event_id')
            assert hasattr(event, 'timestamp')
            assert hasattr(event, 'conversation_id')
            assert isinstance(event.timestamp, datetime)
            assert len(event.event_id) > 0
    
    def test_event_equality(self):
        """Test event equality based on event_id."""
        event1 = make_conversation_start_event()
        event2 = make_conversation_start_event()
        
        # Different events should have different IDs
        assert event1.event_id != event2.event_id
        assert event1 != event2
        
        # Same event should equal itself
        assert event1 == event1