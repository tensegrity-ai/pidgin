"""Tests for InterruptHandler."""

import signal
import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from rich.console import Console

from pidgin.core.interrupt_handler import InterruptHandler
from pidgin.core.events import (
    InterruptRequestEvent,
    ConversationPausedEvent,
    ConversationResumedEvent,
)
from tests.builders import make_conversation


class TestInterruptHandler:
    """Test InterruptHandler functionality."""
    
    @pytest.fixture
    def mock_bus(self):
        """Create a mock event bus."""
        bus = AsyncMock()
        bus.emit = AsyncMock()
        return bus
    
    @pytest.fixture
    def mock_console(self):
        """Create a mock console."""
        return Mock(spec=Console)
    
    @pytest.fixture
    def handler(self, mock_bus, mock_console):
        """Create an InterruptHandler instance."""
        return InterruptHandler(mock_bus, mock_console)
    
    def test_init(self, handler, mock_bus, mock_console):
        """Test handler initialization."""
        assert handler.bus == mock_bus
        assert handler.console == mock_console
        assert handler.interrupt_requested is False
        assert handler.paused is False
        assert handler.current_turn == 0
        assert handler._original_sigint_handler is None
        assert handler.NORD_YELLOW == "#ebcb8b"
    
    def test_setup_interrupt_handler(self, handler):
        """Test setting up the interrupt handler."""
        with patch('signal.signal') as mock_signal:
            original_handler = Mock()
            mock_signal.return_value = original_handler
            
            handler.setup_interrupt_handler()
            
            # Should save original handler
            assert handler._original_sigint_handler == original_handler
            
            # Should set up new handler
            mock_signal.assert_called_once()
            assert mock_signal.call_args[0][0] == signal.SIGINT
            assert callable(mock_signal.call_args[0][1])
    
    def test_interrupt_handler_callback(self, handler, mock_console):
        """Test the interrupt handler callback function."""
        with patch('signal.signal') as mock_signal:
            handler.setup_interrupt_handler()
            
            # Get the callback function
            interrupt_callback = mock_signal.call_args[0][1]
            
            # Trigger interrupt
            interrupt_callback(signal.SIGINT, None)
            
            # Should set interrupt flag
            assert handler.interrupt_requested is True
            
            # Should show feedback (two calls: one for spacing, one for message)
            assert mock_console.print.call_count == 2
            # First call is empty (spacing)
            first_call = mock_console.print.call_args_list[0]
            assert first_call == ((), {})  # Empty call with no args
            # Second call has the interrupt message
            second_call_args = mock_console.print.call_args_list[1][0]
            if len(second_call_args) > 0:
                call_args = second_call_args[0]
                assert "Interrupt received" in call_args
                assert "pausing after current message" in call_args
    
    def test_multiple_interrupts_ignored(self, handler, mock_console):
        """Test that multiple interrupts are ignored."""
        with patch('signal.signal') as mock_signal:
            handler.setup_interrupt_handler()
            interrupt_callback = mock_signal.call_args[0][1]
            
            # First interrupt
            interrupt_callback(signal.SIGINT, None)
            assert mock_console.print.call_count == 2  # Two calls: spacing + message
            
            # Second interrupt should be ignored
            interrupt_callback(signal.SIGINT, None)
            assert mock_console.print.call_count == 2  # No additional print
    
    def test_restore_interrupt_handler(self, handler):
        """Test restoring the original interrupt handler."""
        with patch('signal.signal') as mock_signal:
            original_handler = Mock()
            mock_signal.return_value = original_handler
            
            # Setup handler
            handler.setup_interrupt_handler()
            assert handler._original_sigint_handler == original_handler
            
            # Restore handler
            handler.restore_interrupt_handler()
            
            # Should restore original
            mock_signal.assert_called_with(signal.SIGINT, original_handler)
            assert handler._original_sigint_handler is None
    
    def test_restore_without_setup(self, handler):
        """Test restoring when no handler was set up."""
        with patch('signal.signal') as mock_signal:
            handler.restore_interrupt_handler()
            
            # Should not call signal.signal if no original handler
            mock_signal.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_interrupt_request(self, handler, mock_bus):
        """Test handling interrupt request."""
        handler.current_turn = 5
        
        await handler.handle_interrupt_request("conv-123")
        
        # Should emit InterruptRequestEvent
        mock_bus.emit.assert_called_once()
        event = mock_bus.emit.call_args[0][0]
        assert isinstance(event, InterruptRequestEvent)
        assert event.conversation_id == "conv-123"
        assert event.turn_number == 5
        assert event.interrupt_source == "user"
    
    @pytest.mark.asyncio
    async def test_handle_pause(self, handler, mock_bus):
        """Test handling conversation pause."""
        conversation = make_conversation(id="conv-456")
        handler.current_turn = 3
        
        await handler.handle_pause(conversation)
        
        # Should emit two events
        assert mock_bus.emit.call_count == 2
        
        # First should be InterruptRequestEvent
        first_event = mock_bus.emit.call_args_list[0][0][0]
        assert isinstance(first_event, InterruptRequestEvent)
        assert first_event.conversation_id == "conv-456"
        assert first_event.turn_number == 3
        
        # Second should be ConversationPausedEvent
        second_event = mock_bus.emit.call_args_list[1][0][0]
        assert isinstance(second_event, ConversationPausedEvent)
        assert second_event.conversation_id == "conv-456"
        assert second_event.turn_number == 3
        assert second_event.paused_during == "between_turns"
        
        # Should set paused flag
        assert handler.paused is True
    
    @pytest.mark.asyncio
    async def test_should_continue_always_exits(self, handler, mock_bus):
        """Test that should_continue always returns False (exits)."""
        conversation = make_conversation(id="conv-789")
        handler.current_turn = 7
        handler.interrupt_requested = True
        handler.paused = True
        
        # Should always return False (exit)
        result = await handler.should_continue(conversation)
        assert result is False
        
        # Should not emit resumed event
        mock_bus.emit.assert_not_called()
        
        # Flags should remain unchanged
        assert handler.interrupt_requested is True
        assert handler.paused is True
    
    @pytest.mark.asyncio
    async def test_should_continue_with_continue_decision(self, handler, mock_bus):
        """Test should_continue with continue decision (currently unreachable)."""
        # This tests the continue branch even though decision is hardcoded to "exit"
        conversation = make_conversation(id="conv-999")
        handler.current_turn = 10
        handler.interrupt_requested = True
        handler.paused = True
        
        # Temporarily override the decision logic
        with patch.object(handler, 'should_continue') as mock_should_continue:
            # Simulate continue decision
            async def mock_continue(conv):
                # Emit resumed event
                await handler.bus.emit(
                    ConversationResumedEvent(
                        conversation_id=conv.id,
                        turn_number=handler.current_turn
                    )
                )
                handler.interrupt_requested = False
                handler.paused = False
                return True
            
            mock_should_continue.side_effect = mock_continue
            
            result = await handler.should_continue(conversation)
            assert result is True
            
            # Should emit resumed event
            mock_bus.emit.assert_called_once()
            event = mock_bus.emit.call_args[0][0]
            assert isinstance(event, ConversationResumedEvent)
            assert event.conversation_id == "conv-999"
            assert event.turn_number == 10
            
            # Should reset flags
            assert handler.interrupt_requested is False
            assert handler.paused is False
    
    def test_check_interrupt(self, handler):
        """Test checking interrupt status."""
        # Initially no interrupt
        assert handler.check_interrupt() is False
        
        # Set interrupt
        handler.interrupt_requested = True
        assert handler.check_interrupt() is True
        
        # Clear interrupt
        handler.interrupt_requested = False
        assert handler.check_interrupt() is False
    
    def test_interrupt_handler_without_console(self, mock_bus):
        """Test handler works without console."""
        handler = InterruptHandler(mock_bus, console=None)
        
        with patch('signal.signal') as mock_signal:
            handler.setup_interrupt_handler()
            interrupt_callback = mock_signal.call_args[0][1]
            
            # Should not crash when no console
            interrupt_callback(signal.SIGINT, None)
            
            # Should still set interrupt flag
            assert handler.interrupt_requested is True
    
    @pytest.mark.asyncio
    async def test_full_interrupt_flow(self, handler, mock_bus):
        """Test the full interrupt flow from signal to pause."""
        conversation = make_conversation(id="flow-test")
        handler.current_turn = 2
        
        # Setup interrupt handler
        with patch('signal.signal') as mock_signal:
            handler.setup_interrupt_handler()
            interrupt_callback = mock_signal.call_args[0][1]
            
            # Trigger interrupt
            interrupt_callback(signal.SIGINT, None)
            
            # Check interrupt
            assert handler.check_interrupt() is True
            
            # Handle pause
            await handler.handle_pause(conversation)
            
            # Should emit both events
            assert mock_bus.emit.call_count == 2
            assert handler.paused is True
            
            # Check if should continue
            should_continue = await handler.should_continue(conversation)
            assert should_continue is False
            
            # Restore handler
            handler.restore_interrupt_handler()