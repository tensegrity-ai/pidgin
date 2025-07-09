"""Event-aware wrapper for AI providers."""

import time
from typing import List

from ..core.event_bus import EventBus
from ..core.events import (
    MessageRequestEvent,
    MessageCompleteEvent,
    APIErrorEvent,
    TokenUsageEvent,
)
from ..core.types import Message
from .base import Provider
from ..core.router import DirectRouter  # For message transformation
from .token_utils import estimate_tokens, estimate_messages_tokens


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
        
        # Estimate input tokens
        # Try model_name first (for providers that store model name separately)
        # Fall back to model if model_name doesn't exist
        model_name = getattr(self.provider, 'model_name', None) or getattr(self.provider, 'model', None)
        input_tokens = estimate_messages_tokens(agent_messages, model_name)

        # Stream response and buffer chunks (no longer emitting chunk events)
        chunks = []
        try:
            async for chunk in self.provider.stream_response(agent_messages, temperature=event.temperature):
                chunks.append(chunk)
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
                    retry_count=0,  # TODO: Track retry count from provider retry logic
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
        
        # Get provider name for model-specific token counting
        provider_name = self.provider.__class__.__name__.replace("Provider", "").lower()
        model_name = getattr(self.provider, 'model', None)
        
        # Try to get actual token usage from provider
        tokens_used = 0
        if hasattr(self.provider, 'get_last_usage'):
            usage_data = self.provider.get_last_usage()
            if usage_data and 'completion_tokens' in usage_data:
                tokens_used = usage_data['completion_tokens']
            else:
                # Fall back to estimation
                tokens_used = estimate_tokens(content, model_name)
        else:
            # Provider doesn't support usage tracking, use estimation
            tokens_used = estimate_tokens(content, model_name)

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
        
        # Emit token usage event if we have actual usage data
        if hasattr(self.provider, 'get_last_usage'):
            usage_data = self.provider.get_last_usage()
            if usage_data and 'total_tokens' in usage_data:
                # Extract provider name and model
                provider_name = self.provider.__class__.__name__.replace("Provider", "")
                model_name = getattr(self.provider, 'model', 'unknown')
                
                # Get token tracker for rate limits
                from ..providers.token_tracker import get_token_tracker
                tracker = get_token_tracker()
                usage_stats = tracker.get_usage_stats(provider_name.lower())
                
                # Create enhanced token usage event
                token_event = TokenUsageEvent(
                    conversation_id=event.conversation_id,
                    provider=provider_name,
                    tokens_used=usage_data['total_tokens'],
                    tokens_per_minute_limit=usage_stats['rate_limit'],
                    current_usage_rate=usage_stats['current_rate'],
                )
                # Add model as custom attribute
                token_event.model = model_name
                
                # Handle different naming conventions (Anthropic vs OpenAI)
                token_event.prompt_tokens = usage_data.get('prompt_tokens', 0) or usage_data.get('input_tokens', 0)
                token_event.completion_tokens = usage_data.get('completion_tokens', 0) or usage_data.get('output_tokens', 0)
                
                await self.bus.emit(token_event)
