"""Test event-aware provider wrapper."""

from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from pidgin.core.event_bus import EventBus
from pidgin.core.events import (
    APIErrorEvent,
    MessageCompleteEvent,
    MessageRequestEvent,
    TokenUsageEvent,
)
from pidgin.core.types import Message
from pidgin.providers.base import Provider
from pidgin.providers.event_wrapper import EventAwareProvider
from tests.builders import make_message


class MockProvider(Provider):
    """Mock provider for testing."""

    def __init__(self, model: str = "test-model"):
        self.model = model
        self.last_usage = None
        self._stream_chunks = []
        self._should_raise = None

    async def stream_response(self, messages: List[Message], temperature=None):
        """Stream response implementation."""
        if self._should_raise:
            raise self._should_raise

        for chunk in self._stream_chunks:
            yield chunk

    def get_last_usage(self) -> Dict[str, Any]:
        """Return last usage data."""
        return self.last_usage

    def set_stream_chunks(self, chunks):
        """Set chunks to stream."""
        self._stream_chunks = chunks

    def set_error(self, error):
        """Set error to raise."""
        self._should_raise = error


class TestEventAwareProvider:
    """Test suite for EventAwareProvider."""

    @pytest.fixture
    def event_bus(self):
        """Create an event bus instance."""
        return EventBus()

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider."""
        return MockProvider()

    @pytest.fixture
    def wrapper(self, mock_provider, event_bus):
        """Create an event-aware wrapper."""
        return EventAwareProvider(
            provider=mock_provider, bus=event_bus, agent_id="test_agent"
        )

    def test_initialization(self, wrapper, mock_provider, event_bus):
        """Test wrapper initialization."""
        assert wrapper.provider == mock_provider
        assert wrapper.bus == event_bus
        assert wrapper.agent_id == "test_agent"
        assert wrapper.router is not None

    @pytest.mark.asyncio
    async def test_handle_message_request_wrong_agent(self, wrapper, event_bus):
        """Test that wrapper ignores requests for other agents."""
        event = MessageRequestEvent(
            conversation_id="test_conv",
            agent_id="other_agent",  # Different agent
            conversation_history=[],
            turn_number=1,
            temperature=0.7,
        )

        # Should return None (ignore event)
        result = await wrapper.handle_message_request(event)
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_message_request_success(
        self, wrapper, event_bus, mock_provider
    ):
        """Test successful message request handling."""
        # Setup mock provider response
        mock_provider.set_stream_chunks(["Hello ", "world!"])
        mock_provider.last_usage = {
            "total_tokens": 100,
            "prompt_tokens": 50,
            "completion_tokens": 50,
        }

        # Track emitted events
        emitted_events = []
        event_bus.subscribe(MessageCompleteEvent, lambda e: emitted_events.append(e))
        event_bus.subscribe(TokenUsageEvent, lambda e: emitted_events.append(e))

        # Create request event
        event = MessageRequestEvent(
            conversation_id="test_conv",
            agent_id="test_agent",
            conversation_history=[
                make_message("Hello", role="user"),
            ],
            turn_number=1,
            temperature=0.7,
        )

        # Mock the token tracker
        mock_tracker = Mock()
        mock_tracker.get_usage_stats.return_value = {
            "rate_limit": 1000000,
            "current_rate": 100,
        }

        # Handle the request
        with patch("time.time", side_effect=[1000.0, 1000.1]):  # 100ms duration
            with patch(
                "pidgin.providers.token_tracker.get_token_tracker",
                return_value=mock_tracker,
            ):
                await wrapper.handle_message_request(event)

        # Verify MessageCompleteEvent was emitted
        complete_events = [
            e for e in emitted_events if isinstance(e, MessageCompleteEvent)
        ]
        assert len(complete_events) == 1
        complete_event = complete_events[0]

        assert complete_event.conversation_id == "test_conv"
        assert complete_event.agent_id == "test_agent"
        assert complete_event.message.content == "Hello world!"
        assert complete_event.message.role == "assistant"
        assert complete_event.tokens_used == 50
        assert complete_event.duration_ms == 100

        # Verify TokenUsageEvent was emitted
        token_events = [e for e in emitted_events if isinstance(e, TokenUsageEvent)]
        assert len(token_events) == 1
        token_event = token_events[0]

        assert token_event.conversation_id == "test_conv"
        assert token_event.provider == "Mock"
        assert token_event.tokens_used == 100
        assert token_event.prompt_tokens == 50
        assert token_event.completion_tokens == 50
        assert hasattr(token_event, "model")
        assert token_event.model == "test-model"

    @pytest.mark.asyncio
    async def test_handle_message_request_api_error(
        self, wrapper, event_bus, mock_provider
    ):
        """Test API error handling."""
        # Setup mock provider to raise error
        mock_provider.set_error(Exception("Rate limit exceeded (429)"))

        # Track emitted events
        emitted_events = []
        event_bus.subscribe(APIErrorEvent, lambda e: emitted_events.append(e))

        # Create request event
        event = MessageRequestEvent(
            conversation_id="test_conv",
            agent_id="test_agent",
            conversation_history=[],
            turn_number=1,
            temperature=0.7,
        )

        # Handle the request - should raise
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await wrapper.handle_message_request(event)

        # Verify APIErrorEvent was emitted
        assert len(emitted_events) == 1
        error_event = emitted_events[0]

        assert error_event.conversation_id == "test_conv"
        assert error_event.error_type == "api_error"
        assert error_event.error_message == "Rate limit exceeded (429)"
        assert error_event.agent_id == "test_agent"
        assert error_event.provider == "Mock"
        assert error_event.retryable is True  # Rate limit errors are retryable
        assert error_event.context == "During message generation for turn 1"

    @pytest.mark.asyncio
    async def test_handle_message_request_non_retryable_error(
        self, wrapper, event_bus, mock_provider
    ):
        """Test non-retryable error handling."""
        # Setup mock provider to raise non-retryable error
        mock_provider.set_error(Exception("Invalid API key"))

        # Track emitted events
        emitted_events = []
        event_bus.subscribe(APIErrorEvent, lambda e: emitted_events.append(e))

        # Create request event
        event = MessageRequestEvent(
            conversation_id="test_conv",
            agent_id="test_agent",
            conversation_history=[],
            turn_number=1,
            temperature=0.7,
        )

        # Handle the request - should raise
        with pytest.raises(Exception, match="Invalid API key"):
            await wrapper.handle_message_request(event)

        # Verify error event
        assert len(emitted_events) == 1
        error_event = emitted_events[0]
        assert error_event.retryable is False  # Invalid API key is not retryable

    @pytest.mark.asyncio
    async def test_token_estimation_fallback(self, wrapper, event_bus):
        """Test token estimation when provider doesn't support usage tracking."""
        # Create a provider without get_last_usage
        provider_no_usage = Mock(spec=Provider)
        provider_no_usage.model = "test-model"
        # Ensure the provider doesn't have get_last_usage method
        if hasattr(provider_no_usage, "get_last_usage"):
            delattr(provider_no_usage, "get_last_usage")

        async def mock_stream(messages, temperature=None):
            yield "Test response"

        provider_no_usage.stream_response = mock_stream

        # Create wrapper with this provider
        wrapper_no_usage = EventAwareProvider(
            provider=provider_no_usage, bus=event_bus, agent_id="test_agent"
        )

        # Track emitted events
        emitted_events = []
        event_bus.subscribe(MessageCompleteEvent, lambda e: emitted_events.append(e))
        event_bus.subscribe(TokenUsageEvent, lambda e: emitted_events.append(e))

        # Create request event
        event = MessageRequestEvent(
            conversation_id="test_conv",
            agent_id="test_agent",
            conversation_history=[],
            turn_number=1,
            temperature=0.7,
        )

        # Handle the request
        await wrapper_no_usage.handle_message_request(event)

        # Verify MessageCompleteEvent was emitted with estimated tokens
        complete_events = [
            e for e in emitted_events if isinstance(e, MessageCompleteEvent)
        ]
        assert len(complete_events) == 1
        complete_event = complete_events[0]

        # Should have estimated tokens (roughly 3 tokens for "Test response")
        assert complete_event.tokens_used > 0

        # No TokenUsageEvent should be emitted without actual usage data
        token_events = [e for e in emitted_events if isinstance(e, TokenUsageEvent)]
        assert len(token_events) == 0

    @pytest.mark.asyncio
    async def test_message_transformation(self, wrapper, event_bus, mock_provider):
        """Test message history transformation for agent perspective."""
        # Setup mock provider
        mock_provider.set_stream_chunks(["Response"])

        # Create conversation history with multiple agents
        history = [
            make_message("Hello from A", agent_id="agent_a", role="user"),
            make_message("Hi from B", agent_id="agent_b", role="assistant"),
            make_message("Question from A", agent_id="agent_a", role="user"),
        ]

        # Spy on stream_response to capture messages
        original_stream = mock_provider.stream_response
        captured_messages = None

        async def capture_stream(messages, temperature=None):
            nonlocal captured_messages
            captured_messages = messages
            async for chunk in original_stream(messages, temperature):
                yield chunk

        mock_provider.stream_response = capture_stream

        # Create request event for agent_b
        wrapper.agent_id = "agent_b"
        event = MessageRequestEvent(
            conversation_id="test_conv",
            agent_id="agent_b",
            conversation_history=history,
            turn_number=2,
            temperature=0.7,
        )

        # Handle the request
        await wrapper.handle_message_request(event)

        # Verify message transformation
        assert captured_messages is not None
        # Agent B should see agent A's messages as "user" and its own as "assistant"
        assert len(captured_messages) == 3
        assert captured_messages[0].role == "user"
        assert captured_messages[0].content == "Hello from A"
        assert captured_messages[1].role == "assistant"
        assert captured_messages[1].content == "Hi from B"
        assert captured_messages[2].role == "user"
        assert captured_messages[2].content == "Question from A"

    @pytest.mark.asyncio
    async def test_token_usage_with_different_naming(
        self, wrapper, event_bus, mock_provider
    ):
        """Test token usage with different naming conventions (Anthropic vs OpenAI)."""
        # Setup mock provider response
        mock_provider.set_stream_chunks(["Response"])

        # Test with Anthropic-style naming (input_tokens/output_tokens)
        mock_provider.last_usage = {
            "total_tokens": 100,
            "input_tokens": 40,  # Anthropic style
            "output_tokens": 60,  # Anthropic style
        }

        # Track emitted events
        emitted_events = []
        event_bus.subscribe(TokenUsageEvent, lambda e: emitted_events.append(e))

        # Create request event
        event = MessageRequestEvent(
            conversation_id="test_conv",
            agent_id="test_agent",
            conversation_history=[],
            turn_number=1,
            temperature=0.7,
        )

        # Mock the token tracker
        mock_tracker = Mock()
        mock_tracker.get_usage_stats.return_value = {
            "rate_limit": 1000000,
            "current_rate": 500000,
        }

        # Handle the request
        with patch(
            "pidgin.providers.token_tracker.get_token_tracker",
            return_value=mock_tracker,
        ):
            await wrapper.handle_message_request(event)

        # Verify TokenUsageEvent handles different naming
        assert len(emitted_events) == 1
        token_event = emitted_events[0]

        assert token_event.prompt_tokens == 40
        assert token_event.completion_tokens == 60
        assert token_event.tokens_per_minute_limit == 1000000
        assert token_event.current_usage_rate == 500000
