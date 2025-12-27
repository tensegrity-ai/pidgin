"""Message request and response handling."""

import asyncio
import time
from typing import Dict, List, Optional

from .constants import RateLimits, SystemDefaults
from .events import (
    ConversationPausedEvent,
    MessageRequestEvent,
    ProviderTimeoutEvent,
    RateLimitPaceEvent,
)
from .types import Agent, Message


class MessageHandler:
    """Handles agent message requests, responses, and timeouts."""

    def __init__(self, bus, rate_limiter, name_coordinator, console=None) -> None:
        """Initialize message handler.

        Args:
            bus: Event bus for emitting events
            rate_limiter: Rate limiting component
            name_coordinator: For getting provider names
            console: Optional console for user feedback
        """
        self.bus = bus
        self.rate_limiter = rate_limiter
        self.name_coordinator = name_coordinator
        self.console = console
        self.pending_messages: Dict[str, asyncio.Future] = {}
        self.display_filter = None

    def set_display_filter(self, display_filter) -> None:
        """Set display filter for pacing indicators."""
        self.display_filter = display_filter

    async def get_agent_message(
        self,
        conversation_id: str,
        agent: Agent,
        turn_number: int,
        conversation_history: List[Message],
        interrupt_handler,
        timeout: float = SystemDefaults.DEFAULT_TIMEOUT,
    ) -> Optional[Message]:
        """Get a single agent's message with timeout handling.

        Args:
            conversation_id: ID of the current conversation
            agent: The agent to get a message from
            turn_number: Current turn number
            conversation_history: Full conversation history
            interrupt_handler: For checking interrupts
            timeout: Initial timeout in seconds

        Returns:
            The agent's message or None if skipped
        """
        # Handle rate limiting
        await self._handle_rate_limiting(conversation_id, agent, conversation_history)

        # Request and wait for message
        message = await self._request_and_wait_for_message(
            conversation_id,
            agent,
            turn_number,
            conversation_history,
            interrupt_handler,
            timeout,
        )

        return message

    async def _handle_rate_limiting(
        self, conversation_id: str, agent: Agent, conversation_history: List[Message]
    ) -> None:
        """Handle rate limiting before making a request."""
        # Estimate payload size for rate limiting
        payload_tokens = self._estimate_payload_tokens(
            conversation_history, agent.model
        )
        total_estimated = payload_tokens + RateLimits.DEFAULT_RESPONSE_TOKENS

        # Determine provider for rate limiting
        provider = self.name_coordinator.get_provider_name(agent.model)

        # Acquire rate limit slot (may wait)
        wait_time = await self.rate_limiter.acquire(provider, total_estimated)

        # Emit rate limit event if we waited
        if wait_time > RateLimits.RATE_LIMIT_WAIT_THRESHOLD:
            await self._emit_rate_limit_event(conversation_id, provider, wait_time)

    async def _emit_rate_limit_event(
        self, conversation_id: str, provider: str, wait_time: float
    ) -> None:
        """Emit rate limit event and show pacing indicator."""
        await self.bus.emit(
            RateLimitPaceEvent(
                conversation_id=conversation_id,
                provider=provider,
                wait_time=wait_time,
                reason="mixed",  # Could be either request or token rate
            )
        )

        # Show pacing indicator if we have display
        if self.display_filter:
            self.display_filter.show_pacing_indicator(provider, wait_time)

    async def _request_and_wait_for_message(
        self,
        conversation_id: str,
        agent: Agent,
        turn_number: int,
        conversation_history: List[Message],
        interrupt_handler,
        timeout: float,
    ) -> Optional[Message]:
        """Request message and wait for response with interrupt handling."""
        request_start = time.time()

        # Create future for this agent's response
        future: asyncio.Future[Message] = asyncio.Future()
        self.pending_messages[agent.id] = future

        # Request message
        await self._emit_message_request(
            conversation_id, agent, turn_number, conversation_history
        )

        # Wait for response with interrupt handling
        try:
            message = await self._wait_for_message_with_interrupt(
                future, conversation_id, agent, turn_number, interrupt_handler, timeout
            )

            if message:
                await self._record_request_completion(
                    agent.model, message, request_start, conversation_history
                )

            return message

        except asyncio.TimeoutError:
            return await self._handle_timeout(
                conversation_id, agent, turn_number, timeout, future
            )
        except Exception as e:
            # Check if this is a context limit error
            from ..providers.error_utils import ContextLimitError

            if isinstance(e, ContextLimitError):
                # Return None to signal the conversation should end
                return None
            else:
                # Re-raise other exceptions
                raise

    async def _emit_message_request(
        self,
        conversation_id: str,
        agent: Agent,
        turn_number: int,
        conversation_history: List[Message],
    ) -> None:
        """Emit message request event."""
        await self.bus.emit(
            MessageRequestEvent(
                conversation_id=conversation_id,
                agent_id=agent.id,
                turn_number=turn_number,
                conversation_history=conversation_history.copy(),
                temperature=agent.temperature,
                thinking_enabled=agent.thinking_enabled,
                thinking_budget=agent.thinking_budget,
            )
        )

    async def _wait_for_message_with_interrupt(
        self,
        future: asyncio.Future,
        conversation_id: str,
        agent: Agent,
        turn_number: int,
        interrupt_handler,
        timeout: float,
    ) -> Optional[Message]:
        """Wait for message with interrupt handling."""

        # Create interrupt check task
        async def check_interrupt():
            """Check for interrupt flag."""
            while not interrupt_handler.interrupt_requested:
                await asyncio.sleep(RateLimits.INTERRUPT_CHECK_INTERVAL)
            return True

        interrupt_task = asyncio.create_task(check_interrupt())
        message_task = asyncio.create_task(asyncio.wait_for(future, timeout=timeout))

        # Wait for EITHER message completion OR interrupt
        done, pending = await asyncio.wait(
            [message_task, interrupt_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()

        if interrupt_task in done and interrupt_task.result():
            # Handle interrupt
            return await self._handle_interrupt(
                conversation_id, agent, turn_number, future
            )
        else:
            # Message completed normally
            return await message_task

    async def _handle_interrupt(
        self,
        conversation_id: str,
        agent: Agent,
        turn_number: int,
        future: asyncio.Future,
    ) -> Optional[Message]:
        """Handle conversation interrupt."""
        await self.bus.emit(
            ConversationPausedEvent(
                conversation_id=conversation_id,
                turn_number=turn_number,
                paused_during=f"waiting_for_{agent.id}",
            )
        )

        # Wait for the message to complete anyway
        try:
            message = await future
            return message
        except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
            # Message generation was cancelled or failed
            return None

    async def _record_request_completion(
        self,
        model: str,
        message: Message,
        request_start: float,
        conversation_history: List[Message],
    ) -> None:
        """Record request completion for rate limiting."""
        provider = self.name_coordinator.get_provider_name(model)
        request_duration = time.time() - request_start

        # Estimate actual tokens
        payload_tokens = self._estimate_payload_tokens(conversation_history, model)
        actual_tokens = (
            len(message.content) // RateLimits.TOKEN_CHAR_RATIO + payload_tokens
        )

        self.rate_limiter.record_request_complete(
            provider, actual_tokens, request_duration
        )

    async def _handle_timeout(
        self,
        conversation_id: str,
        agent: Agent,
        turn_number: int,
        timeout: float,
        future: asyncio.Future,
    ) -> Optional[Message]:
        """Handle message timeout."""
        # Emit timeout event
        # Extract provider from model string (e.g., "anthropic:claude-3-opus" -> "anthropic")
        provider = agent.model.split(":")[0] if ":" in agent.model else agent.model

        await self.bus.emit(
            ProviderTimeoutEvent(
                conversation_id=conversation_id,
                error_type="timeout",
                error_message=f"{agent.display_name} did not respond within {timeout} seconds",
                context=f"Turn {turn_number}",
                agent_id=agent.id,
                provider=provider,
                timeout_seconds=timeout,
            )
        )

        # Always skip on timeout for now
        return None

    async def handle_message_complete(self, event):
        """Handle completed message event.

        Args:
            event: MessageCompleteEvent
        """
        # Resolve the pending future for this agent
        if event.agent_id in self.pending_messages:
            future = self.pending_messages.pop(event.agent_id)
            if not future.done():
                future.set_result(event.message)

    async def handle_context_limit(self, event):
        """Handle context limit event by failing the pending message.

        Args:
            event: ContextLimitEvent
        """
        # Set exception in the pending future for this agent
        if event.agent_id in self.pending_messages:
            future = self.pending_messages.pop(event.agent_id)
            if not future.done():
                # Create a specific exception for context limits
                from ..providers.error_utils import ContextLimitError

                future.set_exception(ContextLimitError(event.error_message))

    def _estimate_payload_tokens(
        self, conversation_history: List[Message], model: str
    ) -> int:
        """Roughly estimate tokens in conversation history.

        Args:
            conversation_history: Messages to estimate
            model: Model being used (for provider-specific estimation)

        Returns:
            Estimated token count
        """
        # Very rough estimation: ~4 chars per token
        total_chars = sum(len(msg.content) for msg in conversation_history)

        # Add ~10% for message metadata/formatting
        estimated = int(
            total_chars
            / RateLimits.TOKEN_CHAR_RATIO
            * RateLimits.TOKEN_OVERHEAD_MULTIPLIER
        )

        # Add base system prompt overhead from provider capabilities
        from ..config.models import get_model_config
        from ..config.provider_capabilities import get_provider_capabilities

        model_config = get_model_config(model)
        if model_config:
            capabilities = get_provider_capabilities(model_config.provider)
            estimated += capabilities.system_prompt_overhead
        else:
            estimated += 100  # Default if model not found

        return estimated
