import logging
from typing import AsyncGenerator, Dict, List, Optional

from ..core.types import Message
from .api_key_manager import APIKeyManager
from .base import Provider
from .error_utils import ProviderErrorHandler

logger = logging.getLogger(__name__)

# Import model config classes from central location
from ..config.models import ModelCharacteristics, ModelConfig

# xAI model definitions
XAI_MODELS = {
    "grok-3": ModelConfig(
        model_id="grok-3",
        shortname="Grok-3",
        aliases=["grok"],
        provider="xai",
        context_window=131072,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="long",
            recommended_pairings=["gpt-4.1", "claude-4-opus-20250514"],
            conversation_style="analytical",
        ),
        notes="Latest Grok model with impressive HLE scores",
    ),
    "grok-beta": ModelConfig(
        model_id="grok-beta",
        shortname="Grok-Beta",
        aliases=["grok-beta", "xai"],
        provider="xai",
        context_window=131072,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="medium",
            recommended_pairings=["gpt-4o", "claude-4-sonnet-20250514"],
            conversation_style="analytical",
        ),
        notes="xAI's flagship model",
    ),
    "grok-2-1212": ModelConfig(
        model_id="grok-2-1212",
        shortname="Grok-2",
        aliases=["grok-2"],
        provider="xai",
        context_window=131072,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="medium",
            recommended_pairings=["gpt-4.1", "claude-4-sonnet-20250514"],
            conversation_style="analytical",
        ),
        notes="Latest Grok model",
    ),
}

try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None


class xAIProvider(Provider):
    def __init__(self, model: str):
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI client not available. Install with: " "pip install openai"
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
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        # Apply context truncation
        from .context_utils import apply_context_truncation

        truncated_messages = apply_context_truncation(
            messages, provider="xai", model=self.model, logger_name=__name__
        )

        # Convert to OpenAI format (xAI is OpenAI-compatible)
        openai_messages = [
            {"role": m.role, "content": m.content} for m in truncated_messages
        ]

        try:
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
                    yield chunk.choices[0].delta.content

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
