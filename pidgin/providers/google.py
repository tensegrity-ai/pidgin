import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Dict, List, Optional

from ..core.types import Message
from .api_key_manager import APIKeyManager
from .base import Provider, ResponseChunk
from .error_utils import create_google_error_handler

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    genai = None


class GoogleProvider(Provider):
    def __init__(self, model: str):
        super().__init__()
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google Generative AI not available. Install with: "
                "pip install google-generativeai"
            )

        api_key = APIKeyManager.get_api_key("google")
        genai.configure(api_key=api_key)
        self.model_name = model  # Store the model name as string
        self.model = genai.GenerativeModel(model)
        # Extra safety: ensure model_name is always a string
        if not isinstance(self.model_name, str):
            logger.error(
                f"GoogleProvider model_name is not a string: {type(self.model_name)}"
            )
            self.model_name = str(model)
        self._last_usage: Optional[Dict[str, int]] = None
        self.error_handler = create_google_error_handler()

    async def stream_response(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        thinking_enabled: Optional[bool] = None,
        thinking_budget: Optional[int] = None,
    ) -> AsyncGenerator[ResponseChunk, None]:
        # Note: thinking_enabled and thinking_budget are not yet supported by Google
        # Apply context truncation
        from .context_utils import apply_context_truncation

        truncated_messages = apply_context_truncation(
            messages,
            provider="google",
            model=self.model.model_name if hasattr(self.model, "model_name") else None,
            logger_name=__name__,
            allow_truncation=self.allow_truncation,
        )

        # Convert to Google format
        # Google uses 'user' and 'model' roles instead of 'user' and 'assistant'
        # Google doesn't support system messages, so we skip them
        google_messages = []
        for m in truncated_messages:
            if m.role == "system":
                # Skip system messages as Google doesn't support them
                logger.debug(
                    f"Skipping system message for Google provider: {m.content[:50]}..."
                )
                continue
            role = "model" if m.role == "assistant" else m.role
            google_messages.append({"role": role, "parts": [m.content]})

        # Initialize usage tracking
        # (already initialized in __init__)

        # Retry logic for rate limits and transient errors
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Create chat session
                chat = self.model.start_chat(history=google_messages[:-1])  # type: ignore[arg-type]

                # Build generation config if temperature is specified
                generation_config = {}
                if temperature is not None:
                    generation_config["temperature"] = temperature

                # Stream the response
                response = chat.send_message(
                    google_messages[-1]["parts"][0],
                    stream=True,
                    generation_config=generation_config if generation_config else None,  # type: ignore[arg-type]
                )

                last_chunk = None
                for chunk in response:
                    if chunk.text:
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
