"""Comprehensive tests for ConversationLifecycle."""

import time
from unittest.mock import Mock, patch

import pytest

from pidgin.core.conversation_lifecycle import ConversationLifecycle
from pidgin.core.event_bus import EventBus
from pidgin.core.events import (
    ConversationEndEvent,
    ConversationStartEvent,
    Event,
    SystemPromptEvent,
)
from pidgin.core.types import Agent, Conversation, Message


class TestConversationLifecycleBasics:
    """Test basic ConversationLifecycle functionality."""

    def test_initialization(self):
        """Test ConversationLifecycle initialization."""
        console = Mock()
        lifecycle = ConversationLifecycle(console)

        assert lifecycle.console == console
        assert lifecycle.bus is None
        assert lifecycle._owns_bus is False
        assert lifecycle.db_store is None
        assert lifecycle._owns_db_store is False
        assert lifecycle.event_logger is None
        assert lifecycle.display_filter is None
        assert lifecycle.base_providers == {}
        assert lifecycle.wrapped_providers == {}
        assert lifecycle._end_event_emitted is False
        assert lifecycle.chat_display is None
        assert lifecycle.tail_display is None

    def test_set_providers(self):
        """Test setting base providers."""
        lifecycle = ConversationLifecycle()

        providers = {"agent_a": Mock(), "agent_b": Mock()}

        lifecycle.set_providers(providers)
        assert lifecycle.base_providers == providers

    def test_create_conversation(self):
        """Test creating a conversation."""
        lifecycle = ConversationLifecycle()

        agent_a = Agent(id="agent_a", model="model_a", display_name="Agent A")
        agent_b = Agent(id="agent_b", model="model_b", display_name="Agent B")

        conv = lifecycle.create_conversation(
            conv_id="test_conv_123",
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt="Hello",
        )

        assert conv.id == "test_conv_123"
        assert len(conv.agents) == 2
        assert conv.agents[0] == agent_a
        assert conv.agents[1] == agent_b
        assert conv.initial_prompt == "Hello"
        assert len(conv.messages) == 0

    def test_create_conversation_with_prepopulated_messages(self):
        """Test creating a conversation with pre-populated messages (for branching)."""
        lifecycle = ConversationLifecycle()

        agent_a = Agent(id="agent_a", model="model_a")
        agent_b = Agent(id="agent_b", model="model_b")

        pre_messages = [
            Message(role="user", content="Previous message 1", agent_id="agent_a"),
            Message(role="assistant", content="Previous message 2", agent_id="agent_b"),
        ]

        conv = lifecycle.create_conversation(
            conv_id="test_conv_123",
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt="Hello",
            pre_populated_messages=pre_messages,
        )

        assert len(conv.messages) == 2
        assert conv.messages[0].content == "Previous message 1"
        assert conv.messages[1].content == "Previous message 2"


