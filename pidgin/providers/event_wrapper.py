"""Event-aware wrapper for AI providers."""

import logging
import time

from ..core.event_bus import EventBus
from ..core.events import (
    APIErrorEvent,
    MessageCompleteEvent,
    MessageRequestEvent,
    TokenUsageEvent,
)
from ..core.router import DirectRouter  # For message transformation
from ..core.types import Message
from .base import Provider
from .token_tracker import GlobalTokenTracker
from .token_utils import estimate_tokens, estimate_messages_tokens

logger = logging.getLogger(__name__)


class EventAwareProvider:
    """Wraps existing providers to emit events."""

    def __init__(self, provider: Provider, bus: EventBus, agent_id: str, token_tracker: GlobalTokenTracker):
        """Initialize wrapper.

        Args:
            provider: The underlying provider
            bus: Event bus for emitting events
            agent_id: ID of the agent using this provider
            token_tracker: Token tracker for rate limiting
        """
        self.provider = provider
        self.bus = bus
        self.agent_id = agent_id
        self.token_tracker = token_tracker

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

        try:
            # Track timing
            start_time = time.time()
            chunk_index = 0

            # Transform messages for this agent's perspective
            agent_messages = self.router._build_agent_history(
                event.conversation_history, self.agent_id
            )

            model_name = getattr(self.provider, "model_name", None) or getattr(
                self.provider, "model", None
            )

            # Stream response and buffer chunks (no longer emitting chunk events)
            chunks = []
            # Add timeout to prevent hanging
            import asyncio

            timeout_seconds = 120  # 2 minute timeout (with retries this is sufficient)

            try:
                async with asyncio.timeout(timeout_seconds):
                    async for chunk in self.provider.stream_response(
                        agent_messages, temperature=event.temperature
                    ):
                        chunks.append(chunk)
                        chunk_index += 1
            except asyncio.TimeoutError:
                logger.error(
                    f"Provider {self.provider.__class__.__name__} timed out after {timeout_seconds}s"
                )
                raise Exception(
                    f"Provider response timed out after {timeout_seconds} seconds"
                )

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
            provider_name = self.provider.__class__.__name__.replace(
                "Provider", ""
            ).lower()
            model_name = getattr(self.provider, "model_name", None) or getattr(
                self.provider, "model", None
            )

            prompt_tokens = 0
            completion_tokens = 0
            
            if hasattr(self.provider, "get_last_usage"):
                usage_data = self.provider.get_last_usage()
                if usage_data:
                    prompt_tokens = usage_data.get("prompt_tokens", 0)
                    completion_tokens = usage_data.get("completion_tokens", 0)
                    
                if not completion_tokens:
                    completion_tokens = estimate_tokens(content, model_name)
                    
                if not prompt_tokens:
                    prompt_tokens = estimate_messages_tokens(agent_messages, model_name)
            else:
                prompt_tokens = estimate_messages_tokens(agent_messages, model_name)
                completion_tokens = estimate_tokens(content, model_name)
            
            total_tokens = prompt_tokens + completion_tokens

            # Emit completion event
            await self.bus.emit(
                MessageCompleteEvent(
                    conversation_id=event.conversation_id,
                    agent_id=self.agent_id,
                    message=message,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    duration_ms=duration_ms,
                )
            )

            # Emit token usage event if we have actual usage data
            if hasattr(self.provider, "get_last_usage"):
                usage_data = self.provider.get_last_usage()
                if usage_data and "total_tokens" in usage_data:
                    # Extract provider name and model
                    provider_name = self.provider.__class__.__name__.replace(
                        "Provider", ""
                    )
                    # Get model name, ensuring we get a string not an object
                    model_name = getattr(self.provider, "model_name", None)
                    if not model_name:
                        model_obj = getattr(self.provider, "model", None)
                        if model_obj and hasattr(model_obj, "model_name"):
                            # Google's GenerativeModel has model_name attribute
                            model_name = model_obj.model_name
                        elif isinstance(model_obj, str):
                            model_name = model_obj
                        else:
                            model_name = "unknown"

                    # Ensure model_name is a string
                    if not isinstance(model_name, str):
                        model_name = str(model_name)

                    # Record the usage before getting stats so current_rate includes this request
                    self.token_tracker.record_usage(
                        provider_name.lower(), usage_data["total_tokens"], model_name
                    )

                    # Now get the updated usage stats
                    usage_stats = self.token_tracker.get_usage_stats(provider_name.lower())

                    # Create enhanced token usage event
                    token_event = TokenUsageEvent(
                        conversation_id=event.conversation_id,
                        provider=provider_name,
                        tokens_used=usage_data["total_tokens"],
                        tokens_per_minute_limit=usage_stats["rate_limit"],
                        current_usage_rate=usage_stats["current_rate"],
                    )
                    # Add agent_id as dynamic attribute (needed by tracking_event_bus)
                    token_event.agent_id = self.agent_id
                    # Add model as custom attribute (ensure it's a string)
                    # CRITICAL: Only set model if it's actually a string to prevent serialization issues
                    if isinstance(model_name, str) and model_name != "unknown":
                        # Double-check it's really a string and not an object
                        if type(model_name) is str:
                            token_event.model = model_name
                            # Debug log to track what we're setting
                            logger.debug(
                                f"Set token_event.model to: {model_name} (type: {type(model_name)})"
                            )
                        else:
                            logger.warning(
                                f"Model name is not a pure string: {type(model_name)}"
                            )

                    # Handle different naming conventions (Anthropic vs OpenAI)
                    token_event.prompt_tokens = usage_data.get(
                        "prompt_tokens", 0
                    ) or usage_data.get("input_tokens", 0)
                    token_event.completion_tokens = usage_data.get(
                        "completion_tokens", 0
                    ) or usage_data.get("output_tokens", 0)

                    # Final safety check before emitting
                    if hasattr(token_event, "model"):
                        model_val = getattr(token_event, "model")
                        if not isinstance(model_val, str):
                            logger.error(
                                f"CRITICAL: token_event.model is not a string! Type: {type(model_val)}"
                            )
                            # Remove the problematic attribute
                            delattr(token_event, "model")

                    await self.bus.emit(token_event)

        except Exception as e:
            # Emit error event
            error_str = str(e)

            # Check if this is a context limit error
            from .error_utils import ErrorClassifier
            error_classifier = ErrorClassifier()
            is_context_error = error_classifier.is_context_limit_error(e)

            # Determine if error is retryable using comprehensive error classification
            from .retry_utils import is_retryable_error
            retryable = not is_context_error and is_retryable_error(e)

            # Extract provider name from model
            provider_name = self.provider.__class__.__name__.replace("Provider", "")

            # Emit appropriate error event
            if is_context_error:
                # Emit a special context limit error event
                from ..core.events import ContextLimitEvent
                await self.bus.emit(
                    ContextLimitEvent(
                        conversation_id=event.conversation_id,
                        agent_id=self.agent_id,
                        turn_number=event.turn_number,
                        error_message=error_str,
                        provider=provider_name,
                    )
                )
            else:
                await self.bus.emit(
                    APIErrorEvent(
                        conversation_id=event.conversation_id,
                        error_type="api_error",
                        error_message=error_str,
                        context=f"During message generation for turn {event.turn_number}",
                        agent_id=self.agent_id,
                        provider=provider_name,
                        retryable=retryable,
                        retry_count=0,  # Retry tracking is handled internally by providers
                    )
                )

            # Log the error
            logger.error(f"Error in handle_message_request: {e}", exc_info=True)

            # For context limit errors, don't create a fallback response
            # The ContextLimitEvent will signal the conversation to end naturally
            if is_context_error:
                return  # Just return without sending a message
            
            # For other errors, create a fallback response
            fallback_content = "[Unable to generate response due to API error]"
            
            # Create a valid message response
            message = Message(
                role="assistant",
                content=fallback_content,
                agent_id=self.agent_id,
            )
            
            # Emit completion event with the fallback message
            await self.bus.emit(
                MessageCompleteEvent(
                    conversation_id=event.conversation_id,
                    agent_id=self.agent_id,
                    message=message,
                    tokens_used=0,  # No tokens for error response
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            )
            
            # Don't raise - let conversation continue
            return
