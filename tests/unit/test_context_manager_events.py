"""Unit tests for context truncation event emission."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from pidgin.core.events import ContextTruncationEvent
from pidgin.core.types import Message
from pidgin.providers.context_manager import ProviderContextManager


class TestContextManagerEvents:
    """Test ContextTruncationEvent emission in ProviderContextManager."""

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus."""
        bus = Mock()
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def context_manager(self):
        """Create a ProviderContextManager instance."""
        return ProviderContextManager()

    @pytest.fixture
    def sample_messages(self):
        """Create sample messages for testing."""
        messages = []
        # Add a system message
        messages.append(
            Message(
                role="system", content="You are a helpful assistant.", agent_id="system"
            )
        )
        # Add many conversation messages to trigger truncation
        for i in range(50):
            messages.append(
                Message(
                    role="assistant" if i % 2 == 0 else "user",
                    content=f"This is message {i} with some content to make it longer. "
                    * 10,
                    agent_id="agent_a" if i % 2 == 0 else "agent_b",
                )
            )
        return messages

    def test_no_event_when_no_truncation(self, context_manager, mock_event_bus):
        """Test that no event is emitted when messages fit within context."""
        # Create a short conversation that won't be truncated
        messages = [
            Message(role="system", content="System prompt", agent_id="system"),
            Message(role="user", content="Hello", agent_id="agent_a"),
            Message(role="assistant", content="Hi there!", agent_id="agent_b"),
        ]

        # Prepare context without truncation
        result = context_manager.prepare_context(
            messages,
            provider="anthropic",
            model="claude-3-haiku",
            event_bus=mock_event_bus,
            conversation_id="test_conv",
            agent_id="agent_a",
            turn_number=1,
        )

        # No truncation should have occurred
        assert len(result) == len(messages)
        # No event should have been emitted
        mock_event_bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_event_emitted_on_truncation(
        self, context_manager, mock_event_bus, sample_messages
    ):
        """Test that ContextTruncationEvent is emitted when truncation occurs."""
        # Prepare context with a low limit to force truncation
        with patch.object(
            ProviderContextManager, "CONTEXT_LIMITS", {"anthropic": 1000}
        ):
            result = context_manager.prepare_context(
                sample_messages,
                provider="anthropic",
                model="claude-3-haiku",
                event_bus=mock_event_bus,
                conversation_id="test_conv",
                agent_id="agent_a",
                turn_number=5,
            )

        # Truncation should have occurred
        assert len(result) < len(sample_messages)

        # Event should have been emitted
        mock_event_bus.emit.assert_called_once()

        # Check the emitted event
        call_args = mock_event_bus.emit.call_args[0]
        event = call_args[0]
        assert isinstance(event, ContextTruncationEvent)

    @pytest.mark.asyncio
    async def test_event_contains_correct_data(
        self, context_manager, mock_event_bus, sample_messages
    ):
        """Test that emitted event has accurate truncation statistics."""
        # Force truncation with low limit
        with patch.object(
            ProviderContextManager, "CONTEXT_LIMITS", {"anthropic": 1000}
        ):
            result = context_manager.prepare_context(
                sample_messages,
                provider="anthropic",
                model="claude-3-haiku",
                event_bus=mock_event_bus,
                conversation_id="test_conv_123",
                agent_id="agent_b",
                turn_number=10,
            )

        # Get the emitted event
        event = mock_event_bus.emit.call_args[0][0]

        # Verify event data
        assert event.conversation_id == "test_conv_123"
        assert event.agent_id == "agent_b"
        assert event.provider == "anthropic"
        assert event.model == "claude-3-haiku"
        assert event.turn_number == 10
        assert event.original_message_count == len(sample_messages)
        assert event.truncated_message_count == len(result)
        assert event.messages_dropped == len(sample_messages) - len(result)
        assert event.messages_dropped > 0  # Some truncation occurred

    def test_truncation_without_event_bus(self, context_manager, sample_messages):
        """Test that truncation works normally when no event bus provided."""
        # Force truncation but don't provide event bus
        with patch.object(
            ProviderContextManager, "CONTEXT_LIMITS", {"anthropic": 1000}
        ):
            result = context_manager.prepare_context(
                sample_messages,
                provider="anthropic",
                model="claude-3-haiku",
                # No event_bus parameter
            )

        # Truncation should still work
        assert len(result) < len(sample_messages)
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_event_emission_failure_doesnt_break_truncation(
        self, context_manager, mock_event_bus, sample_messages
    ):
        """Test that failed event emission doesn't prevent truncation from working."""
        # Make event emission fail
        mock_event_bus.emit.side_effect = Exception("Event bus error")

        # Force truncation
        with patch.object(
            ProviderContextManager, "CONTEXT_LIMITS", {"anthropic": 1000}
        ):
            # This should not raise an exception
            result = context_manager.prepare_context(
                sample_messages,
                provider="anthropic",
                model="claude-3-haiku",
                event_bus=mock_event_bus,
                conversation_id="test_conv",
                agent_id="agent_a",
                turn_number=5,
            )

        # Truncation should have completed successfully
        assert len(result) < len(sample_messages)

        # Event emission was attempted
        mock_event_bus.emit.assert_called_once()

    def test_exact_boundary_no_truncation(self, context_manager, mock_event_bus):
        """Test boundary case where messages exactly fit the limit."""
        # Create messages that just fit
        messages = [
            Message(role="system", content="System", agent_id="system"),
            Message(role="user", content="Test message", agent_id="agent_a"),
        ]

        # Set limit to exactly accommodate these messages
        # Assuming ~3.5 chars per token, these messages are ~20 tokens
        with patch.object(ProviderContextManager, "CONTEXT_LIMITS", {"openai": 25}):
            result = context_manager.prepare_context(
                messages,
                provider="openai",
                model="gpt-4",
                event_bus=mock_event_bus,
                conversation_id="boundary_test",
                agent_id="agent_a",
                turn_number=1,
            )

        # No truncation should occur
        assert len(result) == len(messages)
        # No event should be emitted
        mock_event_bus.emit.assert_not_called()
