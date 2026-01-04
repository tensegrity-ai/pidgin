import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any, Dict, List, Optional

from ..core.types import Message
from .api_key_manager import APIKeyManager
from .base import Provider, ResponseChunk
from .error_utils import create_google_error_handler

logger = logging.getLogger(__name__)

try:
    from google import genai

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    genai = None


class GoogleProvider(Provider):
    def __init__(self, model: str):
        super().__init__()
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google GenAI not available. Install with: pip install google-genai"
            )

        api_key = APIKeyManager.get_api_key("google")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model
        self._last_usage: Optional[Dict[str, int]] = None
        self.error_handler = create_google_error_handler()

    async def stream_response(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        thinking_enabled: Optional[bool] = None,
        thinking_budget: Optional[int] = None,
    ) -> AsyncGenerator[ResponseChunk, None]:
        # Apply context truncation
        from .context_utils import apply_context_truncation

        truncated_messages = apply_context_truncation(
            messages,
            provider="google",
            model=self.model_name,
            logger_name=__name__,
            allow_truncation=self.allow_truncation,
        )

        # Convert to Google format
        # Google uses 'user' and 'model' roles instead of 'user' and 'assistant'
        # Google doesn't support system messages, so we skip them
        contents = []
        for m in truncated_messages:
            if m.role == "system":
                # Skip system messages as Google doesn't support them
                logger.debug(
                    f"Skipping system message for Google provider: {m.content[:50]}..."
                )
                continue
            role = "model" if m.role == "assistant" else m.role
            contents.append({"role": role, "parts": [{"text": m.content}]})

        # Retry logic for rate limits and transient errors
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Build config with optional temperature and thinking settings
                config_kwargs: Dict[str, Any] = {}
                if temperature is not None:
                    config_kwargs["temperature"] = temperature

                # Add thinking config if enabled
                if thinking_enabled:
                    config_kwargs["thinking_config"] = genai.types.ThinkingConfig(
                        include_thoughts=True
                    )

                config = (
                    genai.types.GenerateContentConfig(**config_kwargs)
                    if config_kwargs
                    else None
                )

                # Stream the response using new SDK API
                response = self.client.models.generate_content_stream(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )

                last_chunk = None
                for chunk in response:
                    # Check for parts with thought flag (thinking mode)
                    if (
                        hasattr(chunk, "candidates")
                        and chunk.candidates
                        and hasattr(chunk.candidates[0], "content")
                        and chunk.candidates[0].content
                        and hasattr(chunk.candidates[0].content, "parts")
                    ):
                        for part in chunk.candidates[0].content.parts:
                            if hasattr(part, "text") and part.text:
                                # Check if this is a thinking part
                                if hasattr(part, "thought") and part.thought:
                                    yield ResponseChunk(part.text, "thinking")
                                else:
                                    yield ResponseChunk(part.text, "response")
                    elif chunk.text:
                        # Fallback for simple text response
                        yield ResponseChunk(chunk.text, "response")
                    last_chunk = chunk

                # Try to extract usage data from the last chunk
                if last_chunk and hasattr(last_chunk, "usage_metadata"):
                    metadata = last_chunk.usage_metadata
                    if metadata:
                        self._last_usage = {
                            "prompt_tokens": getattr(metadata, "prompt_token_count", 0),
                            "completion_tokens": getattr(
                                metadata, "candidates_token_count", 0
                            ),
                            "total_tokens": getattr(metadata, "total_token_count", 0),
                        }
                        logger.debug(f"Google usage data captured: {self._last_usage}")

                return  # Success!

            except Exception as e:
                error_str = str(e)
                error_type = type(e).__name__.lower()

                # Check if it's a timeout error
                if "timeout" in error_type or any(
                    err in error_str.lower()
                    for err in ["timeout", "timed out", "deadline exceeded"]
                ):
                    if attempt < max_retries - 1:
                        # Calculate exponential backoff with jitter
                        delay = base_delay * (2**attempt) + (
                            0.1 * asyncio.get_event_loop().time() % 1
                        )
                        # Log timeout without traceback
                        logger.info(
                            f"Google API request timed out, retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Max retries exhausted for timeout
                        friendly_error = self.error_handler.get_friendly_error(e)
                        logger.info(f"Timeout after retries: {friendly_error}")
                        raise Exception(friendly_error) from None

                # Check if it's a rate limit or quota error
                elif any(
                    err in error_str.lower()
                    for err in [
                        "rate_limit",
                        "rate limit",
                        "quota",
                        "429",
                        "resource_exhausted",
                        "too many requests",
                    ]
                ):
                    if attempt < max_retries - 1:
                        # Calculate exponential backoff with jitter
                        delay = base_delay * (2**attempt) + (
                            0.1 * asyncio.get_event_loop().time() % 1
                        )
                        # Log rate limit without traceback
                        logger.info(
                            f"Google API rate limit hit, retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Max retries exhausted
                        friendly_error = self.error_handler.get_friendly_error(e)
                        if self.error_handler.should_suppress_traceback(e):
                            logger.info(f"Expected API error: {friendly_error}")
                        else:
                            logger.error(
                                f"API error after retries: {e!s}", exc_info=True
                            )
                        raise Exception(friendly_error) from None

                # Check if it's another retryable error
                elif any(
                    err in error_str.lower()
                    for err in ["unavailable", "internal", "500", "502", "503", "504"]
                ):
                    if attempt < max_retries - 1:
                        # Calculate exponential backoff with jitter
                        delay = base_delay * (2**attempt) + (
                            0.1 * asyncio.get_event_loop().time() % 1
                        )
                        logger.info(
                            f"Google API temporarily unavailable, retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Max retries exhausted
                        friendly_error = self.error_handler.get_friendly_error(e)
                        if self.error_handler.should_suppress_traceback(e):
                            logger.info(f"Expected API error: {friendly_error}")
                        else:
                            logger.error(
                                f"API error after retries: {e!s}", exc_info=True
                            )
                        raise Exception(friendly_error) from None
                else:
                    # Non-retryable error
                    friendly_error = self.error_handler.get_friendly_error(e)
                    if self.error_handler.should_suppress_traceback(e):
                        logger.info(f"Expected API error: {friendly_error}")
                    else:
                        logger.error(f"Unexpected API error: {e!s}", exc_info=True)
                    raise Exception(friendly_error) from None

    def get_last_usage(self) -> Optional[Dict[str, int]]:
        """Get token usage from the last API call."""
        return self._last_usage
