import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, List, Optional

from openai import AsyncOpenAI

from ..core.types import Message
from .api_key_manager import APIKeyManager
from .base import Provider
from .error_utils import create_openai_error_handler

logger = logging.getLogger(__name__)

# Import model config classes from central location
from ..config.models import ModelConfig

# OpenAI model definitions
OPENAI_MODELS = {
    "gpt-4.1": ModelConfig(
        model_id="gpt-4.1",
        display_name="GPT 4.1",
        aliases=["gpt-4.1"],
        provider="openai",
        context_window=1000000,
        notes="Primary coding-focused model",
    ),
    "gpt-4.1-mini": ModelConfig(
        model_id="gpt-4.1-mini",
        display_name="GPT 4.1 MINI",
        aliases=["gpt"],
        provider="openai",
        context_window=1000000,
    ),
    "gpt-4.1-nano": ModelConfig(
        model_id="gpt-4.1-nano",
        display_name="GPT 4.1 NANO",
        aliases=["nano"],
        provider="openai",
        context_window=1000000,
    ),
    "o3": ModelConfig(
        model_id="o3",
        display_name="O3",
        aliases=["o3"],
        provider="openai",
        context_window=128000,
        notes="Premium reasoning model",
    ),
    "o3-mini": ModelConfig(
        model_id="o3-mini",
        display_name="O3 Mini",
        aliases=["o3-mini"],
        provider="openai",
        context_window=128000,
        notes="Small reasoning model",
    ),
    "o4-mini": ModelConfig(
        model_id="o4-mini",
        display_name="O4 Mini",
        aliases=["o4-mini"],
        provider="openai",
        context_window=128000,
        notes="Latest small reasoning model (recommended over o3-mini)",
    ),
    "o4-mini-high": ModelConfig(
        model_id="o4-mini-high",
        display_name="O4 Mini High",
        aliases=["o4-mini-high"],
        provider="openai",
        context_window=128000,
        notes="Enhanced reasoning variant",
    ),
    "gpt-4.5": ModelConfig(
        model_id="gpt-4.5",
        display_name="GPT 4.5",
        aliases=["gpt-4.5"],
        provider="openai",
        context_window=128000,
        deprecated=True,
        notes="Research preview - being deprecated July 2025",
    ),
    "gpt-4o": ModelConfig(
        model_id="gpt-4o",
        display_name="GPT 4O",
        aliases=["4o"],
        provider="openai",
        context_window=128000,
        notes="Multimodal model",
    ),
    "gpt-4o-mini": ModelConfig(
        model_id="gpt-4o-mini",
        display_name="GPT 4O MINI",
        aliases=["4o-mini"],
        provider="openai",
        context_window=128000,
        notes="Fast multimodal model",
    ),
}


class OpenAIProvider(Provider):
    """OpenAI API provider with friendly error handling."""

    def __init__(self, model: str):
        api_key = APIKeyManager.get_api_key("openai")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.error_handler = create_openai_error_handler()

    async def stream_response(
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        # Apply context truncation
        from .context_utils import apply_context_truncation

        truncated_messages = apply_context_truncation(
            messages, provider="openai", model=self.model, logger_name=__name__
        )

        # Convert to OpenAI format
        openai_messages = [
            {"role": m.role, "content": m.content} for m in truncated_messages
        ]

        # Initialize usage tracking
        self._last_usage = None

        # Retry logic for overloaded/rate limit errors
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Build parameters
                params = {
                    "model": self.model,
                    "messages": openai_messages,
                    "max_completion_tokens": 1000,
                    "stream": True,
                    "stream_options": {"include_usage": True},  # Request usage data
                }

                # Add temperature if specified (OpenAI allows 0-2)
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
                        logger.debug(f"OpenAI usage data captured: {self._last_usage}")
                return  # Success!

            except Exception as e:
                error_str = str(e)
                error_type = type(e).__name__.lower()

                # Check if it's a timeout error (by type name or content)
                if "timeout" in error_type or any(
                    err in error_str.lower() for err in ["timeout", "timed out"]
                ):
                    if attempt < max_retries - 1:
                        # Calculate exponential backoff with jitter
                        delay = base_delay * (2**attempt) + (0.1 * time.time() % 1)
                        # Log timeout without traceback
                        logger.info(
                            f"OpenAI request timed out, retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Max retries exhausted for timeout
                        friendly_error = self.error_handler.get_friendly_error(e)
                        logger.info(f"Timeout after retries: {friendly_error}")
                        raise Exception(friendly_error) from None

                # Check if it's a rate limit or overloaded error
                elif any(
                    err in error_str.lower()
                    for err in ["rate_limit", "rate limit", "overloaded", "429"]
                ):
                    if attempt < max_retries - 1:
                        # Calculate exponential backoff with jitter
                        delay = base_delay * (2**attempt) + (0.1 * time.time() % 1)
                        # Log rate limit without traceback
                        logger.info(f"OpenAI rate limit hit, retrying in {delay:.1f}s")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Max retries exhausted
                        friendly_error = self.error_handler.get_friendly_error(e)
                        if self.error_handler.should_suppress_traceback(e):
                            logger.info(f"Expected API error: {friendly_error}")
                        else:
                            logger.error(
                                f"API error after retries: {str(e)}", exc_info=True
                            )
                        raise Exception(friendly_error) from None
                else:
                    # Non-retryable error
                    friendly_error = self.error_handler.get_friendly_error(e)
                    if self.error_handler.should_suppress_traceback(e):
                        logger.info(f"Expected API error: {friendly_error}")
                    else:
                        logger.error(f"Unexpected API error: {str(e)}", exc_info=True)
                    raise Exception(friendly_error) from None

    def get_last_usage(self) -> Optional[Dict[str, int]]:
        """Get token usage from the last API call."""
        return self._last_usage
