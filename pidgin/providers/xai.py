import logging
from collections.abc import AsyncGenerator
from typing import Dict, List, Optional

from ..core.types import Message
from .api_key_manager import APIKeyManager
from .base import Provider, ResponseChunk
from .retry_utils import retry_with_exponential_backoff

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None  # type: ignore[assignment,misc]


class xAIProvider(Provider):
    def __init__(self, model: str):
        super().__init__()
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI client not available. Install with: pip install openai"
            )

        api_key = APIKeyManager.get_api_key("xai")

        # xAI uses OpenAI-compatible API with custom base URL
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        self.model = model
        self._last_usage = None
        # Use the xAI-specific error handler
        from .error_utils import create_xai_error_handler

        self.error_handler = create_xai_error_handler()

    async def stream_response(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        thinking_enabled: Optional[bool] = None,
        thinking_budget: Optional[int] = None,
    ) -> AsyncGenerator[ResponseChunk, None]:
        # Note: thinking_enabled and thinking_budget are not supported by xAI
        # Apply context truncation
        from .context_utils import apply_context_truncation

        truncated_messages = apply_context_truncation(
            messages,
            provider="xai",
            model=self.model,
            logger_name=__name__,
            allow_truncation=self.allow_truncation,
        )

        # Convert to OpenAI format (xAI is OpenAI-compatible)
        openai_messages = [
            {"role": m.role, "content": m.content} for m in truncated_messages
        ]

        # Define inner function for retry wrapper
        async def _make_api_call():
            # Build parameters
            params = {
                "model": self.model,
                "messages": openai_messages,
                "max_tokens": 1000,
                "stream": True,
                "stream_options": {
                    "include_usage": True
                },  # Request usage data like OpenAI
            }

            # Add temperature if specified (xAI/OpenAI allows 0-2)
            if temperature is not None:
                params["temperature"] = temperature

            stream = await self.client.chat.completions.create(**params)

            async for chunk in stream:
                # Handle content chunks
                if (
                    chunk.choices
                    and len(chunk.choices) > 0
                    and chunk.choices[0].delta.content
                ):
                    yield ResponseChunk(chunk.choices[0].delta.content, "response")

                # Check for usage data in the final chunk
                if hasattr(chunk, "usage") and chunk.usage:
                    self._last_usage = {
                        "prompt_tokens": getattr(chunk.usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(
                            chunk.usage, "completion_tokens", 0
                        ),
                        "total_tokens": getattr(chunk.usage, "total_tokens", 0),
                    }
                    logger.debug(f"xAI usage data captured: {self._last_usage}")

        # Initialize usage tracking
        self._last_usage = None

        # Use retry wrapper with exponential backoff
        try:
            async for response_chunk in retry_with_exponential_backoff(
                _make_api_call,
                max_retries=3,
                base_delay=1.0,
                retry_on=(Exception,),  # Retry on all exceptions
            ):
                # Filter out status message strings, only yield ResponseChunk
                if isinstance(response_chunk, ResponseChunk):
                    yield response_chunk
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
