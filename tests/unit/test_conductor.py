"""Tests for the Conductor class - conversation orchestrator."""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from tests.builders import (
    make_agent,
    make_message,
    make_conversation_start_event,
    make_conversation_end_event,
    make_turn_start_event,
    make_turn_complete_event,
    make_message_complete_event
)
from pidgin.core.conductor import Conductor
from pidgin.core.types import Agent, Message, Conversation
from pidgin.core.events import (
    ConversationStartEvent,
    ConversationEndEvent,
    TurnStartEvent,
    TurnCompleteEvent,
    MessageCompleteEvent
)
import asyncio
from pidgin.io.output_manager import OutputManager
from pidgin.core.event_bus import EventBus


class TestConductorInitialization:
    """Test Conductor initialization."""
    
    def test_basic_initialization(self):
        """Test basic Conductor initialization."""
        output_manager = Mock(spec=OutputManager)
        conductor = Conductor(output_manager=output_manager)
        
        assert conductor is not None
        assert conductor.output_manager == output_manager
        assert hasattr(conductor, 'lifecycle')
        assert hasattr(conductor, 'message_handler')
        assert hasattr(conductor, 'turn_executor')
        assert hasattr(conductor, 'interrupt_handler')
        assert hasattr(conductor, 'name_coordinator')
    
    def test_initialization_with_custom_bus(self):
        """Test Conductor initialization with custom event bus."""
        output_manager = Mock(spec=OutputManager)
        custom_bus = Mock(spec=EventBus)
        
        conductor = Conductor(
            output_manager=output_manager,
            bus=custom_bus
        )
        
        assert conductor.bus == custom_bus
    
    def test_initialization_with_console(self):
        """Test Conductor initialization with console."""
        from rich.console import Console
        
        output_manager = Mock(spec=OutputManager)
        console = Console()
        
        conductor = Conductor(
            output_manager=output_manager,
            console=console
        )
        
        assert conductor.console == console


class TestConductorConversation:
    """Test Conductor conversation management."""
    
    @pytest.fixture
    def conductor(self, mock_providers):
        """Create a Conductor instance for testing."""
        output_manager = Mock(spec=OutputManager)
        # Mock the output manager methods
        output_manager.create_conversation_dir.return_value = ("test_conv_123", Path("/tmp/test_conv_123"))
        
        # Create a mock bus with sync methods
        mock_bus = Mock(spec=EventBus)
        mock_bus.subscribe = Mock()
        mock_bus.emit = AsyncMock()
        
        conductor = Conductor(
            output_manager=output_manager,
            base_providers=mock_providers,
            bus=mock_bus
        )
        
        # Mock dependencies
        conductor.lifecycle = AsyncMock()
        conductor.message_handler = Mock()  # Has both sync and async methods
        conductor.message_handler.set_display_filter = Mock()  # Sync method
        conductor.message_handler.handle_message_complete = Mock()  # Sync method
        conductor.turn_executor = AsyncMock()
        conductor.interrupt_handler = Mock()
        conductor.name_coordinator = Mock()  # Use regular Mock since these are sync methods
        conductor.name_coordinator.initialize_name_mode = Mock()
        conductor.name_coordinator.assign_display_names = Mock()
        
        return conductor
    
    @pytest.fixture
    def mock_providers(self):
        """Create mock providers."""
        provider_a = AsyncMock()
        provider_b = AsyncMock()
        
        async def mock_stream_a():
            yield {"type": "text", "text": "Hello from A"}
            yield {"type": "usage", "usage": {"total_tokens": 10}}
        
        async def mock_stream_b():
            yield {"type": "text", "text": "Hello from B"}
            yield {"type": "usage", "usage": {"total_tokens": 10}}
        
        provider_a.stream_response.return_value = mock_stream_a()
        provider_b.stream_response.return_value = mock_stream_b()
        
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
            initial_prompt="Hello"
        )
        
        # Mock the lifecycle methods that are actually called
        conductor.lifecycle.create_conversation.return_value = test_conversation
        conductor.lifecycle.add_initial_messages = AsyncMock()
        conductor.lifecycle.emit_start_events = AsyncMock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        conductor.lifecycle.save_transcripts = AsyncMock()
        
        # Mock message handler methods
        conductor.message_handler.set_display_filter = Mock()
        conductor.message_handler.handle_message_complete = Mock()
        
        # Mock turn execution - stop after 1 turn
        # run_single_turn returns a Turn object or None (None means stop)
        conductor.turn_executor.run_single_turn = AsyncMock(return_value=None)
        conductor.turn_executor.stop_reason = "max_turns"
        
        # Run conversation
        result = await conductor.run_conversation(
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt="Hello",
            max_turns=1
        )
        
        # Note: The result will be an AsyncMock in this test setup
        # What's important is that the proper lifecycle methods were called
        assert result is not None
        
        # Verify lifecycle methods were called
        conductor.lifecycle.create_conversation.assert_called_once()
        conductor.lifecycle.add_initial_messages.assert_called_once()
        conductor.lifecycle.emit_start_events.assert_called_once()
        conductor.lifecycle.emit_end_event_with_reason.assert_called_once()
        conductor.lifecycle.save_transcripts.assert_called_once()
        
        # Verify turn was executed
        conductor.turn_executor.run_single_turn.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_conversation_with_name_choosing(self, conductor, mock_providers):
        """Test conversation with agent name choosing."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")
        
        # Mock conversation and name coordination
        test_conversation = Conversation(
            id="test_conv_123",
            agents=[agent_a, agent_b],
            messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation
        conductor.lifecycle.add_initial_messages = AsyncMock()
        conductor.lifecycle.emit_start_events = AsyncMock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        conductor.lifecycle.save_transcripts = AsyncMock()
        conductor.lifecycle.initialize_event_system = AsyncMock()
        
        # Mock turn execution
        conductor.turn_executor.run_single_turn = AsyncMock(return_value=None)
        conductor.turn_executor.stop_reason = "max_turns"
        
        # Mock name choosing methods that actually exist
        conductor.name_coordinator.initialize_name_mode = Mock()
        conductor.name_coordinator.assign_display_names = Mock()
        
        # Run conversation with choose_names=True
        result = await conductor.run_conversation(
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt="Hello",
            max_turns=1,
            choose_names=True
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
        conductor.lifecycle.initialize_event_system = AsyncMock(side_effect=Exception("Test error"))
        
        # Run conversation and expect exception
        with pytest.raises(Exception, match="Test error"):
            await conductor.run_conversation(
                agent_a=agent_a,
                agent_b=agent_b,
                initial_prompt="Hello",
                max_turns=1
            )
    
    @pytest.mark.asyncio
    async def test_run_conversation_interrupt(self, conductor, mock_providers):
        """Test conversation interruption."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")
        
        test_conversation = Conversation(
            id="test_conv_123",
            agents=[agent_a, agent_b],
            messages=[]
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
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt="Hello",
            max_turns=10
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
            id="test_conv_123",
            agents=[agent_a, agent_b],
            messages=[]
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
            None    # Turn 4 - returns None to stop
        ]
        conductor.turn_executor.stop_reason = "max_turns"
        
        # Run conversation
        result = await conductor.run_conversation(
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt="Hello",
            max_turns=3
        )
        
        # Verify turn executor was called 3 times (3 turns, then stops on max_turns)
        assert conductor.turn_executor.run_single_turn.call_count == 3


