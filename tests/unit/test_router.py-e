"""Tests for Router and DirectRouter."""

from typing import AsyncIterator
from unittest.mock import AsyncMock, Mock

import pytest

from pidgin.core.router import DirectRouter, Router
from pidgin.core.types import Message
from tests.builders import make_message


class MockProvider:
    """Mock provider for testing."""

    def __init__(self, response_text: str = "Test response"):
        self.response_text = response_text
        self.stream_response = self._create_stream_mock()

    def _create_stream_mock(self):
        """Create a mock that returns an async generator."""

        async def _stream_response(messages):
            """Simulate streaming response."""
            # Return response in chunks
            words = self.response_text.split()
            for word in words:
                yield word + " "

        return _stream_response


class TestDirectRouter:
    """Test DirectRouter functionality."""

    @pytest.fixture
    def mock_providers(self):
        """Create mock providers for agents."""
        return {
            "agent_a": MockProvider("Hello from agent A"),
            "agent_b": MockProvider("Hello from agent B"),
        }

    @pytest.fixture
    def router(self, mock_providers):
        """Create a DirectRouter instance."""
        return DirectRouter(mock_providers)

    def test_init(self, router, mock_providers):
        """Test router initialization."""
        assert router.providers == mock_providers
        assert router.last_agent_id is None

    @pytest.mark.asyncio
    async def test_get_next_response_basic(self, router):
        """Test basic response generation."""
        history = [
            make_message(content="Hi there!", agent_id="agent_a", role="assistant")
        ]

        response = await router.get_next_response(history, "agent_b")

        assert isinstance(response, Message)
        assert response.agent_id == "agent_b"
        assert response.role == "assistant"
        assert response.content == "Hello from agent B "

    @pytest.mark.asyncio
    async def test_get_next_response_stream(self, router):
        """Test streaming response generation."""
        history = [
            make_message(content="Hi there!", agent_id="agent_a", role="assistant")
        ]

        chunks = []
        async for chunk, agent_id in router.get_next_response_stream(
            history, "agent_b"
        ):
            chunks.append(chunk)
            assert agent_id == "agent_b"

        assert len(chunks) == 4  # "Hello", "from", "agent", "B"
        assert "".join(chunks) == "Hello from agent B "

    def test_build_agent_history_empty(self, router):
        """Test building history with no messages."""
        history = []
        agent_history = router._build_agent_history(history, "agent_a")
        assert agent_history == []

    def test_build_agent_history_system_messages(self, router):
        """Test handling of system messages."""
        history = [
            make_message(
                content="You are Agent A in a conversation",
                agent_id="system",
                role="system",
            )
        ]

        # For agent_a, system message should pass through
        agent_a_history = router._build_agent_history(history, "agent_a")
        assert len(agent_a_history) == 1
        assert agent_a_history[0].content == "You are Agent A in a conversation"
        assert agent_a_history[0].role == "system"

        # For agent_b, system message should be adjusted
        agent_b_history = router._build_agent_history(history, "agent_b")
        assert len(agent_b_history) == 1
        assert "You are Agent B" in agent_b_history[0].content
        assert agent_b_history[0].role == "system"

    def test_build_agent_history_choose_names_mode(self, router):
        """Test handling of choose-names system prompt."""
        history = [
            make_message(
                content="Please choose a short name for yourself",
                agent_id="system",
                role="system",
            )
        ]

        # Choose names prompt should be the same for both agents
        agent_a_history = router._build_agent_history(history, "agent_a")
        agent_b_history = router._build_agent_history(history, "agent_b")

        assert agent_a_history[0].content == agent_b_history[0].content
        assert "Please choose a short name" in agent_a_history[0].content

    def test_build_agent_history_conversation_flow(self, router):
        """Test building history for normal conversation flow."""
        history = [
            make_message(content="Hello!", agent_id="agent_a", role="assistant"),
            make_message(content="Hi there!", agent_id="agent_b", role="assistant"),
            make_message(content="How are you?", agent_id="agent_a", role="assistant"),
        ]

        # Build history for agent_b
        agent_b_history = router._build_agent_history(history, "agent_b")

        assert len(agent_b_history) == 3

        # agent_a's messages should be user messages
        assert agent_b_history[0].role == "user"
        assert agent_b_history[0].content == "Hello!"

        # agent_b's own message should be assistant
        assert agent_b_history[1].role == "assistant"
        assert agent_b_history[1].content == "Hi there!"

        # agent_a's next message should be user
        assert agent_b_history[2].role == "user"
        assert agent_b_history[2].content == "How are you?"

    def test_build_agent_history_human_intervention(self, router):
        """Test handling of human/external messages."""
        history = [
            make_message(content="Start talking", agent_id="human", role="user"),
            make_message(content="Okay!", agent_id="agent_a", role="assistant"),
        ]

        agent_a_history = router._build_agent_history(history, "agent_a")

        # Human message should pass through as user message
        assert agent_a_history[0].role == "user"
        assert agent_a_history[0].content == "Start talking"
        assert agent_a_history[0].agent_id == "human"

        # Own message should be assistant
        assert agent_a_history[1].role == "assistant"
        assert agent_a_history[1].content == "Okay!"

    def test_build_agent_history_model_specific_names(self, router):
        """Test handling of model-specific names in system prompts."""
        history = [
            make_message(
                content="You are Sonnet-1. Your conversation partner (Sonnet-2) is ready.",
                agent_id="system",
                role="system",
            )
        ]

        # For agent_b, should swap Sonnet-1 and Sonnet-2
        agent_b_history = router._build_agent_history(history, "agent_b")
        assert "You are Sonnet-2" in agent_b_history[0].content
        assert "Your conversation partner (Sonnet-1)" in agent_b_history[0].content

    @pytest.mark.asyncio
    async def test_get_next_response_with_complex_history(self, router, mock_providers):
        """Test response generation with complex conversation history."""
        history = [
            make_message(content="You are Agent A", agent_id="system", role="system"),
            make_message(content="Let's discuss AI", agent_id="human", role="user"),
            make_message(content="Sounds good!", agent_id="agent_a", role="assistant"),
            make_message(content="I agree!", agent_id="agent_b", role="assistant"),
        ]

        # Track calls to the provider
        called_messages = []

        async def tracking_stream_response(messages):
            called_messages.extend(messages)
            for word in ["Test", "response", "from", "A"]:
                yield word + " "

        mock_providers["agent_a"].stream_response = tracking_stream_response

        # Get response from agent_a
        response = await router.get_next_response(history, "agent_a")

        # Verify correct history was passed
        assert len(called_messages) == 4  # system + human + own + other agent

        # Verify message roles
        assert called_messages[0].role == "system"
        assert called_messages[1].role == "user"  # human
        assert called_messages[2].role == "assistant"  # own
        assert called_messages[3].role == "user"  # other agent

    @pytest.mark.asyncio
    async def test_streaming_empty_response(self, router):
        """Test handling of empty streaming response."""
        # Create provider with empty response
        empty_provider = MockProvider("")
        router.providers["agent_a"] = empty_provider

        history = []

        chunks = []
        async for chunk, agent_id in router.get_next_response_stream(
            history, "agent_a"
        ):
            chunks.append(chunk)

        # Should handle empty response gracefully
        assert chunks == []

    def test_build_agent_history_preserves_agent_ids(self, router):
        """Test that agent IDs are preserved in history."""
        history = [
            make_message(content="Hello", agent_id="agent_a", role="assistant"),
            make_message(content="Hi", agent_id="agent_b", role="assistant"),
            make_message(content="Note", agent_id="observer", role="user"),
        ]

        agent_history = router._build_agent_history(history, "agent_a")

        # All messages should preserve their original agent_id
        assert all(
            msg.agent_id == orig.agent_id for msg, orig in zip(agent_history, history)
        )

    @pytest.mark.asyncio
    async def test_concurrent_responses(self, router):
        """Test handling concurrent response requests."""
        history = [make_message(content="Hello", agent_id="agent_a", role="assistant")]

        # Request responses from both agents concurrently
        import asyncio

        response_a, response_b = await asyncio.gather(
            router.get_next_response(history, "agent_a"),
            router.get_next_response(history, "agent_b"),
        )

        assert response_a.agent_id == "agent_a"
        assert response_b.agent_id == "agent_b"
        assert response_a.content == "Hello from agent A "
        assert response_b.content == "Hello from agent B "


