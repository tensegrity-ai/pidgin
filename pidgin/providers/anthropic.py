import logging
from typing import AsyncGenerator, Dict, List, Optional

from anthropic import AsyncAnthropic

from ..config.model_types import ModelConfig
from ..core.types import Message
from .api_key_manager import APIKeyManager
from .base import Provider
from .error_utils import create_anthropic_error_handler
from .retry_utils import retry_with_exponential_backoff

logger = logging.getLogger(__name__)

# Anthropic model definitions from API response
ANTHROPIC_MODELS = {
    "claude-opus-4-20250514": ModelConfig(
        model_id="claude-opus-4-20250514",
        display_name="Claude Opus 4",
        aliases=["opus", "opus4", "claude-opus"],
        provider="anthropic",
        context_window=200000,
        created_at="2025-05-22T00:00:00Z",
        input_cost_per_million=15.00,
        output_cost_per_million=75.00,
        supports_caching=True,
        cache_read_cost_per_million=1.50,
        cache_write_cost_per_million=18.75,
        pricing_updated="2025-08-04",
    ),
    "claude-sonnet-4-20250514": ModelConfig(
        model_id="claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        aliases=["sonnet", "sonnet4", "claude-sonnet", "claude"],
        provider="anthropic",
        context_window=200000,
        created_at="2025-05-22T00:00:00Z",
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_caching=True,
        cache_read_cost_per_million=0.30,
        cache_write_cost_per_million=3.75,
        pricing_updated="2025-08-04",
    ),
    "claude-3-7-sonnet-20250219": ModelConfig(
        model_id="claude-3-7-sonnet-20250219",
        display_name="Claude Sonnet 3.7",
        aliases=["sonnet3.7", "claude-3.7"],
        provider="anthropic",
        context_window=200000,
        created_at="2025-02-24T00:00:00Z",
    ),
    "claude-3-5-sonnet-20241022": ModelConfig(
        model_id="claude-3-5-sonnet-20241022",
        display_name="Claude Sonnet 3.5 (New)",
        aliases=["sonnet3.5", "claude-3.5"],
        provider="anthropic",
        context_window=200000,
        created_at="2024-10-22T00:00:00Z",
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_caching=True,
        cache_read_cost_per_million=0.30,
        cache_write_cost_per_million=3.75,
        pricing_updated="2025-08-04",
    ),
    "claude-3-5-haiku-20241022": ModelConfig(
        model_id="claude-3-5-haiku-20241022",
        display_name="Claude Haiku 3.5",
        aliases=["haiku", "haiku3.5", "claude-haiku"],
        provider="anthropic",
        context_window=200000,
        created_at="2024-10-22T00:00:00Z",
        input_cost_per_million=0.80,
        output_cost_per_million=4.00,
        supports_caching=True,
        cache_read_cost_per_million=0.08,
        cache_write_cost_per_million=1.00,
        pricing_updated="2025-08-04",
    ),
    "claude-3-5-sonnet-20240620": ModelConfig(
        model_id="claude-3-5-sonnet-20240620",
        display_name="Claude Sonnet 3.5 (Old)",
        aliases=["sonnet3.5-old"],
        provider="anthropic",
        context_window=200000,
        created_at="2024-06-20T00:00:00Z",
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_caching=True,
        cache_read_cost_per_million=0.30,
        cache_write_cost_per_million=3.75,
        pricing_updated="2025-08-04",
    ),
    "claude-3-haiku-20240307": ModelConfig(
        model_id="claude-3-haiku-20240307",
        display_name="Claude Haiku 3",
        aliases=["haiku3", "claude-3-haiku"],
        provider="anthropic",
        context_window=200000,
        created_at="2024-03-07T00:00:00Z",
        input_cost_per_million=0.25,
        output_cost_per_million=1.25,
        supports_caching=True,
        cache_read_cost_per_million=0.03,
        cache_write_cost_per_million=0.30,
        pricing_updated="2025-08-04",
    ),
    "claude-3-opus-20240229": ModelConfig(
        model_id="claude-3-opus-20240229",
        display_name="Claude Opus 3",
        aliases=["opus3", "claude-3-opus"],
        provider="anthropic",
        context_window=200000,
        created_at="2024-02-29T00:00:00Z",
        input_cost_per_million=15.00,
        output_cost_per_million=75.00,
        supports_caching=True,
        cache_read_cost_per_million=1.50,
        cache_write_cost_per_million=18.75,
        pricing_updated="2025-08-04",
    ),
}


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
            messages, provider="anthropic", model=self.model, logger_name=__name__,
            allow_truncation=self.allow_truncation
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
                logger.error(f"Unexpected API error: {str(e)}", exc_info=True)

            # Create a clean exception with friendly message
            raise Exception(friendly_error) from None

    def get_last_usage(self) -> Optional[Dict[str, int]]:
        """Get token usage from the last API call."""
        return self._last_usage
