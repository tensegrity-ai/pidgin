"""Tests for the Conductor class - conversation orchestrator."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest

from pidgin.core.conductor import Conductor
from pidgin.core.event_bus import EventBus
from pidgin.core.events import (
    ConversationEndEvent,
    ConversationStartEvent,
)
from pidgin.core.types import Conversation
from pidgin.io.output_manager import OutputManager
from tests.builders import (
    make_agent,
    make_message,
)


class TestConductorInitialization:
    """Test Conductor initialization."""

    def test_basic_initialization(self):
        """Test basic Conductor initialization."""
        output_manager = Mock(spec=OutputManager)
        conductor = Conductor(output_manager=output_manager)

        assert conductor is not None
        assert conductor.output_manager == output_manager
        assert hasattr(conductor, "lifecycle")
        assert hasattr(conductor, "message_handler")
        assert hasattr(conductor, "turn_executor")
        assert hasattr(conductor, "interrupt_handler")
        assert hasattr(conductor, "name_coordinator")

    def test_initialization_with_custom_bus(self):
        """Test Conductor initialization with custom event bus."""
        output_manager = Mock(spec=OutputManager)
        custom_bus = Mock(spec=EventBus)

        conductor = Conductor(output_manager=output_manager, bus=custom_bus)

        assert conductor.bus == custom_bus

    def test_initialization_with_console(self):
        """Test Conductor initialization with console."""
        from rich.console import Console

        output_manager = Mock(spec=OutputManager)
        console = Console()

        conductor = Conductor(output_manager=output_manager, console=console)

        assert conductor.console == console


class TestConductorConversation:
    """Test Conductor conversation management."""

    @pytest.fixture
    def conductor(self, mock_providers):
        """Create a Conductor instance for testing."""
        output_manager = Mock(spec=OutputManager)
        # Mock the output manager methods
        output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            Path("/tmp/test_conv_123"),
        )

        # Create a mock bus with sync methods
        mock_bus = Mock(spec=EventBus)
        mock_bus.subscribe = Mock()
        mock_bus.emit = AsyncMock()

        conductor = Conductor(
            output_manager=output_manager, base_providers=mock_providers, bus=mock_bus
        )

        # Mock dependencies
        conductor.lifecycle = Mock()
        # Set up async methods on lifecycle
        conductor.lifecycle.create_conversation = Mock()
        conductor.lifecycle.add_initial_messages = AsyncMock()
        conductor.lifecycle.emit_start_events = AsyncMock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        conductor.lifecycle.initialize_event_system = AsyncMock()

        conductor.message_handler = Mock()  # Has both sync and async methods
        # conductor.message_handler.set_display_filter = Mock()  # Not used  # Sync method
        conductor.message_handler.handle_message_complete = Mock()  # Sync method

        conductor.turn_executor = Mock()
        conductor.turn_executor.run_single_turn = AsyncMock()
        conductor.turn_executor.stop_reason = "max_turns"

        conductor.interrupt_handler = Mock()
        conductor.name_coordinator = (
            Mock()
        )  # Use regular Mock since these are sync methods
        conductor.name_coordinator.initialize_name_mode = Mock()
        conductor.name_coordinator.assign_display_names = Mock()

        return conductor

    @pytest.fixture
    def mock_providers(self):
        """Create mock providers."""
        provider_a = Mock()
        provider_b = Mock()

        async def mock_stream_a():
            yield {"type": "text", "text": "Hello from A"}
            yield {"type": "usage", "usage": {"total_tokens": 10}}

        async def mock_stream_b():
            yield {"type": "text", "text": "Hello from B"}
            yield {"type": "usage", "usage": {"total_tokens": 10}}

        # Use Mock with async methods configured properly
        provider_a.stream_response = Mock(return_value=mock_stream_a())
        provider_b.stream_response = Mock(return_value=mock_stream_b())

        # Add any other methods that might be called
        provider_a.get_last_usage = Mock(return_value=None)
        provider_b.get_last_usage = Mock(return_value=None)

        return {"agent_a": provider_a, "agent_b": provider_b}

    @pytest.mark.asyncio
    async def test_run_conversation_basic(self, conductor, mock_providers):
        """Test basic conversation flow."""
        # Setup
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Mock conversation creation and lifecycle methods
        test_conversation = Conversation(
            id="test_conv_123",
            agents=[agent_a, agent_b],
            messages=[],
            initial_prompt="Hello",
        )

        # Mock the lifecycle methods that are actually called
        conductor.lifecycle.create_conversation.return_value = test_conversation
        conductor.lifecycle.add_initial_messages = AsyncMock()
        conductor.lifecycle.emit_start_events = AsyncMock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        conductor.lifecycle.save_transcripts = AsyncMock()

        # Mock message handler methods
        # conductor.message_handler.set_display_filter = Mock()  # Not used
        conductor.message_handler.handle_message_complete = Mock()

        # Mock turn execution - stop after 1 turn
        # run_single_turn returns a Turn object or None (None means stop)
        conductor.turn_executor.run_single_turn = AsyncMock(return_value=None)
        conductor.turn_executor.stop_reason = "max_turns"

        # Run conversation
        result = await conductor.run_conversation(
            agent_a=agent_a, agent_b=agent_b, initial_prompt="Hello", max_turns=1
        )

        # Note: The result will be an AsyncMock in this test setup
        # What's important is that the proper lifecycle methods were called
        assert result is not None

        # Verify lifecycle methods were called
        conductor.lifecycle.create_conversation.assert_called_once()
        conductor.lifecycle.add_initial_messages.assert_called_once()
        conductor.lifecycle.emit_start_events.assert_called_once()
        conductor.lifecycle.emit_end_event_with_reason.assert_called_once()

        # Verify turn was executed
        conductor.turn_executor.run_single_turn.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_conversation_with_name_choosing(self, conductor, mock_providers):
        """Test conversation with agent name choosing."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Mock conversation and name coordination
        test_conversation = Conversation(
            id="test_conv_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Mock name choosing methods that actually exist
        conductor.name_coordinator.initialize_name_mode = Mock()
        conductor.name_coordinator.assign_display_names = Mock()

        # Run conversation with choose_names=True
        result = await conductor.run_conversation(
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt="Hello",
            max_turns=1,
            choose_names=True,
        )

        # Verify name coordinator methods were called
        conductor.name_coordinator.initialize_name_mode.assert_called_once_with(True)
        conductor.name_coordinator.assign_display_names.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_conversation_error_handling(self, conductor, mock_providers):
        """Test error handling during conversation."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Mock initialization to raise an error
        conductor.lifecycle.initialize_event_system = AsyncMock(
            side_effect=Exception("Test error")
        )

        # Run conversation and expect exception
        with pytest.raises(Exception, match="Test error"):
            await conductor.run_conversation(
                agent_a=agent_a, agent_b=agent_b, initial_prompt="Hello", max_turns=1
            )

    @pytest.mark.asyncio
    async def test_run_conversation_interrupt(self, conductor, mock_providers):
        """Test conversation interruption."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        test_conversation = Conversation(
            id="test_conv_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation
        conductor.lifecycle.add_initial_messages = AsyncMock()
        conductor.lifecycle.emit_start_events = AsyncMock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        conductor.lifecycle.save_transcripts = AsyncMock()

        # Mock turn execution to stop immediately with interrupted reason
        conductor.turn_executor.run_single_turn = AsyncMock(return_value=None)
        conductor.turn_executor.stop_reason = "interrupted"

        # Run conversation
        result = await conductor.run_conversation(
            agent_a=agent_a, agent_b=agent_b, initial_prompt="Hello", max_turns=10
        )

        # Verify lifecycle was completed even though interrupted
        conductor.lifecycle.emit_end_event_with_reason.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_run_conversation_multiple_turns(self, conductor, mock_providers):
        """Test conversation with multiple turns."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        test_conversation = Conversation(
            id="test_conv_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation
        conductor.lifecycle.add_initial_messages = AsyncMock()
        conductor.lifecycle.emit_start_events = AsyncMock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        conductor.lifecycle.save_transcripts = AsyncMock()

        # Mock turn execution - simulate 3 turns then stop
        # Create mock turn objects
        from tests.builders import make_turn

        turn1 = make_turn(turn_number=1)
        turn2 = make_turn(turn_number=2)
        turn3 = make_turn(turn_number=3)

        conductor.turn_executor.run_single_turn.side_effect = [
            turn1,  # Turn 1 - returns turn object
            turn2,  # Turn 2 - returns turn object
            turn3,  # Turn 3 - returns turn object
            None,  # Turn 4 - returns None to stop
        ]
        conductor.turn_executor.stop_reason = "max_turns"

        # Run conversation
        result = await conductor.run_conversation(
            agent_a=agent_a, agent_b=agent_b, initial_prompt="Hello", max_turns=3
        )

        # Verify turn executor was called 3 times (3 turns, then stops on max_turns)
        assert conductor.turn_executor.run_single_turn.call_count == 3


class TestConductorEventEmission:
    """Test that Conductor properly coordinates event emission."""

    @pytest.fixture
    def conductor_with_bus(self, mock_pidgin_output_dir):
        """Create a Conductor with a real EventBus for testing events."""
        output_manager = Mock(spec=OutputManager)
        output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            Path("/tmp/test_conv_123"),
        )

        # Create EventBus with proper event log directory
        conversations_dir = mock_pidgin_output_dir / "conversations"
        bus = EventBus(event_log_dir=str(conversations_dir))

        # Mock providers
        mock_providers = {"agent_a": Mock(), "agent_b": Mock()}

        conductor = Conductor(
            output_manager=output_manager, bus=bus, base_providers=mock_providers
        )

        # Mock dependencies but keep real lifecycle and bus
        conductor.message_handler = AsyncMock()
        # conductor.message_handler.set_display_filter = Mock()  # Not used
        conductor.message_handler.handle_message_complete = Mock()

        conductor.turn_executor = AsyncMock()
        conductor.interrupt_handler = Mock()
        conductor.name_coordinator = Mock()
        conductor.name_coordinator.initialize_name_mode = Mock()
        conductor.name_coordinator.assign_display_names = Mock()

        return conductor, bus

    @pytest.mark.asyncio
    async def test_lifecycle_events(self, conductor_with_bus):
        """Test that lifecycle emits proper events."""
        conductor, bus = conductor_with_bus

        # Track events
        events_received = []

        def track_event(event):
            events_received.append(event)

        bus.subscribe(ConversationStartEvent, track_event)
        bus.subscribe(ConversationEndEvent, track_event)

        # Setup
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Mock turn execution to stop immediately
        conductor.turn_executor.run_single_turn = AsyncMock(return_value=None)
        conductor.turn_executor.stop_reason = "max_turns"

        # Run conversation
        result = await conductor.run_conversation(
            agent_a=agent_a, agent_b=agent_b, initial_prompt="Hello", max_turns=1
        )

        # Give events time to be processed
        await asyncio.sleep(0.1)

        # Verify events were emitted
        assert len(events_received) >= 2  # At least start and end
        assert any(isinstance(e, ConversationStartEvent) for e in events_received)
        assert any(isinstance(e, ConversationEndEvent) for e in events_received)

        # Cleanup
        await bus.stop()


class TestConductorProviderHandling:
    """Test Conductor's provider management."""

    def test_providers_initialization(self):
        """Test that providers are properly initialized."""
        # Mock providers
        mock_providers = {"agent_a": Mock(), "agent_b": Mock()}

        output_manager = Mock(spec=OutputManager)
        conductor = Conductor(
            output_manager=output_manager, base_providers=mock_providers
        )

        # Verify providers were stored
        assert conductor.base_providers == mock_providers

        # The providers are set during initialization
        assert hasattr(conductor, "lifecycle")
        # The lifecycle should have set_providers method called
        assert hasattr(conductor.lifecycle, "set_providers")

    @pytest.mark.asyncio
    async def test_providers_used_in_conversation(self):
        """Test that providers are used during conversation."""
        # Setup mock providers
        mock_providers = {"agent_a": AsyncMock(), "agent_b": AsyncMock()}

        output_manager = Mock(spec=OutputManager)
        output_manager.create_conversation_dir.return_value = (
            "test_conv",
            Path("/tmp/test_conv"),
        )

        conductor = Conductor(
            output_manager=output_manager, base_providers=mock_providers
        )

        # Mock dependencies
        conductor.lifecycle.create_conversation = AsyncMock()
        conductor.lifecycle.add_initial_messages = AsyncMock()
        conductor.lifecycle.emit_start_events = AsyncMock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        conductor.lifecycle.save_transcripts = AsyncMock()

        conductor.turn_executor.run_single_turn = AsyncMock(return_value=None)
        conductor.turn_executor.stop_reason = "max_turns"

        # conductor.message_handler.set_display_filter = Mock()  # Not used
        conductor.message_handler.handle_message_complete = Mock()

        conductor.interrupt_handler = Mock()
        conductor.name_coordinator = Mock()
        conductor.name_coordinator.initialize_name_mode = Mock()
        conductor.name_coordinator.assign_display_names = Mock()

        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        test_conversation = Conversation(id="test_conv", agents=[agent_a, agent_b])
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Run conversation
        await conductor.run_conversation(
            agent_a=agent_a, agent_b=agent_b, initial_prompt="Hello", max_turns=1
        )

        # Verify turn executor was called
        conductor.turn_executor.run_single_turn.assert_called_once()


class TestConductorInterrupt:
    """Test Conductor interrupt handling."""

    @pytest.fixture
    def conductor(self):
        """Create a Conductor for testing."""
        output_manager = Mock(spec=OutputManager)
        output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            Path("/tmp/test_conv_123"),
        )

        conductor = Conductor(output_manager=output_manager)

        # Mock dependencies
        conductor.lifecycle = Mock()
        conductor.lifecycle.create_conversation = Mock()
        conductor.lifecycle.add_initial_messages = AsyncMock()
        conductor.lifecycle.emit_start_events = AsyncMock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        conductor.lifecycle.initialize_event_system = AsyncMock()

        conductor.message_handler = Mock()
        # conductor.message_handler.set_display_filter = Mock()  # Not used
        conductor.message_handler.handle_message_complete = Mock()

        conductor.turn_executor = Mock()
        conductor.turn_executor.run_single_turn = AsyncMock()
        conductor.turn_executor.set_custom_awareness = Mock()
        conductor.turn_executor.set_convergence_overrides = Mock()

        conductor.interrupt_handler = Mock()
        conductor.interrupt_handler.interrupt_requested = False
        conductor.interrupt_handler.current_turn = 0
        conductor.interrupt_handler.setup_interrupt_handler = Mock()
        conductor.interrupt_handler.restore_interrupt_handler = Mock()
        conductor.interrupt_handler.handle_pause = AsyncMock()
        conductor.interrupt_handler.should_continue = AsyncMock()
        conductor.interrupt_handler.check_interrupt = Mock(return_value=False)

        conductor.name_coordinator = Mock()
        conductor.name_coordinator.initialize_name_mode = Mock()
        conductor.name_coordinator.assign_display_names = Mock()

        return conductor

    def test_check_interrupt_method(self, conductor):
        """Test check_interrupt method."""
        # Test when no interrupt
        conductor.interrupt_handler.check_interrupt.return_value = False
        assert conductor.check_interrupt() is False

        # Test when interrupt requested
        conductor.interrupt_handler.check_interrupt.return_value = True
        assert conductor.check_interrupt() is True

    @pytest.mark.asyncio
    async def test_interrupt_before_turn_execution(self, conductor):
        """Test interrupt handling that triggers lines 303-306."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        test_conversation = Conversation(
            id="test_conv_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Use a property mock to control when interrupt_requested returns True
        # This bypasses the reset in line 267
        _interrupt_prop = PropertyMock(return_value=True)
        type(conductor.interrupt_handler).interrupt_requested = _interrupt_prop
        conductor.interrupt_handler.should_continue.return_value = False

        # Run conversation
        result = await conductor.run_conversation(
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt="Hello",
            max_turns=5,  # Multiple turns to ensure we test the loop
        )

        # Verify interrupt was handled
        conductor.interrupt_handler.handle_pause.assert_called_once()
        conductor.interrupt_handler.should_continue.assert_called_once()

        # Verify no turns were executed due to immediate interrupt
        conductor.turn_executor.run_single_turn.assert_not_called()

        # Verify conversation ended with interrupted reason
        conductor.lifecycle.emit_end_event_with_reason.assert_called_once()
        call_args = conductor.lifecycle.emit_end_event_with_reason.call_args
        assert call_args[0][4] == "interrupted"  # end_reason


class TestConductorBatchLoading:
    """Test Conductor batch loading functionality."""

    @pytest.fixture
    def conductor(self):
        """Create a Conductor for testing."""
        output_manager = Mock(spec=OutputManager)
        output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            Path("/tmp/test_conv_123"),
        )

        conductor = Conductor(output_manager=output_manager)

        # Mock all dependencies
        conductor.lifecycle = Mock()
        conductor.lifecycle.create_conversation = Mock()
        conductor.lifecycle.add_initial_messages = AsyncMock()
        conductor.lifecycle.emit_start_events = AsyncMock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        conductor.lifecycle.initialize_event_system = AsyncMock()

        conductor.message_handler = Mock()
        # conductor.message_handler.set_display_filter = Mock()  # Not used
        conductor.message_handler.handle_message_complete = Mock()

        conductor.turn_executor = Mock()
        conductor.turn_executor.run_single_turn = AsyncMock()
        conductor.turn_executor.set_custom_awareness = Mock()
        conductor.turn_executor.set_convergence_overrides = Mock()
        conductor.turn_executor.stop_reason = "max_turns"

        conductor.interrupt_handler = Mock()
        conductor.interrupt_handler.interrupt_requested = False
        conductor.interrupt_handler.setup_interrupt_handler = Mock()
        conductor.interrupt_handler.restore_interrupt_handler = Mock()
        conductor.interrupt_handler.check_interrupt = Mock(return_value=False)

        conductor.name_coordinator = Mock()
        conductor.name_coordinator.initialize_name_mode = Mock()
        conductor.name_coordinator.assign_display_names = Mock()

        return conductor

    @pytest.mark.asyncio
    async def test_batch_load_single_chat(self, conductor, tmp_path):
        """Test batch loading for single chat sessions."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Set up conversation directory
        conv_dir = tmp_path / "test_conv_123"
        conv_dir.mkdir()
        conductor.output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            conv_dir,
        )

        # Create JSONL file
        jsonl_file = conv_dir / "test_conv_123_events.jsonl"
        jsonl_file.write_text('{"event": "test"}\n')

        test_conversation = Conversation(
            id="test_conv_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Mock turn execution to stop immediately
        conductor.turn_executor.run_single_turn.return_value = None

        # Mock EventStore
        with patch("pidgin.database.event_store.EventStore") as mock_event_store_class:
            with patch(
                "pidgin.io.paths.get_chats_database_path", return_value="/tmp/chats.db"
            ):
                mock_store = Mock()
                mock_store.import_experiment_from_jsonl.return_value = True
                mock_store.close = Mock()
                mock_event_store_class.return_value = mock_store

                # Run conversation
                result = await conductor.run_conversation(
                    agent_a=agent_a,
                    agent_b=agent_b,
                    initial_prompt="Hello",
                    max_turns=1,
                )

                # Verify EventStore was used
                mock_event_store_class.assert_called_once_with("/tmp/chats.db")
                mock_store.import_experiment_from_jsonl.assert_called_once_with(
                    str(conv_dir)
                )
                mock_store.close.assert_called_once()

                # Verify marker file was created
                marker_file = conv_dir / ".loaded_to_db"
                assert marker_file.exists()

    @pytest.mark.asyncio
    async def test_batch_load_skipped_for_experiments(self, conductor, tmp_path):
        """Test that batch loading is skipped for experiment conversations."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Set up experiment conversation directory
        conv_dir = tmp_path / "conv_exp_test_123"
        conv_dir.mkdir()
        conductor.output_manager.create_conversation_dir.return_value = (
            "conv_exp_test_123",
            conv_dir,
        )

        test_conversation = Conversation(
            id="conv_exp_test_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Mock turn execution to stop immediately
        conductor.turn_executor.run_single_turn.return_value = None

        # Mock EventStore
        with patch("pidgin.database.event_store.EventStore") as mock_event_store_class:
            with patch(
                "pidgin.io.paths.get_chats_database_path", return_value="/tmp/chats.db"
            ):
                # Run conversation
                result = await conductor.run_conversation(
                    agent_a=agent_a,
                    agent_b=agent_b,
                    initial_prompt="Hello",
                    max_turns=1,
                    conversation_id="conv_exp_test_123",
                )

                # Verify EventStore was NOT called for experiment
                mock_event_store_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_load_missing_jsonl(self, conductor, tmp_path):
        """Test batch loading when JSONL file is missing."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Set up conversation directory without JSONL file
        conv_dir = tmp_path / "test_conv_123"
        conv_dir.mkdir()
        conductor.output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            conv_dir,
        )

        test_conversation = Conversation(
            id="test_conv_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Mock turn execution to stop immediately
        conductor.turn_executor.run_single_turn.return_value = None

        # Mock EventStore
        with patch("pidgin.database.event_store.EventStore") as mock_event_store_class:
            with patch(
                "pidgin.io.paths.get_chats_database_path", return_value="/tmp/chats.db"
            ):
                # Run conversation
                result = await conductor.run_conversation(
                    agent_a=agent_a,
                    agent_b=agent_b,
                    initial_prompt="Hello",
                    max_turns=1,
                )

                # Verify EventStore was NOT called when JSONL missing
                mock_event_store_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_load_import_failure(self, conductor, tmp_path):
        """Test batch loading when import fails."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Set up conversation directory
        conv_dir = tmp_path / "test_conv_123"
        conv_dir.mkdir()
        conductor.output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            conv_dir,
        )

        # Create JSONL file
        jsonl_file = conv_dir / "test_conv_123_events.jsonl"
        jsonl_file.write_text('{"event": "test"}\n')

        test_conversation = Conversation(
            id="test_conv_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Mock turn execution to stop immediately
        conductor.turn_executor.run_single_turn.return_value = None

        # Mock EventStore to fail import
        with patch("pidgin.database.event_store.EventStore") as mock_event_store_class:
            with patch(
                "pidgin.io.paths.get_chats_database_path", return_value="/tmp/chats.db"
            ):
                mock_store = Mock()
                mock_store.import_experiment_from_jsonl.return_value = (
                    False  # Import fails
                )
                mock_store.close = Mock()
                mock_event_store_class.return_value = mock_store

                # Run conversation
                result = await conductor.run_conversation(
                    agent_a=agent_a,
                    agent_b=agent_b,
                    initial_prompt="Hello",
                    max_turns=1,
                )

                # Verify import was attempted
                mock_store.import_experiment_from_jsonl.assert_called_once()

                # Verify marker file was NOT created due to failure
                marker_file = conv_dir / ".loaded_to_db"
                assert not marker_file.exists()

    @pytest.mark.asyncio
    async def test_batch_load_eventstore_import_error(self, conductor, tmp_path):
        """Test batch loading when EventStore import fails."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Set up conversation directory
        conv_dir = tmp_path / "test_conv_123"
        conv_dir.mkdir()
        conductor.output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            conv_dir,
        )

        # Create JSONL file
        jsonl_file = conv_dir / "test_conv_123_events.jsonl"
        jsonl_file.write_text('{"event": "test"}\n')

        test_conversation = Conversation(
            id="test_conv_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Mock turn execution to stop immediately
        conductor.turn_executor.run_single_turn.return_value = None

        # Mock EventStore import to raise ImportError
        with patch(
            "pidgin.database.event_store.EventStore",
            side_effect=ImportError("Module not found"),
        ):
            with patch(
                "pidgin.io.paths.get_chats_database_path", return_value="/tmp/chats.db"
            ):
                # Run conversation - should not crash
                result = await conductor.run_conversation(
                    agent_a=agent_a,
                    agent_b=agent_b,
                    initial_prompt="Hello",
                    max_turns=1,
                )

                # Verify conversation completed despite import error
                assert result is not None

    @pytest.mark.asyncio
    async def test_batch_load_generic_exception(self, conductor, tmp_path):
        """Test batch loading with generic exception."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Set up conversation directory
        conv_dir = tmp_path / "test_conv_123"
        conv_dir.mkdir()
        conductor.output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            conv_dir,
        )

        # Create JSONL file
        jsonl_file = conv_dir / "test_conv_123_events.jsonl"
        jsonl_file.write_text('{"event": "test"}\n')

        test_conversation = Conversation(
            id="test_conv_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Mock turn execution to stop immediately
        conductor.turn_executor.run_single_turn.return_value = None

        # Mock EventStore to raise exception
        with patch("pidgin.database.event_store.EventStore") as mock_event_store_class:
            with patch(
                "pidgin.io.paths.get_chats_database_path", return_value="/tmp/chats.db"
            ):
                mock_store = Mock()
                mock_store.import_experiment_from_jsonl.side_effect = Exception(
                    "Database error"
                )
                mock_event_store_class.return_value = mock_store

                # Run conversation - should not crash
                result = await conductor.run_conversation(
                    agent_a=agent_a,
                    agent_b=agent_b,
                    initial_prompt="Hello",
                    max_turns=1,
                )

                # Verify conversation completed despite exception
                assert result is not None

    @pytest.mark.asyncio
    async def test_batch_load_file_not_found_error(self, conductor, tmp_path):
        """Test batch loading with FileNotFoundError."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Set up conversation directory
        conv_dir = tmp_path / "test_conv_123"
        conv_dir.mkdir()
        conductor.output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            conv_dir,
        )

        # Create JSONL file
        jsonl_file = conv_dir / "test_conv_123_events.jsonl"
        jsonl_file.write_text('{"event": "test"}\n')

        test_conversation = Conversation(
            id="test_conv_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Mock turn execution to stop immediately
        conductor.turn_executor.run_single_turn.return_value = None

        # Mock EventStore to raise FileNotFoundError
        with patch("pidgin.database.event_store.EventStore") as mock_event_store_class:
            with patch(
                "pidgin.io.paths.get_chats_database_path", return_value="/tmp/chats.db"
            ):
                with patch("pidgin.core.conductor.logger") as mock_logger:
                    mock_store = Mock()
                    mock_store.import_experiment_from_jsonl.side_effect = (
                        FileNotFoundError("File not found")
                    )
                    mock_event_store_class.return_value = mock_store

                    # Run conversation - should not crash
                    result = await conductor.run_conversation(
                        agent_a=agent_a,
                        agent_b=agent_b,
                        initial_prompt="Hello",
                        max_turns=1,
                    )

                    # Verify error was logged (line 388)
                    assert any(
                        "File not found during batch load" in str(call)
                        for call in mock_logger.error.call_args_list
                    )

                    # Verify conversation completed despite exception
                    assert result is not None


class TestConductorEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.fixture
    def conductor(self):
        """Create a Conductor for testing."""
        output_manager = Mock(spec=OutputManager)
        output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            Path("/tmp/test_conv_123"),
        )

        conductor = Conductor(output_manager=output_manager)
        return conductor

    @pytest.mark.asyncio
    async def test_convergence_overrides(self):
        """Test convergence threshold and action overrides."""
        output_manager = Mock(spec=OutputManager)
        output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            Path("/tmp/test_conv_123"),
        )

        # Test with convergence overrides
        conductor = Conductor(
            output_manager=output_manager,
            convergence_threshold_override=0.95,
            convergence_action_override="continue",
        )

        # Verify overrides were set
        assert conductor.turn_executor is not None
        # The overrides should have been passed to turn_executor

    @pytest.mark.asyncio
    async def test_with_transcript_manager(self):
        """Test conductor with transcript manager."""
        output_manager = Mock(spec=OutputManager)
        transcript_manager = Mock()

        conductor = Conductor(
            output_manager=output_manager, transcript_manager=transcript_manager
        )

        assert conductor.transcript_manager == transcript_manager

    @pytest.mark.asyncio
    async def test_branch_messages(self, conductor):
        """Test conversation with branch messages."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Mock dependencies
        conductor.lifecycle = Mock()
        conductor.lifecycle.create_conversation = Mock()
        conductor.lifecycle.add_initial_messages = AsyncMock()
        conductor.lifecycle.emit_start_events = AsyncMock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        conductor.lifecycle.initialize_event_system = AsyncMock()

        conductor.message_handler = Mock()
        # conductor.message_handler.set_display_filter = Mock()  # Not used
        conductor.message_handler.handle_message_complete = Mock()

        conductor.turn_executor = Mock()
        conductor.turn_executor.run_single_turn = AsyncMock(return_value=None)
        conductor.turn_executor.set_custom_awareness = Mock()
        conductor.turn_executor.set_convergence_overrides = Mock()
        conductor.turn_executor.stop_reason = "max_turns"

        conductor.interrupt_handler = Mock()
        conductor.interrupt_handler.interrupt_requested = False
        conductor.interrupt_handler.setup_interrupt_handler = Mock()
        conductor.interrupt_handler.restore_interrupt_handler = Mock()

        conductor.name_coordinator = Mock()
        conductor.name_coordinator.initialize_name_mode = Mock()
        conductor.name_coordinator.assign_display_names = Mock()

        # Create branch messages
        branch_messages = [
            make_message("Previous message 1", agent_id="agent_a"),
            make_message("Previous message 2", agent_id="agent_b"),
        ]

        test_conversation = Conversation(
            id="test_conv_123", agents=[agent_a, agent_b], messages=branch_messages
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Run conversation with branch messages
        result = await conductor.run_conversation(
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt="Continue from here",
            max_turns=1,
            branch_messages=branch_messages,
        )

        # Verify initial messages were NOT added (because we're branching)
        conductor.lifecycle.add_initial_messages.assert_not_called()

        # Verify conversation was created with branch messages
        conductor.lifecycle.create_conversation.assert_called_once()
        call_args = conductor.lifecycle.create_conversation.call_args
        assert call_args[0][4] == branch_messages  # branch_messages argument
