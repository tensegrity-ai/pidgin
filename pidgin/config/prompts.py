"""Prompt building utilities."""

from typing import Optional


def build_initial_prompt(custom_prompt: Optional[str] = None) -> Optional[str]:
    """Build the initial prompt for a conversation.

    Args:
        custom_prompt: Custom prompt text

    Returns:
        The initial prompt string, or None for cold start
    """
    return custom_prompt
