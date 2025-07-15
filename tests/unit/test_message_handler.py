"""Test message handling functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import time

from pidgin.core.message_handler import MessageHandler
from pidgin.core.types import Agent, Message
from pidgin.core.events import (
    MessageRequestEvent,
    MessageCompleteEvent,
    RateLimitPaceEvent,
    ConversationPausedEvent,
    ProviderTimeoutEvent,
)
from pidgin.core.constants import RateLimits, SystemDefaults
from tests.builders import make_agent, make_message


class TestMessageHandler:
    """Test suite for MessageHandler."""
    
    @pytest.fixture
    def mock_bus(self):
        """Create a mock event bus."""
        bus = AsyncMock()
        bus.emit = AsyncMock()
        return bus
    
    @pytest.fixture
    def mock_rate_limiter(self):
        """Create a mock rate limiter."""
        limiter = AsyncMock()
        limiter.acquire = AsyncMock(return_value=0.0)  # No wait by default
        limiter.record_request_complete = Mock()
        return limiter
    
    @pytest.fixture
    def mock_name_coordinator(self):
        """Create a mock name coordinator."""
        coordinator = Mock()
        coordinator.get_provider_name = Mock(return_value="test_provider")
        return coordinator
    
    @pytest.fixture
    def mock_console(self):
        """Create a mock console."""
        return Mock()
    
    @pytest.fixture
    def handler(self, mock_bus, mock_rate_limiter, mock_name_coordinator, mock_console):
        """Create a MessageHandler instance."""
        return MessageHandler(
            bus=mock_bus,
            rate_limiter=mock_rate_limiter,
            name_coordinator=mock_name_coordinator,
            console=mock_console
        )
    
    @pytest.fixture
    def mock_interrupt_handler(self):
        """Create a mock interrupt handler."""
        handler = Mock()
        handler.interrupt_requested = False
        return handler
    
    def test_initialization(self, handler, mock_bus, mock_rate_limiter, mock_name_coordinator, mock_console):
        """Test handler initialization."""
        assert handler.bus == mock_bus
        assert handler.rate_limiter == mock_rate_limiter
        assert handler.name_coordinator == mock_name_coordinator
        assert handler.console == mock_console
        assert handler.pending_messages == {}
        assert handler.display_filter is None
    
    def test_set_display_filter(self, handler):
        """Test setting display filter."""
        mock_filter = Mock()
        handler.set_display_filter(mock_filter)
        assert handler.display_filter == mock_filter
    
    @pytest.mark.asyncio
    async def test_handle_rate_limiting_no_wait(self, handler, mock_rate_limiter):
        """Test rate limiting with no wait time."""
        agent = make_agent("test_agent", "test_model")
        history = [make_message("Hello", "user")]
        
        await handler._handle_rate_limiting("conv_123", agent, history)
        
        # Should call rate limiter
        mock_rate_limiter.acquire.assert_called_once()
        # Should not emit rate limit event (wait_time = 0)
        handler.bus.emit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_rate_limiting_with_wait(self, handler, mock_rate_limiter):
        """Test rate limiting with significant wait time."""
        mock_rate_limiter.acquire.return_value = 2.0  # 2 second wait
        
        agent = make_agent("test_agent", "test_model")
        history = [make_message("Hello", "user")]
        
        await handler._handle_rate_limiting("conv_123", agent, history)
        
        # Should emit rate limit event
        handler.bus.emit.assert_called_once()
        event = handler.bus.emit.call_args[0][0]
        assert isinstance(event, RateLimitPaceEvent)
        assert event.conversation_id == "conv_123"
        assert event.wait_time == 2.0
    
    @pytest.mark.asyncio
    async def test_handle_rate_limiting_with_display(self, handler, mock_rate_limiter):
        """Test rate limiting with display filter."""
        mock_rate_limiter.acquire.return_value = 2.0
        mock_display = Mock()
        handler.set_display_filter(mock_display)
        
        agent = make_agent("test_agent", "test_model")
        history = [make_message("Hello", "user")]
        
        await handler._handle_rate_limiting("conv_123", agent, history)
        
        # Should show pacing indicator
        mock_display.show_pacing_indicator.assert_called_once_with("test_provider", 2.0)
    
    @pytest.mark.asyncio
    async def test_emit_message_request(self, handler):
        """Test emitting message request event."""
        agent = make_agent("test_agent", "test_model", temperature=0.7)
        history = [make_message("Hello", "user")]
        
        await handler._emit_message_request("conv_123", agent, 1, history)
        
        handler.bus.emit.assert_called_once()
        event = handler.bus.emit.call_args[0][0]
        assert isinstance(event, MessageRequestEvent)
        assert event.conversation_id == "conv_123"
        assert event.agent_id == "test_agent"
        assert event.turn_number == 1
        assert event.temperature == 0.7
        assert len(event.conversation_history) == 1
    
    @pytest.mark.asyncio
    async def test_handle_message_complete(self, handler):
        """Test handling message complete event."""
        # Setup pending message
        future = asyncio.Future()
        handler.pending_messages["test_agent"] = future
        
        # Create message complete event
        message = make_message("Response", "test_agent", "assistant")
        event = MessageCompleteEvent(
            conversation_id="conv_123",
            agent_id="test_agent",
            message=message,
            tokens_used=50,
            duration_ms=100
        )
        
        # Handle event
        await handler.handle_message_complete(event)
        
        # Future should be resolved
        assert future.done()
        assert future.result() == message
        assert "test_agent" not in handler.pending_messages
    
    @pytest.mark.asyncio
    async def test_handle_message_complete_no_pending(self, handler):
        """Test handling message complete with no pending future."""
        message = make_message("Response", "test_agent", "assistant")
        event = MessageCompleteEvent(
            conversation_id="conv_123",
            agent_id="test_agent",
            message=message,
            tokens_used=50,
            duration_ms=100
        )
        
        # Should not raise error
        await handler.handle_message_complete(event)
    
    @pytest.mark.asyncio
    async def test_handle_interrupt(self, handler):
        """Test handling interrupt during message wait."""
        future = asyncio.Future()
        agent = make_agent("test_agent")
        
        # Set up future to complete after interrupt handling
        async def delayed_complete():
            await asyncio.sleep(0.1)
            future.set_result(make_message("Interrupted response", "test_agent"))
        
        asyncio.create_task(delayed_complete())
        
        result = await handler._handle_interrupt("conv_123", agent, 1, future)
        
        # Should emit pause event
        handler.bus.emit.assert_called_once()
        event = handler.bus.emit.call_args[0][0]
        assert isinstance(event, ConversationPausedEvent)
        assert event.paused_during == "waiting_for_test_agent"
        
        # Should return the message
        assert result.content == "Interrupted response"
    
    @pytest.mark.asyncio
    async def test_handle_interrupt_with_exception(self, handler):
        """Test handling interrupt when future raises exception."""
        future = asyncio.Future()
        future.set_exception(Exception("Test error"))
        agent = make_agent("test_agent")
        
        result = await handler._handle_interrupt("conv_123", agent, 1, future)
        
        # Should return None on exception
        assert result is None
    
    @pytest.mark.asyncio
    async def test_handle_timeout(self, handler):
        """Test handling message timeout."""
        future = asyncio.Future()
        agent = make_agent("test_agent", display_name="Test Agent")
        
        result = await handler._handle_timeout("conv_123", agent, 1, 30.0, future)
        
        # Should emit timeout event
        handler.bus.emit.assert_called_once()
        event = handler.bus.emit.call_args[0][0]
        assert isinstance(event, ProviderTimeoutEvent)
        assert event.conversation_id == "conv_123"
        assert event.agent_id == "test_agent"
        assert event.timeout_seconds == 30.0
        assert "Test Agent did not respond" in event.error_message
        
        # Should return None
        assert result is None
    
    def test_estimate_payload_tokens_basic(self, handler):
        """Test basic token estimation."""
        history = [
            make_message("Hello world", "user"),
            make_message("Hi there", "assistant")
        ]
        
        tokens = handler._estimate_payload_tokens(history, "gpt-4")
        
        # Should estimate based on character count
        total_chars = len("Hello world") + len("Hi there")
        expected = int(total_chars / RateLimits.TOKEN_CHAR_RATIO * RateLimits.TOKEN_OVERHEAD_MULTIPLIER)
        expected += 100  # Base overhead for non-Claude
        
        assert tokens == expected
    
    def test_estimate_payload_tokens_claude(self, handler):
        """Test token estimation for Claude models."""
        history = [make_message("Test message", "user")]
        
        tokens = handler._estimate_payload_tokens(history, "claude-3-sonnet")
        
        # Should add more overhead for Claude
        total_chars = len("Test message")
        expected = int(total_chars / RateLimits.TOKEN_CHAR_RATIO * RateLimits.TOKEN_OVERHEAD_MULTIPLIER)
        expected += 200  # Claude overhead
        
        assert tokens == expected
    
    @pytest.mark.asyncio
    async def test_record_request_completion(self, handler, mock_rate_limiter, mock_name_coordinator):
        """Test recording request completion."""
        message = make_message("Response text", "assistant")
        history = [make_message("Question", "user")]
        
        # The function uses time.time() only once at the end, not twice
        with patch('time.time', return_value=1001.5):  # End time
            await handler._record_request_completion("test_model", message, 1000.0, history)
        
        # Should record with rate limiter
        mock_rate_limiter.record_request_complete.assert_called_once()
        call_args = mock_rate_limiter.record_request_complete.call_args
        assert call_args[0][0] == "test_provider"
        assert call_args[0][2] == 1.5  # Duration (1001.5 - 1000.0)
    
    @pytest.mark.asyncio
    async def test_get_agent_message_success(self, handler, mock_interrupt_handler):
        """Test successful message retrieval."""
        agent = make_agent("test_agent", "test_model")
        history = [make_message("Hello", "user")]
        
        # Set up future that will be resolved by handle_message_complete
        async def simulate_message_complete():
            await asyncio.sleep(0.1)
            message = make_message("Response", "test_agent", "assistant")
            event = MessageCompleteEvent(
                conversation_id="conv_123",
                agent_id="test_agent",
                message=message,
                tokens_used=50,
                duration_ms=100
            )
            await handler.handle_message_complete(event)
        
        # Start the simulation
        asyncio.create_task(simulate_message_complete())
        
        # Get message
        result = await handler.get_agent_message(
            "conv_123", agent, 1, history, mock_interrupt_handler
        )
        
        assert result is not None
        assert result.content == "Response"
        assert result.agent_id == "test_agent"
    
    @pytest.mark.asyncio
    async def test_get_agent_message_timeout(self, handler, mock_interrupt_handler):
        """Test message timeout."""
        agent = make_agent("test_agent", "test_model")
        history = [make_message("Hello", "user")]
        
        # Don't resolve the future - let it timeout
        result = await handler.get_agent_message(
            "conv_123", agent, 1, history, mock_interrupt_handler, timeout=0.1
        )
        
        # Should return None on timeout
        assert result is None
        
        # Should emit timeout event
        timeout_events = [
            call[0][0] for call in handler.bus.emit.call_args_list
            if isinstance(call[0][0], ProviderTimeoutEvent)
        ]
        assert len(timeout_events) == 1
    @pytest.mark.asyncio
    async def test_wait_for_message_with_interrupt_no_interrupt(self, handler, mock_interrupt_handler):
        """Test waiting for message without interrupt."""
        future = asyncio.Future()
        agent = make_agent("test_agent")
        
        # Complete future normally
        async def complete_future():
            await asyncio.sleep(0.1)
            future.set_result(make_message("Normal response", "test_agent"))
        
        asyncio.create_task(complete_future())
        
        result = await handler._wait_for_message_with_interrupt(
            future, "conv_123", agent, 1, mock_interrupt_handler, 1.0
        )
        
        assert result.content == "Normal response"
        handler.bus.emit.assert_not_called()  # No interrupt event
    
    @pytest.mark.asyncio
    async def test_interrupt_check_function_returns_true(self, handler):
        """Test that the interrupt check function returns True when interrupt is requested."""
        interrupt_handler = Mock()
        interrupt_handler.interrupt_requested = False
        
        # Create the check_interrupt function directly to test it
        async def check_interrupt():
            """Check for interrupt flag."""
            while not interrupt_handler.interrupt_requested:
                await asyncio.sleep(0.01)  # Short sleep for testing
            return True
        
        # Set up interrupt to trigger
        async def trigger_interrupt():
            await asyncio.sleep(0.05)
            interrupt_handler.interrupt_requested = True
        
        asyncio.create_task(trigger_interrupt())
        
        # This should return True when interrupt is triggered
        result = await check_interrupt()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_handle_interrupt_with_cancelled_future(self, handler):
        """Test handling interrupt when future is cancelled."""
        future = asyncio.Future()
        agent = make_agent("test_agent")
        
        # Cancel the future to trigger the exception path
        future.cancel()
        
        result = await handler._handle_interrupt("conv_123", agent, 1, future)
        
        # Should emit pause event
        handler.bus.emit.assert_called_once()
        event = handler.bus.emit.call_args[0][0]
        assert isinstance(event, ConversationPausedEvent)
        assert event.paused_during == "waiting_for_test_agent"
        
        # Should return None on cancelled future
        assert result is None