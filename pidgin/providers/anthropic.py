import logging
from collections.abc import AsyncGenerator
from typing import Dict, List, Optional

from anthropic import AsyncAnthropic

from ..core.types import Message
from .api_key_manager import APIKeyManager
from .base import Provider
from .error_utils import create_anthropic_error_handler
from .retry_utils import retry_with_exponential_backoff

logger = logging.getLogger(__name__)


class AnthropicProvider(Provider):
    """Anthropic API provider with friendly error handling."""

    def __init__(self, model: str):
        super().__init__()
        api_key = APIKeyManager.get_api_key("anthropic")
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.error_handler = create_anthropic_error_handler()

    async def stream_response(
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        # Apply context truncation
        from .context_utils import (
            apply_context_truncation,
            split_system_and_conversation_messages,
        )

        truncated_messages = apply_context_truncation(
            messages,
            provider="anthropic",
            model=self.model,
            logger_name=__name__,
            allow_truncation=self.allow_truncation,
        )

        # Extract system messages and conversation messages
        system_messages, conversation_messages = split_system_and_conversation_messages(
            truncated_messages
        )

        # Build API call parameters
        api_params = {
            "model": self.model,
            "messages": conversation_messages,
            "max_tokens": 1000,
        }

        # Add temperature if specified (Anthropic caps at 1.0)
        if temperature is not None:
            api_params["temperature"] = min(temperature, 1.0)

        # Add system parameter if we have system messages
        if system_messages:
            api_params["system"] = "\n\n".join(system_messages)

        # Validate we have at least one conversation message
        if not conversation_messages:
            raise ValueError(
                "Anthropic API requires at least one user or assistant message. "
                "Only system messages were provided."
            )

        # Define inner function for retry wrapper
        async def _make_api_call():
            # Use async streaming
            async with self.client.messages.stream(**api_params) as stream:
                async for text in stream.text_stream:
                    yield text
                # Capture usage data after stream completes
                final_message = await stream.get_final_message()
                if hasattr(final_message, "usage"):
                    self._last_usage = {
                        "input_tokens": getattr(final_message.usage, "input_tokens", 0),
                        "output_tokens": getattr(
                            final_message.usage, "output_tokens", 0
                        ),
                        "total_tokens": 0,  # Will be calculated
                    }
                    self._last_usage["total_tokens"] = (
                        self._last_usage["input_tokens"]
                        + self._last_usage["output_tokens"]
                    )

        # Initialize usage tracking
        self._last_usage = None

        # Use retry wrapper with exponential backoff
        try:
            async for chunk in retry_with_exponential_backoff(
                _make_api_call,
                max_retries=3,
                base_delay=1.0,
                retry_on=(Exception,),  # Retry on all exceptions for now
            ):
                yield chunk
        except Exception as e:
            # Get friendly error message
            friendly_error = self.error_handler.get_friendly_error(e)

            # Log appropriately based on error type
            if self.error_handler.should_suppress_traceback(e):
                logger.info(f"Expected API error: {friendly_error}")
            else:
                logger.error(f"Unexpected API error: {e!s}", exc_info=True)

            # Create a clean exception with friendly message
            raise Exception(friendly_error) from None

    def get_last_usage(self) -> Optional[Dict[str, int]]:
        """Get token usage from the last API call."""
        return self._last_usage
