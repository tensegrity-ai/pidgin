"""Token counting utilities for providers."""

from typing import Any, Dict, List

from ..core.types import Message


def estimate_tokens(text: str, model: str = None) -> int:
    """Estimate token count for text.

    This uses heuristics that approximate tokenization:
    - Average English word is ~1.3 tokens
    - Average character count is ~4 characters per token
    - Adjustments for different model families

    Args:
        text: Text to count tokens for
        model: Optional model name for model-specific adjustments

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Base estimation: characters / 4
    char_estimate = len(text) / 4

    # Word-based estimation: words * 1.3
    words = text.split()
    word_estimate = len(words) * 1.3

    # Use average of both methods
    base_estimate = int((char_estimate + word_estimate) / 2)

    # Model-specific adjustments
    if model:
        if "gpt-4" in model or "gpt-3.5" in model:
            # GPT models tend to have slightly more tokens
            return int(base_estimate * 1.1)
        elif "claude" in model:
            # Claude tokenization is similar
            return base_estimate
        elif "gemini" in model:
            # Gemini might have different tokenization
            return int(base_estimate * 1.05)

    return base_estimate


def estimate_messages_tokens(messages: List[Message], model: str = None) -> int:
    """Estimate total tokens for a list of messages.

    Includes overhead for message structure (role, etc).

    Args:
        messages: List of messages
        model: Optional model name

    Returns:
        Estimated total token count
    """
    total = 0

    for message in messages:
        # Message content
        total += estimate_tokens(message.content, model)

        # Overhead for message structure (role, separators)
        total += 4  # Approximate overhead per message

    # Additional overhead for conversation structure
    total += 3

    return total


def parse_usage_from_response(
    response: Dict[str, Any], provider: str
) -> Dict[str, int]:
    """Extract token usage from provider response.

    Different providers return usage data in different formats.

    Args:
        response: Raw response from provider
        provider: Provider name (openai, anthropic, etc)

    Returns:
        Dict with 'prompt_tokens', 'completion_tokens', 'total_tokens'
    """
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    if provider == "openai":
        # OpenAI format: response.usage.prompt_tokens, etc
        if hasattr(response, "usage") and response.usage:
            usage["prompt_tokens"] = getattr(response.usage, "prompt_tokens", 0)
            usage["completion_tokens"] = getattr(response.usage, "completion_tokens", 0)
            usage["total_tokens"] = getattr(response.usage, "total_tokens", 0)

    elif provider == "anthropic":
        # Anthropic format: response.usage.input_tokens, output_tokens
        if hasattr(response, "usage") and response.usage:
            usage["prompt_tokens"] = getattr(response.usage, "input_tokens", 0)
            usage["completion_tokens"] = getattr(response.usage, "output_tokens", 0)
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]

    elif provider == "google":
        # Google format might be in metadata
        if hasattr(response, "metadata") and response.metadata:
            # This is approximate - need to check actual format
            usage["prompt_tokens"] = response.metadata.get("input_token_count", 0)
            usage["completion_tokens"] = response.metadata.get("output_token_count", 0)
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]

    return usage