class TestRouterProtocol:
    """Test Router protocol for completeness."""

    def test_router_protocol_methods_exist(self):
        """Test that Router protocol has required methods."""
        # This tests that the protocol methods exist and are callable
        import inspect

        # Check that all protocol methods are defined
        assert hasattr(Router, "stream_response")
        assert hasattr(Router, "get_next_response")
        assert hasattr(Router, "get_next_response_stream")

        # Check that they are coroutines
        assert inspect.iscoroutinefunction(Router.stream_response)
        assert inspect.iscoroutinefunction(Router.get_next_response)
        assert inspect.iscoroutinefunction(Router.get_next_response_stream)

    def test_direct_router_implements_protocol(self):
        """Test that DirectRouter implements the Router protocol."""
        # This confirms DirectRouter has all required methods
        mock_providers = {"agent_a": MockProvider()}
        router = DirectRouter(mock_providers)

        # Check that DirectRouter has all protocol methods
        assert hasattr(router, "get_next_response")
        assert hasattr(router, "get_next_response_stream")

        # Note: DirectRouter doesn't implement stream_response directly,
        # but it uses provider.stream_response internally

        # Verify the methods are callable
        import inspect

        assert inspect.iscoroutinefunction(router.get_next_response)
        assert inspect.isasyncgenfunction(router.get_next_response_stream)
