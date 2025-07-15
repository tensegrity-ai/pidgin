"""Tests for TailDisplay class."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from rich.console import Console
from rich.text import Text

from pidgin.ui.tail_display import TailDisplay
from pidgin.core.event_bus import EventBus
from pidgin.core.events import (
    ConversationStartEvent,
    ConversationEndEvent,
    TurnStartEvent,
    TurnCompleteEvent,
    MessageRequestEvent,
    MessageCompleteEvent,
    MessageChunkEvent,
    SystemPromptEvent,
    APIErrorEvent,
    ContextTruncationEvent,
    RateLimitPaceEvent,
    TokenUsageEvent,
    ProviderTimeoutEvent,
    InterruptRequestEvent,
    ConversationPausedEvent,
    ConversationResumedEvent,
    Event,
)
from pidgin.core.types import Message


@pytest.fixture
def console():
    """Create a mock console for testing."""
    return MagicMock(spec=Console)


@pytest.fixture
def event_bus():
    """Create a mock event bus."""
    return MagicMock(spec=EventBus)


@pytest.fixture
def tail_display(event_bus, console):
    """Create a TailDisplay instance."""
    return TailDisplay(event_bus, console)


@pytest.fixture
def mock_message():
    """Create a mock message."""
    msg = Mock(spec=Message)
    msg.content = "Hello, this is a test message"
    msg.role = "user"
    return msg


class TestTailDisplay:
    """Test TailDisplay functionality."""

    def test_init_subscribes_to_events(self, event_bus, console):
        """Test that TailDisplay subscribes to all events."""
        display = TailDisplay(event_bus, console)
        
        # Should subscribe to all events
        event_bus.subscribe.assert_called_once_with(Event, display.log_event)
        
        # Should initialize instance variables
        assert display.bus == event_bus
        assert display.console == console
        assert display.chunk_buffer == {}

    def test_log_event_with_none_console(self, event_bus):
        """Test that log_event returns early if console is None."""
        display = TailDisplay(event_bus, None)
        
        # Create a mock event
        event = Mock(spec=Event)
        event.timestamp = datetime.now(timezone.utc)
        
        # Should return early and not crash
        display.log_event(event)

    def test_log_event_with_message_chunk(self, tail_display, console):
        """Test that log_event handles MessageChunkEvent separately."""
        event = Mock(spec=MessageChunkEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.chunk = "chunk content"
        event.agent_id = "agent_a"
        
        with patch.object(tail_display, '_handle_message_chunk') as mock_handler:
            tail_display.log_event(event)
            mock_handler.assert_called_once_with(event)

    def test_display_conversation_start_basic(self, tail_display, console):
        """Test conversation start event display."""
        event = Mock(spec=ConversationStartEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.conversation_id = "conv123456789012345"
        event.agent_a_model = "gpt-4"
        event.agent_b_model = "claude-3"
        event.max_turns = 10
        event.initial_prompt = None
        
        tail_display.log_event(event)
        
        # Should print header and content
        assert console.print.call_count == 1
        args = console.print.call_args[0]
        assert len(args) == 2  # header and content
        assert "conv12345678..." in args[1]  # Truncated to 12 chars
        assert "gpt-4 ↔ claude-3" in args[1]
        assert "max_turns: 10" in args[1]

    def test_display_conversation_start_with_prompt(self, tail_display, console):
        """Test conversation start event with initial prompt."""
        event = Mock(spec=ConversationStartEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.conversation_id = "conv123456789012345"
        event.agent_a_model = "gpt-4"
        event.agent_b_model = "claude-3"
        event.max_turns = 10
        event.initial_prompt = "What is the meaning of life?"
        
        with patch('pidgin.config.Config') as mock_config:
            config_instance = Mock()
            config_instance.get.return_value = "[HUMAN]"
            mock_config.return_value = config_instance
            
            tail_display.log_event(event)
            
            # Should print both conversation start and initial prompt
            assert console.print.call_count == 2
            
            # Check the first call (conversation start)
            first_call = console.print.call_args_list[0]
            assert "conv12345678..." in first_call[0][1]
            
            # Check the second call (initial prompt)
            second_call = console.print.call_args_list[1]
            assert "[HUMAN]: What is the meaning of life?" in second_call[0][1]

    def test_display_conversation_start_with_long_prompt(self, tail_display, console):
        """Test conversation start with long prompt gets truncated."""
        event = Mock(spec=ConversationStartEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.conversation_id = "conv123456789012345"
        event.agent_a_model = "gpt-4"
        event.agent_b_model = "claude-3"
        event.max_turns = 10
        event.initial_prompt = "This is a very long prompt that should be truncated because it exceeds the maximum length limit set in the display"
        
        with patch('pidgin.config.Config') as mock_config:
            config_instance = Mock()
            config_instance.get.return_value = "[HUMAN]"
            mock_config.return_value = config_instance
            
            tail_display.log_event(event)
            
            # Should print both conversation start and initial prompt
            assert console.print.call_count == 2
            
            # Check the first call (conversation start)
            first_call = console.print.call_args_list[0]
            assert "conv12345678..." in first_call[0][1]
            
            # Check the second call (initial prompt) - should be truncated
            second_call = console.print.call_args_list[1]
            assert "..." in second_call[0][1]
            assert "[HUMAN]:" in second_call[0][1]

    def test_display_conversation_end(self, tail_display, console):
        """Test conversation end event display."""
        event = Mock(spec=ConversationEndEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.reason = "max_turns_reached"
        event.total_turns = 10
        event.duration_ms = 120000
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "reason: max_turns" in args[1]
        assert "turns: 10" in args[1]
        assert "duration: 2m 0s" in args[1]

    def test_display_turn_start(self, tail_display, console):
        """Test turn start event display."""
        event = Mock(spec=TurnStartEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.turn_number = 5
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "Turn 5" in args[1]

    def test_display_turn_complete(self, tail_display, console):
        """Test turn complete event display."""
        event = Mock(spec=TurnCompleteEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.turn_number = 5
        event.convergence_score = 0.75
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "turn: 5" in args[1]
        assert "convergence: 0.750" in args[1]

    def test_display_message_request(self, tail_display, console):
        """Test message request event display."""
        event = Mock(spec=MessageRequestEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.agent_id = "agent_a"
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "[#a3be8c]agent_a[/#a3be8c] thinking..." in args[1]

    def test_display_message_complete(self, tail_display, console, mock_message):
        """Test message complete event display."""
        event = Mock(spec=MessageCompleteEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.agent_id = "agent_a"
        event.message = mock_message
        event.duration_ms = 2500
        event.tokens_used = 150
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "agent_a" in args[1]
        assert "Hello, this is a ..." in args[1]  # Truncated to 20 chars
        assert "2.5s" in args[1]
        assert "150tok" in args[1]

    def test_display_message_complete_with_long_message(self, tail_display, console):
        """Test message complete with long message gets truncated."""
        mock_message = Mock(spec=Message)
        mock_message.content = "This is a very long message that should be truncated"
        
        event = Mock(spec=MessageCompleteEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.agent_id = "agent_b"
        event.message = mock_message
        event.duration_ms = None
        event.tokens_used = None
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "This is a very lo..." in args[1]  # Truncated to 17 chars + ...
        assert "agent_b" in args[1]

    def test_handle_message_chunk(self, tail_display, console):
        """Test message chunk handling."""
        event = Mock(spec=MessageChunkEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.chunk = "chunk content here"
        event.agent_id = "agent_a"
        
        tail_display._handle_message_chunk(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "[#a3be8c]agent_a[/#a3be8c]: chunk content here" in args[1]

    def test_handle_message_chunk_with_content_attr(self, tail_display, console):
        """Test message chunk with content attribute instead of chunk."""
        event = Mock(spec=MessageChunkEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.content = "chunk content here"
        event.agent_id = "agent_a"
        # No chunk attribute
        
        tail_display._handle_message_chunk(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "[#a3be8c]agent_a[/#a3be8c]: chunk content here" in args[1]

    def test_display_api_error(self, tail_display, console):
        """Test API error event display."""
        event = Mock(spec=APIErrorEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.provider = "openai"
        event.error_type = "rate_limit"
        event.error_message = "Rate limit exceeded. Please try again later."
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "openai" in args[1]
        assert "rate_limit: Rate limit exceeded. Please try again later." in args[1]

    def test_display_context_truncation(self, tail_display, console):
        """Test context truncation event display."""
        event = Mock(spec=ContextTruncationEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.agent_id = "agent_a"
        event.messages_dropped = 5
        event.original_message_count = 20
        event.truncated_message_count = 15
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "agent_a" in args[1]
        assert "removed 5 msgs" in args[1]
        assert "20 → 15 msgs" in args[1]

    def test_display_system_prompt(self, tail_display, console):
        """Test system prompt event display."""
        event = Mock(spec=SystemPromptEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.agent_id = "agent_a"
        event.prompt = "You are a helpful assistant."
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "[#a3be8c]agent_a[/#a3be8c]: You are a helpful assistant." in args[1]

    def test_display_system_prompt_without_prompt(self, tail_display, console):
        """Test system prompt event without prompt text."""
        event = Mock(spec=SystemPromptEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.agent_id = "agent_a"
        event.prompt = None
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "[#a3be8c]agent_a[/#a3be8c] system prompt configured" in args[1]

    def test_display_rate_limit(self, tail_display, console):
        """Test rate limit event display."""
        event = Mock(spec=RateLimitPaceEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.reason = "mixed"
        event.wait_time = 30.5
        event.provider = "openai"
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "Waiting 30.5s for openai (request + token limits)" in args[1]

    def test_display_token_usage(self, tail_display, console):
        """Test token usage event display."""
        event = Mock(spec=TokenUsageEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.provider = "openai"
        event.tokens_used = 150
        event.current_usage_rate = 8000
        event.tokens_per_minute_limit = 10000
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "openai: 150 tokens" in args[1]
        assert "80% of limit (10000/min)" in args[1]

    def test_display_provider_timeout(self, tail_display, console):
        """Test provider timeout event display."""
        event = Mock(spec=ProviderTimeoutEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.agent_id = "agent_a"
        event.error_type = "timeout"
        event.error_message = "Request timed out"
        event.timeout_seconds = 30
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "[#a3be8c]agent_a[/#a3be8c] | timeout: Request timed out (timeout: 30s)" in args[1]

    def test_display_interrupt_request(self, tail_display, console):
        """Test interrupt request event display."""
        event = Mock(spec=InterruptRequestEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.interrupt_source = "user"
        event.turn_number = 5
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "Interrupt from user at turn 5" in args[1]

    def test_display_conversation_paused(self, tail_display, console):
        """Test conversation paused event display."""
        event = Mock(spec=ConversationPausedEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.turn_number = 5
        event.paused_during = "message_generation"
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "Paused at turn 5 (message_generation)" in args[1]

    def test_display_conversation_resumed(self, tail_display, console):
        """Test conversation resumed event display."""
        event = Mock(spec=ConversationResumedEvent)
        event.timestamp = datetime.now(timezone.utc)
        event.turn_number = 5
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "Resumed at turn 5" in args[1]

    def test_display_generic_event(self, tail_display, console):
        """Test generic event display."""
        # Create a mock event that has a dict method
        event = Mock()
        event.timestamp = datetime.now(timezone.utc)
        event.dict.return_value = {
            'custom_field': 'custom_value',
            'another_field': 'another_value',
            'timestamp': event.timestamp,
            'event_id': 'test123'
        }
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "custom_field: custom_value" in args[1]
        assert "another_field: another_value" in args[1]

    def test_display_generic_event_with_no_data(self, tail_display, console):
        """Test generic event with no useful data."""
        # Create a mock event with no useful data
        event = Mock()
        event.timestamp = datetime.now(timezone.utc)
        event.dict.return_value = {
            'empty_field': None,
            'blank_field': "",
            'timestamp': event.timestamp,
            'event_id': 'test123'
        }
        
        tail_display.log_event(event)
        
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert "(no data)" in args[1]

    def test_format_event_content_conversation_start(self, tail_display):
        """Test legacy format method for conversation start."""
        event = Mock(spec=ConversationStartEvent)
        event.conversation_id = "conv123"
        event.agent_a_model = "gpt-4"
        event.agent_b_model = "claude-3"
        event.temperature_a = 0.7
        event.temperature_b = 0.8
        event.initial_prompt = "What is the meaning of life?" * 10  # Long prompt
        event.max_turns = 10
        
        result = tail_display._format_event_content(event)
        
        assert "conversation_id: conv123" in result
        assert "agent_a: gpt-4 (temp: 0.7)" in result
        assert "agent_b: claude-3 (temp: 0.8)" in result
        assert "initial_prompt: " in result
        assert "max_turns: 10" in result

    def test_format_event_content_conversation_end(self, tail_display):
        """Test legacy format method for conversation end."""
        event = Mock(spec=ConversationEndEvent)
        event.conversation_id = "conv123"
        event.reason = "max_turns_reached"
        event.final_convergence = 0.85
        event.total_turns = 10
        event.duration_ms = 120000
        
        result = tail_display._format_event_content(event)
        
        assert "conversation_id: conv123" in result
        assert "reason: max_turns_reached" in result
        assert "final_convergence: 0.85" in result
        assert "total_turns: 10" in result
        assert "duration: 120000ms" in result

    def test_format_event_content_message_chunk(self, tail_display):
        """Test legacy format method for message chunk."""
        event = Mock(spec=MessageChunkEvent)
        event.content = "chunk content"
        
        result = tail_display._format_event_content(event)
        
        assert result == "chunk content"

    def test_format_event_content_generic(self, tail_display):
        """Test legacy format method for generic event."""
        # Create a mock event with dict method
        event = Mock()
        event.timestamp = datetime.now(timezone.utc)
        event.dict.return_value = {
            'field1': 'value1',
            'field2': None,
            'field3': 'value3',
            'timestamp': event.timestamp,
            'event_id': 'test123'
        }
        
        result = tail_display._format_event_content(event)
        
        assert "field1: value1" in result
        assert "field2" not in result  # None values should be skipped
        assert "field3: value3" in result
        assert "timestamp" not in result  # Should be removed