class TestEventSystemInitialization:
    """Test event system initialization."""

    @pytest.mark.asyncio
    async def test_initialize_with_new_bus(self, tmp_path):
        """Test initializing with a new EventBus."""
        lifecycle = ConversationLifecycle()

        agents = {
            "agent_a": Agent(id="agent_a", model="model_a"),
            "agent_b": Agent(id="agent_b", model="model_b"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path,
            display_mode="normal",
            show_timing=False,
            agents=agents,
            existing_bus=None,
            db_store=None,
        )

        assert lifecycle.bus is not None
        assert lifecycle._owns_bus is True
        assert lifecycle.bus._running is True

        # Clean up
        await lifecycle.cleanup()

    @pytest.mark.asyncio
    async def test_initialize_with_existing_bus(self, tmp_path):
        """Test initializing with an existing EventBus."""
        existing_bus = EventBus()
        await existing_bus.start()

        lifecycle = ConversationLifecycle()

        agents = {
            "agent_a": Agent(id="agent_a", model="model_a"),
            "agent_b": Agent(id="agent_b", model="model_b"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path,
            display_mode="normal",
            show_timing=False,
            agents=agents,
            existing_bus=existing_bus,
            db_store=None,
        )

        assert lifecycle.bus == existing_bus
        assert lifecycle._owns_bus is False

        # Existing bus should still be running
        assert existing_bus._running is True

        # Clean up shouldn't stop the bus we don't own
        await lifecycle.cleanup()
        assert existing_bus._running is True

        # Clean up bus
        await existing_bus.stop()

    @pytest.mark.asyncio
    async def test_initialize_tail_display(self, tmp_path):
        """Test initializing with tail display mode."""
        console = Mock()
        lifecycle = ConversationLifecycle(console)

        agents = {
            "agent_a": Agent(id="agent_a", model="model_a"),
            "agent_b": Agent(id="agent_b", model="model_b"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="tail", show_timing=False, agents=agents
        )

        assert lifecycle.tail_display is not None
        assert lifecycle.chat_display is None
        assert lifecycle.display_filter is None

        await lifecycle.cleanup()

    @pytest.mark.asyncio
    async def test_initialize_chat_display(self, tmp_path):
        """Test initializing with chat display mode."""
        console = Mock()
        lifecycle = ConversationLifecycle(console)

        agents = {
            "agent_a": Agent(id="agent_a", model="model_a"),
            "agent_b": Agent(id="agent_b", model="model_b"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="chat", show_timing=False, agents=agents
        )

        assert lifecycle.chat_display is not None
        assert lifecycle.tail_display is None
        assert lifecycle.display_filter is None

        await lifecycle.cleanup()

    @pytest.mark.asyncio
    async def test_initialize_normal_display(self, tmp_path):
        """Test initializing with normal display mode."""
        console = Mock()
        lifecycle = ConversationLifecycle(console)

        agents = {
            "agent_a": Agent(id="agent_a", model="model_a"),
            "agent_b": Agent(id="agent_b", model="model_b"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="normal", show_timing=True, agents=agents
        )

        assert lifecycle.display_filter is not None
        assert lifecycle.tail_display is not None  # Still created for logging
        assert lifecycle.chat_display is None

        await lifecycle.cleanup()

    @pytest.mark.asyncio
    async def test_initialize_quiet_mode(self, tmp_path):
        """Test initializing with quiet display mode."""
        console = Mock()
        lifecycle = ConversationLifecycle(console)

        agents = {
            "agent_a": Agent(id="agent_a", model="model_a"),
            "agent_b": Agent(id="agent_b", model="model_b"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="quiet", show_timing=False, agents=agents
        )

        assert lifecycle.display_filter is not None
        assert lifecycle.tail_display is not None

        await lifecycle.cleanup()

    @pytest.mark.asyncio
    async def test_initialize_none_mode(self, tmp_path):
        """Test initializing with none display mode."""
        console = Mock()
        lifecycle = ConversationLifecycle(console)

        agents = {
            "agent_a": Agent(id="agent_a", model="model_a"),
            "agent_b": Agent(id="agent_b", model="model_b"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="none", show_timing=False, agents=agents
        )

        assert lifecycle.display_filter is None
        assert lifecycle.tail_display is not None  # Still created for file logging

        await lifecycle.cleanup()

    @pytest.mark.asyncio
    async def test_initialize_without_console(self, tmp_path):
        """Test initializing without console."""
        lifecycle = ConversationLifecycle(console=None)

        agents = {
            "agent_a": Agent(id="agent_a", model="model_a"),
            "agent_b": Agent(id="agent_b", model="model_b"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="normal", show_timing=False, agents=agents
        )

        assert lifecycle.display_filter is None
        assert lifecycle.tail_display is not None

        await lifecycle.cleanup()

    @pytest.mark.asyncio
    async def test_provider_wrapping(self, tmp_path):
        """Test that providers are properly wrapped with EventAwareProvider."""
        lifecycle = ConversationLifecycle()

        # Set base providers
        base_providers = {"agent_a": Mock(), "agent_b": Mock()}
        lifecycle.set_providers(base_providers)

        agents = {
            "agent_a": Agent(id="agent_a", model="model_a"),
            "agent_b": Agent(id="agent_b", model="model_b"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="normal", show_timing=False, agents=agents
        )

        # Check providers were wrapped
        assert "agent_a" in lifecycle.wrapped_providers
        assert "agent_b" in lifecycle.wrapped_providers
        assert (
            lifecycle.wrapped_providers["agent_a"].provider == base_providers["agent_a"]
        )
        assert (
            lifecycle.wrapped_providers["agent_b"].provider == base_providers["agent_b"]
        )

        await lifecycle.cleanup()


class TestMessageHandling:
    """Test message handling functionality."""

    @pytest.mark.asyncio
    async def test_add_initial_messages_with_system_prompts(self):
        """Test adding initial messages with system prompts."""
        lifecycle = ConversationLifecycle()

        agent_a = Agent(id="agent_a", model="model_a")
        agent_b = Agent(id="agent_b", model="model_b")
        conv = Conversation(agents=[agent_a, agent_b])

        system_prompts = {"agent_a": "You are Agent A", "agent_b": "You are Agent B"}

        await lifecycle.add_initial_messages(
            conversation=conv,
            system_prompts=system_prompts,
            initial_prompt="Hello world",
        )

        assert len(conv.messages) == 2
        assert conv.messages[0].role == "system"
        assert conv.messages[0].content == "You are Agent A"
        assert conv.messages[0].agent_id == "system"

        assert conv.messages[1].role == "user"
        assert "[HUMAN]" in conv.messages[1].content
        assert "Hello world" in conv.messages[1].content
        assert conv.messages[1].agent_id == "researcher"

    @pytest.mark.asyncio
    async def test_add_initial_messages_without_system_prompts(self):
        """Test adding initial messages without system prompts (chaos mode)."""
        lifecycle = ConversationLifecycle()

        agent_a = Agent(id="agent_a", model="model_a")
        agent_b = Agent(id="agent_b", model="model_b")
        conv = Conversation(agents=[agent_a, agent_b])

        system_prompts = {"agent_a": "", "agent_b": ""}  # Empty system prompt

        await lifecycle.add_initial_messages(
            conversation=conv,
            system_prompts=system_prompts,
            initial_prompt="Hello world",
        )

        assert len(conv.messages) == 1  # Only user message
        assert conv.messages[0].role == "user"
        assert "Hello world" in conv.messages[0].content

    @pytest.mark.asyncio
    async def test_add_initial_messages_with_custom_tag(self):
        """Test adding initial messages with custom prompt tag."""
        lifecycle = ConversationLifecycle()

        agent_a = Agent(id="agent_a", model="model_a")
        agent_b = Agent(id="agent_b", model="model_b")
        conv = Conversation(agents=[agent_a, agent_b])

        system_prompts = {"agent_a": "", "agent_b": ""}

        await lifecycle.add_initial_messages(
            conversation=conv,
            system_prompts=system_prompts,
            initial_prompt="Hello world",
            prompt_tag="[CUSTOM]",
        )

        assert len(conv.messages) == 1
        assert "[CUSTOM]" in conv.messages[0].content
        assert "Hello world" in conv.messages[0].content

    @pytest.mark.asyncio
    async def test_add_initial_messages_without_tag(self):
        """Test adding initial messages without prompt tag."""
        lifecycle = ConversationLifecycle()

        agent_a = Agent(id="agent_a", model="model_a")
        agent_b = Agent(id="agent_b", model="model_b")
        conv = Conversation(agents=[agent_a, agent_b])

        system_prompts = {"agent_a": "", "agent_b": ""}

        await lifecycle.add_initial_messages(
            conversation=conv,
            system_prompts=system_prompts,
            initial_prompt="Hello world",
            prompt_tag="",  # Empty tag
        )

        assert len(conv.messages) == 1
        assert conv.messages[0].content == "Hello world"  # No tag prepended


class TestEventEmission:
    """Test event emission functionality."""

    @pytest.mark.asyncio
    async def test_emit_start_events(self, tmp_path):
        """Test emitting start events."""
        lifecycle = ConversationLifecycle()

        # Initialize event system
        agents = {
            "agent_a": Agent(id="agent_a", model="model_a", display_name="Agent A"),
            "agent_b": Agent(id="agent_b", model="model_b", display_name="Agent B"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="none", show_timing=False, agents=agents
        )

        # Track emitted events
        emitted_events = []
        lifecycle.bus.subscribe(Event, lambda e: emitted_events.append(e))

        # Create conversation
        conv = Conversation(id="test_conv", agents=list(agents.values()))

        system_prompts = {"agent_a": "System prompt A", "agent_b": "System prompt B"}

        await lifecycle.emit_start_events(
            conversation=conv,
            agent_a=agents["agent_a"],
            agent_b=agents["agent_b"],
            initial_prompt="Test prompt",
            max_turns=10,
            system_prompts=system_prompts,
            temperature_a=0.7,
            temperature_b=0.8,
        )

        # Check events
        assert len(emitted_events) == 3  # ConversationStart + 2 SystemPrompt

        conv_start = emitted_events[0]
        assert isinstance(conv_start, ConversationStartEvent)
        assert conv_start.conversation_id == "test_conv"
        assert conv_start.agent_a_model == "model_a"
        assert conv_start.agent_b_model == "model_b"
        assert conv_start.initial_prompt == "Test prompt"
        assert conv_start.max_turns == 10
        assert conv_start.agent_a_display_name == "Agent A"
        assert conv_start.agent_b_display_name == "Agent B"
        assert conv_start.temperature_a == 0.7
        assert conv_start.temperature_b == 0.8

        sys_prompt_a = emitted_events[1]
        assert isinstance(sys_prompt_a, SystemPromptEvent)
        assert sys_prompt_a.agent_id == "agent_a"
        assert sys_prompt_a.prompt == "System prompt A"
        assert sys_prompt_a.agent_display_name == "Agent A"

        sys_prompt_b = emitted_events[2]
        assert isinstance(sys_prompt_b, SystemPromptEvent)
        assert sys_prompt_b.agent_id == "agent_b"
        assert sys_prompt_b.prompt == "System prompt B"

        await lifecycle.cleanup()

    @pytest.mark.asyncio
    async def test_emit_start_events_without_system_prompts(self, tmp_path):
        """Test emitting start events without system prompts."""
        lifecycle = ConversationLifecycle()

        agents = {
            "agent_a": Agent(id="agent_a", model="model_a"),
            "agent_b": Agent(id="agent_b", model="model_b"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="none", show_timing=False, agents=agents
        )

        emitted_events = []
        lifecycle.bus.subscribe(Event, lambda e: emitted_events.append(e))

        conv = Conversation(id="test_conv", agents=list(agents.values()))

        system_prompts = {"agent_a": "", "agent_b": ""}  # Empty  # Empty

        await lifecycle.emit_start_events(
            conversation=conv,
            agent_a=agents["agent_a"],
            agent_b=agents["agent_b"],
            initial_prompt="Test",
            max_turns=5,
            system_prompts=system_prompts,
            temperature_a=None,
            temperature_b=None,
        )

        # Only ConversationStart event, no SystemPrompt events
        assert len(emitted_events) == 1
        assert isinstance(emitted_events[0], ConversationStartEvent)

        await lifecycle.cleanup()

    @pytest.mark.asyncio
    async def test_emit_end_event_with_reason(self, tmp_path):
        """Test emitting end event with specific reason."""
        lifecycle = ConversationLifecycle()

        agents = {"agent_a": Agent(id="agent_a", model="model_a")}
        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="none", show_timing=False, agents=agents
        )

        emitted_events = []
        lifecycle.bus.subscribe(Event, lambda e: emitted_events.append(e))

        conv = Conversation(id="test_conv", agents=list(agents.values()))
        start_time = time.time() - 5  # 5 seconds ago

        await lifecycle.emit_end_event_with_reason(
            conversation=conv,
            final_turn=4,
            max_turns=10,
            start_time=start_time,
            reason="convergence_reached",
        )

        assert len(emitted_events) == 1
        end_event = emitted_events[0]
        assert isinstance(end_event, ConversationEndEvent)
        assert end_event.conversation_id == "test_conv"
        assert end_event.reason == "convergence_reached"
        assert end_event.total_turns == 5  # final_turn + 1
        assert end_event.duration_ms > 4000  # At least 4 seconds

        # Check that end event was marked as emitted
        assert lifecycle._end_event_emitted is True

        # Bus should be stopped since we own it
        assert lifecycle.bus._running is False

    @pytest.mark.asyncio
    async def test_emit_end_event_auto_reason_max_turns(self, tmp_path):
        """Test emitting end event with auto-determined reason (max turns)."""
        lifecycle = ConversationLifecycle()

        agents = {"agent_a": Agent(id="agent_a", model="model_a")}
        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="none", show_timing=False, agents=agents
        )

        emitted_events = []
        lifecycle.bus.subscribe(Event, lambda e: emitted_events.append(e))

        conv = Conversation(id="test_conv", agents=list(agents.values()))
        start_time = time.time()

        await lifecycle.emit_end_event_with_reason(
            conversation=conv,
            final_turn=9,  # Last turn (0-indexed)
            max_turns=10,
            start_time=start_time,
            reason=None,  # Auto-determine
        )

        assert len(emitted_events) == 1
        end_event = emitted_events[0]
        assert end_event.reason == "max_turns_reached"
        assert end_event.total_turns == 10

    @pytest.mark.asyncio
    async def test_emit_end_event_auto_reason_interrupted(self, tmp_path):
        """Test emitting end event with auto-determined reason (interrupted)."""
        lifecycle = ConversationLifecycle()

        agents = {"agent_a": Agent(id="agent_a", model="model_a")}
        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="none", show_timing=False, agents=agents
        )

        emitted_events = []
        lifecycle.bus.subscribe(Event, lambda e: emitted_events.append(e))

        conv = Conversation(id="test_conv", agents=list(agents.values()))
        start_time = time.time()

        await lifecycle.emit_end_event_with_reason(
            conversation=conv,
            final_turn=2,  # Stopped early
            max_turns=10,
            start_time=start_time,
            reason=None,  # Auto-determine
        )

        assert len(emitted_events) == 1
        end_event = emitted_events[0]
        assert end_event.reason == "interrupted"
        assert end_event.total_turns == 3

    @pytest.mark.asyncio
    async def test_emit_end_event_twice(self, tmp_path):
        """Test that emitting end event twice is handled properly."""
        console = Mock()
        lifecycle = ConversationLifecycle(console)

        agents = {"agent_a": Agent(id="agent_a", model="model_a")}
        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="none", show_timing=False, agents=agents
        )

        emitted_events = []
        lifecycle.bus.subscribe(Event, lambda e: emitted_events.append(e))

        conv = Conversation(id="test_conv", agents=list(agents.values()))
        start_time = time.time()

        # First emission
        await lifecycle.emit_end_event_with_reason(
            conversation=conv,
            final_turn=2,
            max_turns=10,
            start_time=start_time,
            reason="test",
        )

        # Second emission - should be blocked
        await lifecycle.emit_end_event_with_reason(
            conversation=conv,
            final_turn=3,
            max_turns=10,
            start_time=start_time,
            reason="test2",
        )

        # Only one end event should be emitted
        assert len(emitted_events) == 1
        assert emitted_events[0].reason == "test"

        # Console should have warning
        from pidgin.ui.display_utils import DisplayUtils

        with patch.object(DisplayUtils, "warning") as mock_warning:
            # Need to reset and try again to capture the warning
            lifecycle._end_event_emitted = True
            await lifecycle.emit_end_event_with_reason(
                conversation=conv,
                final_turn=3,
                max_turns=10,
                start_time=start_time,
                reason="test2",
            )
            # Warning should be called
            assert mock_warning.called

    @pytest.mark.asyncio
    async def test_emit_end_event_convenience_method(self, tmp_path):
        """Test the convenience emit_end_event method."""
        lifecycle = ConversationLifecycle()

        agents = {"agent_a": Agent(id="agent_a", model="model_a")}
        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="none", show_timing=False, agents=agents
        )

        emitted_events = []
        lifecycle.bus.subscribe(Event, lambda e: emitted_events.append(e))

        conv = Conversation(id="test_conv", agents=list(agents.values()))
        start_time = time.time()

        await lifecycle.emit_end_event(
            conversation=conv, final_turn=5, max_turns=10, start_time=start_time
        )

        assert len(emitted_events) == 1
        end_event = emitted_events[0]
        assert end_event.total_turns == 6
        # Reason should be auto-determined
        assert end_event.reason == "interrupted"  # Since 6 < 10


class TestCleanup:
    """Test cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_owned_bus(self, tmp_path):
        """Test cleanup when we own the event bus."""
        lifecycle = ConversationLifecycle()

        agents = {"agent_a": Agent(id="agent_a", model="model_a")}
        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="none", show_timing=False, agents=agents
        )

        assert lifecycle._owns_bus is True
        assert lifecycle.bus._running is True

        await lifecycle.cleanup()

        # Bus should be stopped
        assert lifecycle.bus._running is False

    @pytest.mark.asyncio
    async def test_cleanup_not_owned_bus(self, tmp_path):
        """Test cleanup when we don't own the event bus."""
        existing_bus = EventBus()
        await existing_bus.start()

        lifecycle = ConversationLifecycle()

        agents = {"agent_a": Agent(id="agent_a", model="model_a")}
        await lifecycle.initialize_event_system(
            conv_dir=tmp_path,
            display_mode="none",
            show_timing=False,
            agents=agents,
            existing_bus=existing_bus,
        )

        assert lifecycle._owns_bus is False
        assert existing_bus._running is True

        await lifecycle.cleanup()

        # Bus should still be running
        assert existing_bus._running is True

        # Clean up bus manually
        await existing_bus.stop()

    @pytest.mark.asyncio
    async def test_conversation_log_closure(self, tmp_path):
        """Test that conversation log is closed on end event."""
        lifecycle = ConversationLifecycle()

        agents = {"agent_a": Agent(id="agent_a", model="model_a")}
        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="none", show_timing=False, agents=agents
        )

        conv = Conversation(id="test_conv", agents=list(agents.values()))

        # Mock the close_conversation_log method
        lifecycle.bus.close_conversation_log = Mock()

        await lifecycle.emit_end_event_with_reason(
            conversation=conv,
            final_turn=0,
            max_turns=1,
            start_time=time.time(),
            reason="test",
        )

        # Should have called close_conversation_log
        lifecycle.bus.close_conversation_log.assert_called_once_with("test_conv")


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_provider_wrapping_partial(self, tmp_path):
        """Test provider wrapping with only one agent having a provider."""
        lifecycle = ConversationLifecycle()

        # Only set provider for agent_a
        base_providers = {
            "agent_a": Mock()
            # agent_b has no provider
        }
        lifecycle.set_providers(base_providers)

        agents = {
            "agent_a": Agent(id="agent_a", model="model_a"),
            "agent_b": Agent(id="agent_b", model="model_b"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path, display_mode="normal", show_timing=False, agents=agents
        )

        # Only agent_a should be wrapped
        assert "agent_a" in lifecycle.wrapped_providers
        assert "agent_b" not in lifecycle.wrapped_providers

        await lifecycle.cleanup()

    @pytest.mark.asyncio
    async def test_display_filter_with_prompt_tag(self, tmp_path):
        """Test display filter initialization with prompt tag."""
        console = Mock()
        lifecycle = ConversationLifecycle(console)

        agents = {
            "agent_a": Agent(id="agent_a", model="model_a"),
            "agent_b": Agent(id="agent_b", model="model_b"),
        }

        await lifecycle.initialize_event_system(
            conv_dir=tmp_path,
            display_mode="normal",
            show_timing=True,
            agents=agents,
            prompt_tag="[TEST]",
        )

        assert lifecycle.display_filter is not None
        # Verify prompt_tag was passed to display filter

        await lifecycle.cleanup()

    @pytest.mark.asyncio
    async def test_db_store_handling(self, tmp_path):
        """Test db_store parameter handling."""
        lifecycle = ConversationLifecycle()

        mock_db_store = Mock()

        agents = {"agent_a": Agent(id="agent_a", model="model_a")}
        await lifecycle.initialize_event_system(
            conv_dir=tmp_path,
            display_mode="none",
            show_timing=False,
            agents=agents,
            db_store=mock_db_store,
        )

        assert lifecycle.db_store == mock_db_store
        assert lifecycle._owns_db_store is False

        await lifecycle.cleanup()
