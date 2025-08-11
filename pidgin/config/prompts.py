"""Prompt building utilities."""

from typing import Optional


def build_initial_prompt(custom_prompt: Optional[str] = None) -> str:
    """Build the initial prompt for a conversation.

    Args:
        custom_prompt: Custom prompt text

    Returns:
        The initial prompt string
    """
    if custom_prompt:
        return custom_prompt
    
    return "I'm looking forward to your conversation."
