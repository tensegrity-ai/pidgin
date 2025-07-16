"""Agent naming and name coordination logic."""

import re
from typing import Dict, Optional

from ..config.models import get_model_config
from .types import Agent


class NameCoordinator:
    """Handles agent naming, name extraction, and display name assignment."""

    def __init__(self):
        """Initialize name coordinator."""
        self.choose_names_mode = False
        self.agent_chosen_names: Dict[str, str] = {}

    def initialize_name_mode(self, choose_names: bool):
        """Set up name choosing mode.

        Args:
            choose_names: Whether agents should choose their own names
        """
        self.choose_names_mode = choose_names
        self.agent_chosen_names = {}

    def get_provider_name(self, model: str) -> str:
        """Get provider name from model.

        Args:
            model: Model name or alias

        Returns:
            Provider name (anthropic, openai, etc)
        """
        config = get_model_config(model)
        if config:
            return config.provider

        # Fallback pattern matching
        model_lower = model.lower()
        if "claude" in model_lower:
            return "anthropic"
        elif model_lower.startswith("gpt") or model_lower.startswith("o"):
            return "openai"
        elif "gemini" in model_lower:
            return "google"
        elif "grok" in model_lower:
            return "xai"
        else:
            return "openai"  # Default

    def extract_chosen_name(self, message_content: str) -> Optional[str]:
        """Extract self-chosen name from first response.

        Args:
            message_content: The message content to extract name from

        Returns:
            Extracted name or None if no name found
        """
        # Look for patterns like:
        # "I'll go by X" or "I'll go by [X]"
        # "Call me X" or "Call me [X]"
        # "I'll be X" or "I'll be [X]"
        # "My name is X" or "My name is [X]"
        # "I choose X" or "I choose [X]"
        # Also handle: "I am [X]", "[X] here", etc.

        # First try specific patterns
        patterns = [
            r"I'll (?:go by|be|choose) \[?(\w{2,8})\]?",
            r"Call me \[?(\w{2,8})\]?",
            r"My name is \[?(\w{2,8})\]?",
            r"I (?:choose|select) \[?(\w{2,8})\]?",
            r"I am \[?(\w{2,8})\]?",
            r"^\[?(\w{2,8})\]? here",  # "[Name] here" at start of message
        ]

        for pattern in patterns:
            match = re.search(pattern, message_content, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1)
                # Clean up the name - remove any remaining brackets
                name = name.strip("[]")
                return name

        # Fallback - look for any quoted short name (with or without brackets)
        quote_match = re.search(r'["\']\[?(\w{2,8})\]?["\']', message_content)
        if quote_match:
            name = quote_match.group(1)
            # Clean up the name - remove any remaining brackets
            name = name.strip("[]")
            return name

        # Additional fallback - look for standalone bracketed names
        bracket_match = re.search(r"\[(\w{2,8})\]", message_content)
        if bracket_match:
            return bracket_match.group(1)

        return None

    def assign_display_names(self, agent_a: Agent, agent_b: Agent):
        """Assign display names to agents based on their models.

        Args:
            agent_a: First agent
            agent_b: Second agent
        """
        config_a = get_model_config(agent_a.model)
        config_b = get_model_config(agent_b.model)

        if config_a and config_b:
            # Store the model shortnames
            agent_a.model_shortname = config_a.shortname
            agent_b.model_shortname = config_b.shortname

            if config_a.shortname == config_b.shortname:
                # Same model - add numbers
                agent_a.display_name = f"{config_a.shortname}-1"
                agent_b.display_name = f"{config_b.shortname}-2"
            else:
                # Different models - use shortnames directly
                agent_a.display_name = config_a.shortname
                agent_b.display_name = config_b.shortname
        else:
            # Fallback to agent IDs
            agent_a.display_name = "Agent A"
            agent_b.display_name = "Agent B"
            agent_a.model_shortname = None
            agent_b.model_shortname = None
