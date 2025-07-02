"""Message request and response handling."""

import asyncio
import time
from typing import List, Optional, Dict

from .types import Agent, Message
from .events import (
    MessageRequestEvent,
    RateLimitPaceEvent,
    ConversationPausedEvent,
    ProviderTimeoutEvent,
)


class MessageHandler:
    """Handles agent message requests, responses, and timeouts."""
    
    def __init__(self, bus, rate_limiter, name_coordinator, console=None):
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
        
        # Nord colors
        self.NORD_RED = "#bf616a"
    
    def set_display_filter(self, display_filter):
        """Set display filter for pacing indicators."""
        self.display_filter = display_filter
    
    async def get_agent_message(
        self,
        conversation_id: str,
        agent: Agent,
        turn_number: int,
        conversation_history: List[Message],
        interrupt_handler,
        timeout: float = 60.0,
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
        # Estimate payload size for rate limiting
        payload_tokens = self._estimate_payload_tokens(
            conversation_history, agent.model
        )
        avg_response_tokens = 500  # Conservative estimate
        total_estimated = payload_tokens + avg_response_tokens
        
        # Determine provider for rate limiting
        provider = self.name_coordinator.get_provider_name(agent.model)
        
        # Acquire rate limit slot (may wait)
        wait_time = await self.rate_limiter.acquire(provider, total_estimated)
        
        # Emit rate limit event if we waited
        if wait_time > 0.1:
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
        
        # Track request timing
        request_start = time.time()
        
        # Create future for this agent's response
        future = asyncio.Future()
        self.pending_messages[agent.id] = future
        
        # Request message
        await self.bus.emit(
            MessageRequestEvent(
                conversation_id=conversation_id,
                agent_id=agent.id,
                turn_number=turn_number,
                conversation_history=conversation_history.copy(),
                temperature=agent.temperature,
            )
        )
        
        # Create interrupt check task
        async def check_interrupt():
            """Check for interrupt flag."""
            while not interrupt_handler.interrupt_requested:
                await asyncio.sleep(0.1)  # Check every 100ms
            return True
        
        interrupt_task = asyncio.create_task(check_interrupt())
        message_task = asyncio.create_task(asyncio.wait_for(future, timeout=timeout))
        
        # Wait for response with timeout OR interrupt
        try:
            # Wait for EITHER message completion OR interrupt
            done, pending = await asyncio.wait(
                [message_task, interrupt_task], return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
            
            if interrupt_task in done and interrupt_task.result():
                # Interrupted! Handle pause
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
                except:
                    return None
            else:
                # Message completed normally
                message = await message_task
                
                # Record request completion for rate limiting
                request_duration = time.time() - request_start
                if message:
                    # Estimate actual tokens (rough)
                    actual_tokens = len(message.content) // 4 + payload_tokens
                    self.rate_limiter.record_request_complete(
                        provider, actual_tokens, request_duration
                    )
                
                return message
        
        except asyncio.TimeoutError:
            # Emit timeout event
            await self.bus.emit(
                ProviderTimeoutEvent(
                    conversation_id=conversation_id,
                    error_type="timeout",
                    error_message=f"{agent.display_name} did not respond within {timeout} seconds",
                    context=f"Turn {turn_number}",
                    agent_id=agent.id,
                    timeout_seconds=timeout,
                )
            )
            
            # Get user decision
            decision = "skip"  # Always skip on timeout
            
            if decision == "skip":
                return None
            elif decision == "end":
                raise KeyboardInterrupt("User requested end")
            else:  # WAIT
                try:
                    # Wait longer (double the timeout)
                    message = await asyncio.wait_for(future, timeout=timeout * 2)
                    return message
                except asyncio.TimeoutError:
                    if self.console:
                        self.console.print(
                            f"[{self.NORD_RED}]{agent.display_name} still not responding. Skipping turn.[/{self.NORD_RED}]"
                        )
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
        estimated = int(total_chars / 4 * 1.1)
        
        # Add base system prompt overhead
        if "claude" in model.lower():
            estimated += 200  # Anthropic system prompts
        else:
            estimated += 100  # Other providers
        
        return estimated