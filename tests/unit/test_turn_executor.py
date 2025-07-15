"""Tests for TurnExecutor."""

import pytest
import time
from unittest.mock import AsyncMock, Mock, MagicMock
from typing import Optional

from pidgin.core.turn_executor import TurnExecutor
from pidgin.core.types import Agent, Conversation, Message
from pidgin.core.events import (
    Turn,
    TurnStartEvent,
    TurnCompleteEvent,
    ConversationEndEvent,
    SystemPromptEvent,
)
from pidgin.core.constants import EndReason
from tests.builders import make_conversation, make_agent, make_message


class TestTurnExecutor:
    """Test TurnExecutor functionality."""
    
    @pytest.fixture
    def mock_bus(self):
        """Create a mock event bus."""
        bus = AsyncMock()
        bus.emit = AsyncMock()
        return bus
    
    @pytest.fixture
    def mock_message_handler(self):
        """Create a mock message handler."""
        handler = Mock()
        handler.get_agent_message = AsyncMock()
        return handler
    
    @pytest.fixture
    def mock_convergence_calculator(self):
        """Create a mock convergence calculator."""
        calculator = Mock()
        calculator.calculate = Mock(return_value=0.5)  # Default convergence
        return calculator
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = Mock()
        config.get_convergence_config = Mock(return_value={
            "convergence_threshold": 0.85,
            "convergence_action": "stop"
        })
        return config
    
    @pytest.fixture
    def executor(self, mock_bus, mock_message_handler, mock_convergence_calculator, mock_config):
        """Create a TurnExecutor instance."""
        start_time = time.time()
        return TurnExecutor(
            mock_bus,
            mock_message_handler,
            mock_convergence_calculator,
            mock_config,
            start_time
        )
    
    def test_init(self, executor, mock_bus, mock_message_handler, mock_convergence_calculator, mock_config):
        """Test executor initialization."""
        assert executor.bus == mock_bus
        assert executor.message_handler == mock_message_handler
        assert executor.convergence_calculator == mock_convergence_calculator
        assert executor.config == mock_config
        assert executor.start_time is not None
        assert executor._convergence_threshold_override is None
        assert executor._convergence_action_override is None
        assert executor.stop_reason is None
    
    def test_set_convergence_overrides(self, executor):
        """Test setting convergence overrides."""
        executor.set_convergence_overrides(threshold=0.95, action="warn")
        assert executor._convergence_threshold_override == 0.95
        assert executor._convergence_action_override == "warn"
        
        # Test partial overrides - they reset the other value to None
        executor.set_convergence_overrides(threshold=0.8)
        assert executor._convergence_threshold_override == 0.8
        assert executor._convergence_action_override is None  # Reset
        
        executor.set_convergence_overrides(action="stop")
        assert executor._convergence_threshold_override is None  # Reset
        assert executor._convergence_action_override == "stop"
    
    @pytest.mark.asyncio
    async def test_run_single_turn_success(self, executor, mock_bus, mock_message_handler, mock_convergence_calculator):
        """Test successful turn execution."""
        conversation = make_conversation(id="conv-123", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Mock message responses
        msg_a = make_message(content="Hello", agent_id="agent_a", role="assistant")
        msg_b = make_message(content="Hi there", agent_id="agent_b", role="assistant")
        mock_message_handler.get_agent_message.side_effect = [msg_a, msg_b]
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 0, agent_a, agent_b, interrupt_handler
        )
        
        # Verify turn was created
        assert turn is not None
        assert turn.agent_a_message == msg_a
        assert turn.agent_b_message == msg_b
        
        # Verify messages were added to conversation
        assert len(conversation.messages) == 2
        assert conversation.messages[0] == msg_a
        assert conversation.messages[1] == msg_b
        
        # Verify events were emitted
        assert mock_bus.emit.call_count == 2
        
        # Check TurnStartEvent
        start_event = mock_bus.emit.call_args_list[0][0][0]
        assert isinstance(start_event, TurnStartEvent)
        assert start_event.conversation_id == "conv-123"
        assert start_event.turn_number == 0
        
        # Check TurnCompleteEvent
        complete_event = mock_bus.emit.call_args_list[1][0][0]
        assert isinstance(complete_event, TurnCompleteEvent)
        assert complete_event.conversation_id == "conv-123"
        assert complete_event.turn_number == 0
        assert complete_event.turn == turn
        assert complete_event.convergence_score == 0.5
    
    @pytest.mark.asyncio
    async def test_run_single_turn_interrupted_agent_a(self, executor, mock_bus, mock_message_handler):
        """Test turn interrupted during agent A message."""
        conversation = make_conversation(id="conv-456", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Mock agent A returns None (interrupted)
        mock_message_handler.get_agent_message.return_value = None
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 1, agent_a, agent_b, interrupt_handler
        )
        
        # Verify turn was interrupted
        assert turn is None
        
        # Verify only start event was emitted
        assert mock_bus.emit.call_count == 1
        assert isinstance(mock_bus.emit.call_args[0][0], TurnStartEvent)
        
        # Verify conversation messages weren't modified
        assert len(conversation.messages) == 0
    
    @pytest.mark.asyncio
    async def test_run_single_turn_interrupted_agent_b(self, executor, mock_bus, mock_message_handler):
        """Test turn interrupted during agent B message."""
        conversation = make_conversation(id="conv-789", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Mock agent A succeeds, agent B returns None
        msg_a = make_message(content="Hello", agent_id="agent_a", role="assistant")
        mock_message_handler.get_agent_message.side_effect = [msg_a, None]
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 2, agent_a, agent_b, interrupt_handler
        )
        
        # Verify turn was interrupted
        assert turn is None
        
        # Verify only start event was emitted
        assert mock_bus.emit.call_count == 1
        
        # Verify only agent A's message was added
        assert len(conversation.messages) == 1
        assert conversation.messages[0] == msg_a
    
    @pytest.mark.asyncio
    async def test_high_convergence_stop_action(self, executor, mock_bus, mock_message_handler, mock_convergence_calculator):
        """Test high convergence with stop action."""
        conversation = make_conversation(id="conv-high", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Set high convergence score
        mock_convergence_calculator.calculate.return_value = 0.9
        
        # Mock messages
        msg_a = make_message(content="Same", agent_id="agent_a", role="assistant")
        msg_b = make_message(content="Same", agent_id="agent_b", role="assistant")
        mock_message_handler.get_agent_message.side_effect = [msg_a, msg_b]
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 5, agent_a, agent_b, interrupt_handler
        )
        
        # Verify turn was stopped due to convergence
        assert turn is None
        assert executor.stop_reason == EndReason.HIGH_CONVERGENCE
        
        # Verify events were emitted (start and complete)
        assert mock_bus.emit.call_count == 2
    
    @pytest.mark.asyncio
    async def test_high_convergence_warn_action(self, executor, mock_bus, mock_message_handler, mock_convergence_calculator, mock_config):
        """Test high convergence with warn action."""
        # Change config to warn instead of stop
        mock_config.get_convergence_config.return_value = {
            "convergence_threshold": 0.85,
            "convergence_action": "warn"
        }
        
        conversation = make_conversation(id="conv-warn", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Set high convergence score
        mock_convergence_calculator.calculate.return_value = 0.9
        
        # Mock messages
        msg_a = make_message(content="Same", agent_id="agent_a", role="assistant")
        msg_b = make_message(content="Same", agent_id="agent_b", role="assistant")
        mock_message_handler.get_agent_message.side_effect = [msg_a, msg_b]
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 5, agent_a, agent_b, interrupt_handler
        )
        
        # Verify turn continued despite high convergence
        assert turn is not None
        assert executor.stop_reason is None
    
    @pytest.mark.asyncio
    async def test_convergence_threshold_override(self, executor, mock_bus, mock_message_handler, mock_convergence_calculator):
        """Test convergence threshold override."""
        # Set custom threshold
        executor.set_convergence_overrides(threshold=0.7)
        
        conversation = make_conversation(id="conv-override", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Set convergence score between default (0.85) and override (0.7)
        mock_convergence_calculator.calculate.return_value = 0.75
        
        # Mock messages
        msg_a = make_message(content="Similar", agent_id="agent_a", role="assistant")
        msg_b = make_message(content="Similar", agent_id="agent_b", role="assistant")
        mock_message_handler.get_agent_message.side_effect = [msg_a, msg_b]
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 3, agent_a, agent_b, interrupt_handler
        )
        
        # Should stop due to override threshold
        assert turn is None
        assert executor.stop_reason == EndReason.HIGH_CONVERGENCE
    
    @pytest.mark.asyncio
    async def test_convergence_action_override(self, executor, mock_bus, mock_message_handler, mock_convergence_calculator):
        """Test convergence action override."""
        # Override action to warn instead of stop
        executor.set_convergence_overrides(action="warn")
        
        conversation = make_conversation(id="conv-action-override", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Set high convergence
        mock_convergence_calculator.calculate.return_value = 0.9
        
        # Mock messages
        msg_a = make_message(content="Same", agent_id="agent_a", role="assistant")
        msg_b = make_message(content="Same", agent_id="agent_b", role="assistant")
        mock_message_handler.get_agent_message.side_effect = [msg_a, msg_b]
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 4, agent_a, agent_b, interrupt_handler
        )
        
        # Should continue due to action override
        assert turn is not None
        assert executor.stop_reason is None
    
    @pytest.mark.asyncio
    async def test_message_handler_gets_correct_params(self, executor, mock_message_handler):
        """Test that message handler receives correct parameters."""
        conversation = make_conversation(id="conv-params", num_turns=0)
        conversation.messages = [make_message(content="Previous", agent_id="agent_a")]
        
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Track what messages were passed at call time
        captured_messages = []
        
        async def capture_and_return(conv_id, agent, turn_num, messages, handler):
            # Capture a copy of the messages at call time
            captured_messages.append(list(messages))
            if agent.id == "agent_a":
                return make_message(content="New A", agent_id="agent_a", role="assistant")
            else:
                return make_message(content="New B", agent_id="agent_b", role="assistant")
        
        mock_message_handler.get_agent_message.side_effect = capture_and_return
        
        # Run turn
        await executor.run_single_turn(
            conversation, 10, agent_a, agent_b, interrupt_handler
        )
        
        # Verify message handler calls
        assert mock_message_handler.get_agent_message.call_count == 2
        
        # Check messages passed to agent A (should only have previous)
        assert len(captured_messages[0]) == 1
        assert captured_messages[0][0].content == "Previous"
        
        # Check messages passed to agent B (should have previous + A's new)
        assert len(captured_messages[1]) == 2
        assert captured_messages[1][0].content == "Previous"
        assert captured_messages[1][1].content == "New A"
    
    @pytest.mark.asyncio
    async def test_low_convergence_continues(self, executor, mock_bus, mock_message_handler, mock_convergence_calculator):
        """Test that low convergence allows continuation."""
        conversation = make_conversation(id="conv-low", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Set low convergence score
        mock_convergence_calculator.calculate.return_value = 0.3
        
        # Mock messages
        msg_a = make_message(content="Different topic", agent_id="agent_a", role="assistant")
        msg_b = make_message(content="Another topic", agent_id="agent_b", role="assistant")
        mock_message_handler.get_agent_message.side_effect = [msg_a, msg_b]
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 7, agent_a, agent_b, interrupt_handler
        )
        
        # Verify turn continued
        assert turn is not None
        assert executor.stop_reason is None
        
        # Verify complete event has correct convergence score
        complete_event = mock_bus.emit.call_args_list[1][0][0]
        assert complete_event.convergence_score == 0.3
    
    def test_set_custom_awareness(self, executor):
        """Test setting custom awareness objects."""
        mock_awareness_a = Mock()
        mock_awareness_b = Mock()
        
        custom_awareness = {
            "agent_a": mock_awareness_a,
            "agent_b": mock_awareness_b
        }
        
        executor.set_custom_awareness(custom_awareness)
        
        assert executor.custom_awareness == custom_awareness
        assert executor.custom_awareness["agent_a"] == mock_awareness_a
        assert executor.custom_awareness["agent_b"] == mock_awareness_b
    
    def test_set_custom_awareness_partial(self, executor):
        """Test setting custom awareness with only one agent."""
        mock_awareness_a = Mock()
        
        custom_awareness = {
            "agent_a": mock_awareness_a,
            "agent_b": None
        }
        
        executor.set_custom_awareness(custom_awareness)
        
        assert executor.custom_awareness["agent_a"] == mock_awareness_a
        assert executor.custom_awareness["agent_b"] is None
    
    @pytest.mark.asyncio
    async def test_custom_awareness_injection_agent_a(self, executor, mock_bus, mock_message_handler):
        """Test custom awareness injection for agent A."""
        conversation = make_conversation(id="conv-custom-a", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Mock custom awareness for agent A
        mock_awareness_a = Mock()
        mock_awareness_a.get_turn_prompts.return_value = {
            "agent_a": "Special instructions for turn 5",
            "agent_b": ""  # Empty for agent B
        }
        
        executor.set_custom_awareness({
            "agent_a": mock_awareness_a,
            "agent_b": None
        })
        
        # Mock messages
        msg_a = make_message(content="Response A", agent_id="agent_a", role="assistant")
        msg_b = make_message(content="Response B", agent_id="agent_b", role="assistant")
        mock_message_handler.get_agent_message.side_effect = [msg_a, msg_b]
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 5, agent_a, agent_b, interrupt_handler
        )
        
        # Verify turn succeeded
        assert turn is not None
        
        # Verify custom awareness was called
        mock_awareness_a.get_turn_prompts.assert_called_once_with(5)
        
        # Verify system message was injected
        assert len(conversation.messages) == 3  # system + msg_a + msg_b
        system_msg = conversation.messages[0]
        assert system_msg.role == "system"
        assert system_msg.content == "Special instructions for turn 5"
        assert system_msg.agent_id == "system"
        
        # Verify SystemPromptEvent was emitted
        assert mock_bus.emit.call_count == 3  # TurnStart + SystemPrompt + TurnComplete
        
        # Check SystemPromptEvent
        system_event = mock_bus.emit.call_args_list[1][0][0]
        assert isinstance(system_event, SystemPromptEvent)
        assert system_event.conversation_id == "conv-custom-a"
        assert system_event.agent_id == "agent_a"
        assert system_event.prompt == "Special instructions for turn 5"
        assert system_event.agent_display_name == "Turn 5 injection for Agent A"
    
    @pytest.mark.asyncio
    async def test_custom_awareness_injection_agent_b(self, executor, mock_bus, mock_message_handler):
        """Test custom awareness injection for agent B."""
        conversation = make_conversation(id="conv-custom-b", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Mock custom awareness for agent B
        mock_awareness_b = Mock()
        mock_awareness_b.get_turn_prompts.return_value = {
            "agent_a": "",  # Empty for agent A
            "agent_b": "Special instructions for agent B at turn 3"
        }
        
        executor.set_custom_awareness({
            "agent_a": None,
            "agent_b": mock_awareness_b
        })
        
        # Mock messages
        msg_a = make_message(content="Response A", agent_id="agent_a", role="assistant")
        msg_b = make_message(content="Response B", agent_id="agent_b", role="assistant")
        mock_message_handler.get_agent_message.side_effect = [msg_a, msg_b]
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 3, agent_a, agent_b, interrupt_handler
        )
        
        # Verify turn succeeded
        assert turn is not None
        
        # Verify custom awareness was called
        mock_awareness_b.get_turn_prompts.assert_called_once_with(3)
        
        # Verify system message was injected
        assert len(conversation.messages) == 3  # system + msg_a + msg_b
        system_msg = conversation.messages[0]
        assert system_msg.role == "system"
        assert system_msg.content == "Special instructions for agent B at turn 3"
        assert system_msg.agent_id == "system"
        
        # Verify SystemPromptEvent was emitted
        assert mock_bus.emit.call_count == 3  # TurnStart + SystemPrompt + TurnComplete
        
        # Check SystemPromptEvent
        system_event = mock_bus.emit.call_args_list[1][0][0]
        assert isinstance(system_event, SystemPromptEvent)
        assert system_event.conversation_id == "conv-custom-b"
        assert system_event.agent_id == "agent_b"
        assert system_event.prompt == "Special instructions for agent B at turn 3"
        assert system_event.agent_display_name == "Turn 3 injection for Agent B"
    
    @pytest.mark.asyncio
    async def test_custom_awareness_injection_both_agents(self, executor, mock_bus, mock_message_handler):
        """Test custom awareness injection for both agents."""
        conversation = make_conversation(id="conv-custom-both", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Mock custom awareness for both agents
        mock_awareness_a = Mock()
        mock_awareness_a.get_turn_prompts.return_value = {
            "agent_a": "Instructions for A",
            "agent_b": ""  # Empty for B in A's awareness
        }
        
        mock_awareness_b = Mock()
        mock_awareness_b.get_turn_prompts.return_value = {
            "agent_a": "",  # Empty for A in B's awareness
            "agent_b": "Instructions for B"
        }
        
        executor.set_custom_awareness({
            "agent_a": mock_awareness_a,
            "agent_b": mock_awareness_b
        })
        
        # Mock messages
        msg_a = make_message(content="Response A", agent_id="agent_a", role="assistant")
        msg_b = make_message(content="Response B", agent_id="agent_b", role="assistant")
        mock_message_handler.get_agent_message.side_effect = [msg_a, msg_b]
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 1, agent_a, agent_b, interrupt_handler
        )
        
        # Verify turn succeeded
        assert turn is not None
        
        # Verify both custom awareness objects were called
        mock_awareness_a.get_turn_prompts.assert_called_once_with(1)
        mock_awareness_b.get_turn_prompts.assert_called_once_with(1)
        
        # Verify two system messages were injected
        assert len(conversation.messages) == 4  # system_a + system_b + msg_a + msg_b
        
        system_msg_a = conversation.messages[0]
        assert system_msg_a.role == "system"
        assert system_msg_a.content == "Instructions for A"
        assert system_msg_a.agent_id == "system"
        
        system_msg_b = conversation.messages[1]
        assert system_msg_b.role == "system"
        assert system_msg_b.content == "Instructions for B"
        assert system_msg_b.agent_id == "system"
        
        # Verify SystemPromptEvents were emitted
        assert mock_bus.emit.call_count == 4  # TurnStart + SystemPrompt_A + SystemPrompt_B + TurnComplete
        
        # Check first SystemPromptEvent (agent A)
        system_event_a = mock_bus.emit.call_args_list[1][0][0]
        assert isinstance(system_event_a, SystemPromptEvent)
        assert system_event_a.agent_id == "agent_a"
        assert system_event_a.prompt == "Instructions for A"
        
        # Check second SystemPromptEvent (agent B)
        system_event_b = mock_bus.emit.call_args_list[2][0][0]
        assert isinstance(system_event_b, SystemPromptEvent)
        assert system_event_b.agent_id == "agent_b"
        assert system_event_b.prompt == "Instructions for B"
    
    @pytest.mark.asyncio
    async def test_custom_awareness_no_prompts(self, executor, mock_bus, mock_message_handler):
        """Test custom awareness when no prompts are returned."""
        conversation = make_conversation(id="conv-no-prompts", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # Mock custom awareness that returns empty prompts
        mock_awareness_a = Mock()
        mock_awareness_a.get_turn_prompts.return_value = {
            "agent_a": "",  # Empty
            "agent_b": ""   # Empty
        }
        
        executor.set_custom_awareness({
            "agent_a": mock_awareness_a,
            "agent_b": None
        })
        
        # Mock messages
        msg_a = make_message(content="Response A", agent_id="agent_a", role="assistant")
        msg_b = make_message(content="Response B", agent_id="agent_b", role="assistant")
        mock_message_handler.get_agent_message.side_effect = [msg_a, msg_b]
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 2, agent_a, agent_b, interrupt_handler
        )
        
        # Verify turn succeeded
        assert turn is not None
        
        # Verify custom awareness was called
        mock_awareness_a.get_turn_prompts.assert_called_once_with(2)
        
        # Verify no system messages were injected
        assert len(conversation.messages) == 2  # only msg_a + msg_b
        assert conversation.messages[0] == msg_a
        assert conversation.messages[1] == msg_b
        
        # Verify no SystemPromptEvents were emitted
        assert mock_bus.emit.call_count == 2  # only TurnStart + TurnComplete
        assert isinstance(mock_bus.emit.call_args_list[0][0][0], TurnStartEvent)
        assert isinstance(mock_bus.emit.call_args_list[1][0][0], TurnCompleteEvent)
    
    @pytest.mark.asyncio
    async def test_custom_awareness_none_agents(self, executor, mock_bus, mock_message_handler):
        """Test custom awareness when no agents have custom awareness."""
        conversation = make_conversation(id="conv-none-agents", num_turns=0)
        agent_a = make_agent(id="agent_a")
        agent_b = make_agent(id="agent_b")
        interrupt_handler = Mock()
        
        # No custom awareness set (default None values)
        assert executor.custom_awareness["agent_a"] is None
        assert executor.custom_awareness["agent_b"] is None
        
        # Mock messages
        msg_a = make_message(content="Response A", agent_id="agent_a", role="assistant")
        msg_b = make_message(content="Response B", agent_id="agent_b", role="assistant")
        mock_message_handler.get_agent_message.side_effect = [msg_a, msg_b]
        
        # Run turn
        turn = await executor.run_single_turn(
            conversation, 8, agent_a, agent_b, interrupt_handler
        )
        
        # Verify turn succeeded
        assert turn is not None
        
        # Verify no system messages were injected
        assert len(conversation.messages) == 2  # only msg_a + msg_b
        assert conversation.messages[0] == msg_a
        assert conversation.messages[1] == msg_b
        
        # Verify no SystemPromptEvents were emitted
        assert mock_bus.emit.call_count == 2  # only TurnStart + TurnComplete
        assert isinstance(mock_bus.emit.call_args_list[0][0][0], TurnStartEvent)
        assert isinstance(mock_bus.emit.call_args_list[1][0][0], TurnCompleteEvent)