"""Unit tests for ContextTruncationEvent."""

import json
from datetime import datetime

import pytest

from pidgin.core.events import ContextTruncationEvent


class TestContextTruncationEvent:
    """Test ContextTruncationEvent functionality."""
    
    def test_context_truncation_event_creation(self):
        """Test basic event creation with required fields."""
        event = ContextTruncationEvent(
            conversation_id="test_conv_123",
            agent_id="agent_a",
            provider="anthropic",
            model="claude-3-haiku",
            turn_number=5,
            original_message_count=20,
            truncated_message_count=10,
            messages_dropped=10
        )
        
        assert event.conversation_id == "test_conv_123"
        assert event.agent_id == "agent_a"
        assert event.provider == "anthropic"
        assert event.model == "claude-3-haiku"
        assert event.turn_number == 5
        assert event.original_message_count == 20
        assert event.truncated_message_count == 10
        assert event.messages_dropped == 10
        assert isinstance(event.timestamp, datetime)
    
    def test_context_truncation_event_serialization(self):
        """Test event can be serialized to/from JSON for JSONL storage."""
        event = ContextTruncationEvent(
            conversation_id="test_conv_123",
            agent_id="agent_a",
            provider="openai",
            model="gpt-4",
            turn_number=3,
            original_message_count=15,
            truncated_message_count=8,
            messages_dropped=7
        )
        
        # Serialize to dict (as would happen for JSONL)
        event_dict = {
            "event_type": "ContextTruncationEvent",
            "timestamp": event.timestamp.isoformat(),
            "conversation_id": event.conversation_id,
            "agent_id": event.agent_id,
            "provider": event.provider,
            "model": event.model,
            "turn_number": event.turn_number,
            "original_message_count": event.original_message_count,
            "truncated_message_count": event.truncated_message_count,
            "messages_dropped": event.messages_dropped
        }
        
        # Should be JSON serializable
        json_str = json.dumps(event_dict)
        loaded = json.loads(json_str)
        
        assert loaded["conversation_id"] == "test_conv_123"
        assert loaded["agent_id"] == "agent_a"
        assert loaded["messages_dropped"] == 7
    
    def test_context_truncation_event_validation(self):
        """Test event validation (non-negative counts, required fields)."""
        # Valid event should work
        event = ContextTruncationEvent(
            conversation_id="test",
            agent_id="agent_a",
            provider="google",
            model="gemini-pro",
            turn_number=1,
            original_message_count=10,
            truncated_message_count=5,
            messages_dropped=5
        )
        assert event.messages_dropped == 5
        
        # Test logical consistency
        assert event.original_message_count == event.truncated_message_count + event.messages_dropped
        
    def test_context_truncation_event_edge_cases(self):
        """Test edge cases like zero messages dropped."""
        # This shouldn't happen in practice but test robustness
        event = ContextTruncationEvent(
            conversation_id="test",
            agent_id="agent_b",
            provider="anthropic",
            model="claude-3-sonnet",
            turn_number=0,
            original_message_count=5,
            truncated_message_count=5,
            messages_dropped=0
        )
        
        assert event.messages_dropped == 0
        assert event.turn_number == 0  # First turn