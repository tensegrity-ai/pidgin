import logging
from collections.abc import AsyncGenerator
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from ..core.types import Message
from .api_key_manager import APIKeyManager
from .base import DEFAULT_MAX_TOKENS, Provider, ResponseChunk
from .error_utils import create_anthropic_error_handler
from .retry_utils import retry_with_exponential_backoff

logger = logging.getLogger(__name__)


class AnthropicProvider(Provider):
    """Anthropic API provider with friendly error handling and extended thinking support."""

    def __init__(self, model: str):
        super().__init__()
        api_key = APIKeyManager.get_api_key("anthropic")
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.error_handler = create_anthropic_error_handler()

    async def stream_response(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        thinking_enabled: Optional[bool] = None,
        thinking_budget: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[ResponseChunk, None]:
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
        api_params: Dict[str, Any] = {
            "model": self.model,
            "messages": conversation_messages,
            # Explicit max_tokens wins; otherwise extended thinking needs extra
            # headroom for the reasoning trace, plain responses use the default.
            "max_tokens": max_tokens
            if max_tokens is not None
            else (16000 if thinking_enabled else DEFAULT_MAX_TOKENS),
        }

        # Add temperature if specified (Anthropic caps at 1.0). Two reasons we
        # may not send it: (1) adaptive thinking manages its own sampling, and
        # Claude 4.6+ reject an explicit temperature alongside thinking; (2) the
        # newest models (Opus 4.7/4.8, Fable 5) removed sampling parameters
        # entirely and 400 on any temperature, thinking or not. _resolve_temperature
        # handles case (2) via the registry; the thinking guard handles case (1).
        resolved_temperature = self._resolve_temperature(temperature, self.model)
        if resolved_temperature is not None and not thinking_enabled:
            api_params["temperature"] = min(resolved_temperature, 1.0)

        # Add system parameter if we have system messages
        if system_messages:
            api_params["system"] = "\n\n".join(system_messages)

        # Enable prompt caching. Top-level cache_control auto-caches the longest
        # stable prefix (system prompt + prior turns); each turn resends the full
        # growing history, so the cached prefix is reused on every subsequent
        # request. Caching is transparent to model output — it only changes
        # cost/latency, not the conversation — so it does not affect experiment
        # validity. Conversations below the model's minimum cacheable prefix
        # (~1024-4096 tokens) silently won't cache, which is fine.
        api_params["cache_control"] = {"type": "ephemeral"}

        # Enable extended thinking via adaptive mode. The older
        # {"type": "enabled", "budget_tokens": N} form is rejected (HTTP 400) by
        # current Claude models (4.6+); adaptive lets the model decide how much
        # to think. thinking_budget no longer maps to a hard token cap here and
        # is accepted only for interface compatibility with other providers.
        if thinking_enabled:
            api_params["thinking"] = {"type": "adaptive"}

        # Validate we have at least one conversation message
        if not conversation_messages:
            raise ValueError(
                "Anthropic API requires at least one user or assistant message. "
                "Only system messages were provided."
            )

        # Track whether we're processing thinking content
        thinking_mode = thinking_enabled

        # Define inner function for retry wrapper
        async def _make_api_call():
            nonlocal thinking_mode
            # Use async streaming with events for thinking support
            async with self.client.messages.stream(**api_params) as stream:
                async for event in stream:
                    # Handle content deltas
                    if event.type == "content_block_delta":
                        delta = event.delta
                        # Check for thinking_delta type (Claude 4 extended thinking)
                        delta_type = getattr(delta, "type", None)
                        if delta_type == "thinking_delta" or hasattr(delta, "thinking"):
                            thinking_text = getattr(delta, "thinking", "")
                            if thinking_text:
                                yield ResponseChunk(thinking_text, "thinking")
                        elif delta_type == "text_delta" or hasattr(delta, "text"):
                            text = getattr(delta, "text", "")
                            if text:
                                yield ResponseChunk(text, "response")

                # Capture usage data after stream completes
                final_message = await stream.get_final_message()
                if hasattr(final_message, "usage"):
                    usage = final_message.usage
                    # Anthropic reports input_tokens as the *uncached* remainder;
                    # cache reads/writes are separate, additive fields. Normalize
                    # input_tokens to the full input total (uncached + cache read
                    # + cache write) so prompt_tokens is consistent with
                    # OpenAI/Google (whose prompt counts already include cache),
                    # and so the importer can subtract the cache portions to bill
                    # them at their own rates without double-counting.
                    uncached_input = getattr(usage, "input_tokens", 0) or 0
                    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
                    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
                    output_tokens = getattr(usage, "output_tokens", 0) or 0
                    total_input = uncached_input + cache_write + cache_read
                    self._last_usage = {
                        "input_tokens": total_input,
                        "output_tokens": output_tokens,
                        "cache_read_tokens": cache_read,
                        "cache_write_tokens": cache_write,
                        "total_tokens": total_input + output_tokens,
                    }

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
                # Filter out status message strings, only yield ResponseChunk
                if isinstance(chunk, ResponseChunk):
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
