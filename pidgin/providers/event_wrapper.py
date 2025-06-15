"""Event-aware wrapper for AI providers."""

import time
from typing import List

from ..event_bus import EventBus
from ..events import (
    MessageRequestEvent,
    MessageChunkEvent,
    MessageCompleteEvent,
    APIErrorEvent,
)
from ..types import Message
from .base import Provider
from ..router import DirectRouter  # For message transformation


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

        # Create a router for message transformation
        self.router = DirectRouter(
            {}
        )  # Empty providers dict, we just need the transformation

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

        # Transform messages for this agent's perspective
        agent_messages = self.router._build_agent_history(
            event.conversation_history, self.agent_id
        )

        # Stream response and emit chunk events
        chunks = []
        try:
            async for chunk in self.provider.stream_response(agent_messages):
                chunks.append(chunk)

                # Emit chunk event
                elapsed_ms = int((time.time() - start_time) * 1000)
                await self.bus.emit(
                    MessageChunkEvent(
                        conversation_id=event.conversation_id,
                        agent_id=self.agent_id,
                        chunk=chunk,
                        chunk_index=chunk_index,
                        elapsed_ms=elapsed_ms,
                    )
                )

                chunk_index += 1

        except Exception as e:
            # Emit error event
            error_str = str(e)

            # Determine if error is retryable
            retryable = any(
                err in error_str.lower()
                for err in ["overloaded", "rate_limit", "rate limit", "429"]
            )

            # Extract provider name from model
            provider_name = self.provider.__class__.__name__.replace("Provider", "")

            await self.bus.emit(
                APIErrorEvent(
                    conversation_id=event.conversation_id,
                    error_type="api_error",
                    error_message=error_str,
                    context=f"During message generation for turn {event.turn_number}",
                    agent_id=self.agent_id,
                    provider=provider_name,
                    retryable=retryable,
                    retry_count=0,  # TODO: Track retry count from provider
                )
            )

            # Still raise to let conductor handle it
            raise

        # Build complete message
        content = "".join(chunks)
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
        await self.bus.emit(
            MessageCompleteEvent(
                conversation_id=event.conversation_id,
                agent_id=self.agent_id,
                message=message,
                tokens_used=tokens_used,
                duration_ms=duration_ms,
            )
        )
