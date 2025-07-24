"""Utilities for context window management across providers."""

import logging
from typing import List, Optional, Tuple

from ..core.types import Message
from .context_manager import ProviderContextManager

logger = logging.getLogger(__name__)


def apply_context_truncation(
    messages: List[Message],
    provider: str,
    model: Optional[str] = None,
    logger_name: Optional[str] = None,
    event_bus=None,
    conversation_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    turn_number: Optional[int] = None,
    allow_truncation: bool = False,
) -> List[Message]:
    """Apply context truncation to messages using ProviderContextManager.

    This is a centralized utility to avoid duplicating context management
    code across all providers.

    Args:
        messages: List of messages to potentially truncate
        provider: Provider name (e.g., "anthropic", "openai")
        model: Optional model name for model-specific limits
        logger_name: Optional logger name for provider-specific logging
        event_bus: Optional event bus for emitting truncation events
        conversation_id: Optional conversation ID for events
        agent_id: Optional agent ID for events
        turn_number: Optional turn number for events
        allow_truncation: If False (default), return all messages even if over limit.
                       If True, truncate to fit within context window.

    Returns:
        List of messages, potentially truncated to fit context limits
    """
    # Use provided logger or default
    log = logging.getLogger(logger_name) if logger_name else logger

    # Apply context management
    context_mgr = ProviderContextManager()
    truncated_messages = context_mgr.prepare_context(
        messages,
        provider=provider,
        model=model,
        event_bus=event_bus,
        conversation_id=conversation_id,
        agent_id=agent_id,
        turn_number=turn_number,
        allow_truncation=allow_truncation,
    )

    # Log if truncation occurred
    if len(truncated_messages) < len(messages):
        log.debug(
            f"Truncated from {len(messages)} to {len(truncated_messages)} messages "
            f"for {model or provider}"
        )

    return truncated_messages


def split_system_and_conversation_messages(
    messages: List[Message],
) -> Tuple[List[str], List[dict]]:
    """Split messages into system messages and conversation messages.

    This is a common pattern used by multiple providers.

    Args:
        messages: List of messages to split

    Returns:
        Tuple of (system_messages, conversation_messages) where:
        - system_messages: List of system message contents
        - conversation_messages: List of dicts with 'role' and 'content'
    """
    system_messages = []
    conversation_messages = []

    for m in messages:
        if m.role == "system":
            system_messages.append(m.content)
        else:
            conversation_messages.append({"role": m.role, "content": m.content})

    return system_messages, conversation_messages
