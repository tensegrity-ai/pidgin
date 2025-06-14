"""Event-aware wrapper for AI providers."""

import time
from typing import List

from ..event_bus import EventBus
from ..events import (
    MessageRequestEvent,
    MessageChunkEvent,
    MessageCompleteEvent,
)
from ..types import Message
from .base import Provider


class EventAwareProvider:
    """Wraps existing providers to emit events."""
    
    def __init__(self, provider: Provider, bus: EventBus, agent_id: str):
        """Initialize wrapper.
        
        Args:
            provider: The underlying provider
            bus: Event bus for emitting events
            agent_id: ID of the agent using this provider
        """
        self.provider = provider
        self.bus = bus
        self.agent_id = agent_id
        
        # Subscribe to message requests for this agent
        bus.subscribe(MessageRequestEvent, self.handle_message_request)
    
    async def handle_message_request(self, event: MessageRequestEvent) -> None:
        """Handle message request events for this agent.
        
        Args:
            event: The message request event
        """
        # Only handle requests for our agent
        if event.agent_id != self.agent_id:
            return
        
        # Track timing
        start_time = time.time()
        chunk_index = 0
        
        # Stream response and emit chunk events
        chunks = []
        try:
            async for chunk in self.provider.stream_response(event.conversation_history):
                chunks.append(chunk)
                
                # Emit chunk event
                elapsed_ms = int((time.time() - start_time) * 1000)
                await self.bus.emit(MessageChunkEvent(
                    conversation_id=event.conversation_id,
                    agent_id=self.agent_id,
                    chunk=chunk,
                    chunk_index=chunk_index,
                    elapsed_ms=elapsed_ms,
                ))
                
                chunk_index += 1
        
        except Exception as e:
            # TODO: Add error event type
            print(f"Error in provider {self.agent_id}: {e}")
            raise
        
        # Build complete message
        content = ''.join(chunks)
        message = Message(
            role="assistant",
            content=content,
            agent_id=self.agent_id,
        )
        
        # Calculate metrics
        duration_ms = int((time.time() - start_time) * 1000)
        # TODO: Get actual token count from provider
        tokens_used = len(content.split())  # Rough estimate
        
        # Emit completion event
        await self.bus.emit(MessageCompleteEvent(
            conversation_id=event.conversation_id,
            agent_id=self.agent_id,
            message=message,
            tokens_used=tokens_used,
            duration_ms=duration_ms,
        ))