class TestConductorEventEmission:
    """Test that Conductor properly coordinates event emission."""
    
    @pytest.fixture
    def conductor_with_bus(self, mock_pidgin_output_dir):
        """Create a Conductor with a real EventBus for testing events."""
        output_manager = Mock(spec=OutputManager)
        output_manager.create_conversation_dir.return_value = ("test_conv_123", Path("/tmp/test_conv_123"))
        
        # Create EventBus with proper event log directory
        conversations_dir = mock_pidgin_output_dir / "conversations"
        bus = EventBus(event_log_dir=str(conversations_dir))
        
        # Mock providers
        mock_providers = {
            "agent_a": AsyncMock(),
            "agent_b": AsyncMock()
        }
        
        conductor = Conductor(
            output_manager=output_manager,
            bus=bus,
            base_providers=mock_providers
        )
        
        # Mock dependencies but keep real lifecycle and bus
        conductor.message_handler = AsyncMock()
        conductor.message_handler.set_display_filter = Mock()
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
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt="Hello",
            max_turns=1
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
        mock_providers = {
            "agent_a": AsyncMock(),
            "agent_b": AsyncMock()
        }
        
        output_manager = Mock(spec=OutputManager)
        conductor = Conductor(
            output_manager=output_manager,
            base_providers=mock_providers
        )
        
        # Verify providers were stored
        assert conductor.base_providers == mock_providers
        
        # The providers are set during initialization
        assert hasattr(conductor, 'lifecycle')
        # The lifecycle should have set_providers method called
        assert hasattr(conductor.lifecycle, 'set_providers')
    
    @pytest.mark.asyncio 
    async def test_providers_used_in_conversation(self):
        """Test that providers are used during conversation."""
        # Setup mock providers
        mock_providers = {
            "agent_a": AsyncMock(),
            "agent_b": AsyncMock()
        }
        
        output_manager = Mock(spec=OutputManager)
        output_manager.create_conversation_dir.return_value = ("test_conv", Path("/tmp/test_conv"))
        
        conductor = Conductor(
            output_manager=output_manager,
            base_providers=mock_providers
        )
        
        # Mock dependencies
        conductor.lifecycle.create_conversation = AsyncMock()
        conductor.lifecycle.add_initial_messages = AsyncMock()
        conductor.lifecycle.emit_start_events = AsyncMock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        conductor.lifecycle.save_transcripts = AsyncMock()
        
        conductor.turn_executor.run_single_turn = AsyncMock(return_value=None)
        conductor.turn_executor.stop_reason = "max_turns"
        
        conductor.message_handler.set_display_filter = Mock()
        conductor.message_handler.handle_message_complete = Mock()
        
        conductor.interrupt_handler = Mock()
        conductor.name_coordinator = Mock()
        conductor.name_coordinator.initialize_name_mode = Mock()
        conductor.name_coordinator.assign_display_names = Mock()
        
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")
        
        test_conversation = Conversation(
            id="test_conv",
            agents=[agent_a, agent_b]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation
        
        # Run conversation
        await conductor.run_conversation(
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt="Hello",
            max_turns=1
        )
        
        # Verify turn executor was called
        conductor.turn_executor.run_single_turn.assert_called_once()