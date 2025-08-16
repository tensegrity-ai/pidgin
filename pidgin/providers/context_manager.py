# pidgin/providers/context_manager.py
"""Minimal context window management - just prevent errors, nothing fancy."""

import logging
from typing import List, Optional

from ..config.models import get_model_config
from ..core.events import ContextTruncationEvent
from ..core.types import Message

logger = logging.getLogger(__name__)


class ProviderContextManager:
    """Dead simple context truncation - just keep conversations under limits."""

    # Conservative limits to avoid errors (80% of actual limits)
    CONTEXT_LIMITS = {
        "anthropic": 160000,  # 200k actual
        "openai": 100000,  # 128k actual
        "google": 800000,  # 1M+ actual
        "xai": 100000,  # 128k actual
        "local": 4000,  # Most local models are 4k-8k
    }

    # Model-specific limits (when known)
    MODEL_LIMITS = {
        # Local models via Ollama
        "qwen2.5:3b": 32768,  # 32k context
        "phi3": 4096,  # 4k context
        "mistral": 8192,  # 8k context
        "llama3.2": 131072,  # 128k context
        # Add more as needed
    }

    # Token estimation: 1 token ≈ 3.5 chars (conservative for cost estimates)
    # Real ratios: English ~4.2, Code ~2.8, Dense text ~5.0
    CHARS_PER_TOKEN = 3.5

    def prepare_context(
        self,
        messages: List[Message],
        provider: str,
        model: Optional[str] = None,
        event_bus=None,
        conversation_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        turn_number: Optional[int] = None,
        allow_truncation: bool = False,
    ) -> List[Message]:
        """Keep messages under context limit - that's it.

        Args:
            messages: List of messages to process
            provider: Provider name
            model: Model identifier
            event_bus: Optional event bus for truncation events
            conversation_id: Optional conversation ID
            agent_id: Optional agent ID
            turn_number: Optional turn number
            allow_truncation: If False (default), return all messages even if over limit.
                           If True, truncate to fit within context window.
        """

        # Get model-specific limit from config if available
        limit = None
        if model:
            config = get_model_config(model)
            if config and config.context_window:
                # Use full context window, no conservative reduction
                limit = config.context_window
                logger.debug(
                    f"Using model-specific context limit for {model}: {limit:,} tokens"
                )

        # Fall back to local model limits
        if limit is None and model:
            limit = self.MODEL_LIMITS.get(model)
            if limit:
                logger.debug(
                    f"Using local model context limit for {model}: {limit:,} tokens"
                )

        # Final fallback to provider limits (as ultimate safety net)
        if limit is None:
            limit = self.CONTEXT_LIMITS.get(provider, 8000)
            logger.debug(
                f"Using provider default context limit for {provider}: {limit:,} tokens"
            )

        # Quick estimate of total size
        total_chars = sum(
            len(m.content) + 20 for m in messages
        )  # +20 for role/formatting
        estimated_tokens = int(total_chars / self.CHARS_PER_TOKEN)

        # If under limit, return as-is
        if estimated_tokens < limit:
            return messages

        # Over limit - check if truncation is allowed
        if not allow_truncation:
            logger.warning(
                f"Context exceeds limit ({estimated_tokens:,} > {limit:,} tokens) "
                f"but truncation is disabled. Returning all {len(messages)} messages. "
                f"Provider may return a context limit error."
            )
            return messages

        # Truncation is allowed - keep system messages + recent conversation
        system_messages = [m for m in messages if m.role == "system"]
        other_messages = [m for m in messages if m.role != "system"]

        # Binary search for how many recent messages fit
        left, right = 1, len(other_messages)
        best = 1

        while left <= right:
            mid = (left + right) // 2
            test_messages = system_messages + other_messages[-mid:]
            test_chars = sum(len(m.content) + 20 for m in test_messages)
            test_tokens = int(test_chars / self.CHARS_PER_TOKEN)

            if test_tokens < limit:
                best = mid
                left = mid + 1
            else:
                right = mid - 1

        result = system_messages + other_messages[-best:]
        final_tokens = int(
            sum(len(m.content) + 20 for m in result) / self.CHARS_PER_TOKEN
        )

        if len(result) < len(messages):
            # Log at INFO level with a minimal message for visibility
            logger.info(
                f"✂ Context truncated: {len(messages)} → {len(result)} messages"
            )
            logger.debug(
                f"Truncated {provider} context: {len(messages)} → {len(result)} messages "
                f"(~{estimated_tokens:,} → {final_tokens:,} tokens, limit: {limit:,})"
            )

            # Emit truncation event if event bus is available
            if (
                event_bus
                and conversation_id
                and agent_id is not None
                and turn_number is not None
            ):
                try:
                    import asyncio

                    event = ContextTruncationEvent(
                        conversation_id=conversation_id,
                        agent_id=agent_id,
                        provider=provider,
                        model=model or "unknown",
                        turn_number=turn_number,
                        original_message_count=len(messages),
                        truncated_message_count=len(result),
                        messages_dropped=len(messages) - len(result),
                    )
                    # Emit the event - EventBus.emit is always async
                    # Since we're already in an async context (providers are async),
                    # we can create a task to emit without blocking
                    try:
                        _loop = asyncio.get_running_loop()
                        asyncio.create_task(event_bus.emit(event))
                    except RuntimeError:
                        # No running loop, skip emission
                        logger.debug(
                            "No running event loop, skipping truncation event emission"
                        )
                except Exception as e:
                    logger.warning(f"Failed to emit truncation event: {e}")

        return result
