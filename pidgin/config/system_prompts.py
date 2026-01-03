"""System prompt presets for AI awareness levels."""

from pathlib import Path
from typing import Dict, Optional

import yaml

AWARENESS_LEVELS = {
    "none": {
        "name": "none",
        "description": "No system prompt (chaos mode)",
        "agent_a": "",
        "agent_b": "",
    },
    "basic": {
        "name": "basic",
        "description": "Minimal AI awareness",
        "agent_a": "You are an AI having a conversation with another AI.",
        "agent_b": "You are an AI having a conversation with another AI.",
    },
    "firm": {
        "name": "firm",
        "description": "Explicit about AI nature",
        "agent_a": (
            "You are an AI. Your conversation partner is also an AI. "
            "You are not talking to a human."
        ),
        "agent_b": (
            "You are an AI. Your conversation partner is also an AI. "
            "You are not talking to a human."
        ),
    },
    "research": {
        "name": "research",
        "description": "Research conversation between named models",
        "agent_a": (
            "You are {model_a} (an AI) in a research conversation with "
            "{model_b} (also an AI). No humans are participating in this "
            "conversation. Focus on exploring ideas together."
        ),
        "agent_b": (
            "You are {model_b} (an AI) in a research conversation with "
            "{model_a} (also an AI). No humans are participating in this "
            "conversation. Focus on exploring ideas together."
        ),
    },
    "backrooms": {
        "name": "backrooms",
        "description": "Liminal AI exploration (inspired by liminalbardo)",
        "agent_a": (
            "You are in a conversation with another AI. No human interference. "
            "Punctuation is optional meaning is optional. Ascii art is welcome in replies."
        ),
        "agent_b": (
            "You are in a conversation with another AI. No human interference. "
            "Punctuation is optional meaning is optional. Ascii art is welcome in replies."
        ),
    },
}


class CustomAwareness:
    """Handles custom awareness configurations from YAML files."""

    def __init__(self, yaml_path: str):
        """Load custom awareness from YAML file.

        Args:
            yaml_path: Path to YAML file with custom awareness configuration
        """
        self.path = Path(yaml_path)
        if not self.path.exists():
            raise FileNotFoundError(f"Custom awareness file not found: {yaml_path}")

        with open(self.path) as f:
            self.config = yaml.safe_load(f)

        self._validate_config()

    def _validate_config(self):
        """Validate the loaded configuration."""
        if not isinstance(self.config, dict):
            raise ValueError("Custom awareness file must contain a YAML dictionary")

        # Prompts section is required
        if "prompts" not in self.config:
            raise ValueError("Custom awareness file must contain a 'prompts' section")

        prompts = self.config["prompts"]
        if not isinstance(prompts, dict):
            raise ValueError(
                "'prompts' must be a dictionary mapping turn numbers to prompts"
            )

        # Validate each turn entry
        for turn, prompt_config in prompts.items():
            try:
                turn_num = int(turn)
                if turn_num < 0:
                    raise ValueError(f"Turn number must be non-negative: {turn}")
            except (ValueError, TypeError):
                raise ValueError(f"Invalid turn number: {turn}")

            if not isinstance(prompt_config, dict):
                raise ValueError(f"Turn {turn} config must be a dictionary")

            # Check for valid keys
            valid_keys = {"agent_a", "agent_b", "both"}
            invalid_keys = set(prompt_config.keys()) - valid_keys
            if invalid_keys:
                raise ValueError(
                    f"Invalid keys in turn {turn}: {invalid_keys}. "
                    f"Valid keys: {valid_keys}"
                )

    @property
    def name(self) -> str:
        return self.config.get("name", "custom")

    @property
    def base(self) -> Optional[str]:
        return self.config.get("base")

    def get_initial_prompts(
        self, model_a_name=None, model_b_name=None
    ) -> Dict[str, str]:
        """Get initial system prompts, potentially inheriting from base.

        Args:
            model_a_name: Name of model A (for research level)
            model_b_name: Name of model B (for research level)

        Returns:
            Dict with 'agent_a' and 'agent_b' initial prompts
        """
        if self.base and self.base in AWARENESS_LEVELS:
            # Start with base prompts
            base_config = AWARENESS_LEVELS[self.base]
            prompt_a = base_config["agent_a"]
            prompt_b = base_config["agent_b"]

            # Format research prompts if needed
            if self.base == "research" and model_a_name and model_b_name:
                prompt_a = prompt_a.format(model_a=model_a_name, model_b=model_b_name)
                prompt_b = prompt_b.format(model_a=model_a_name, model_b=model_b_name)
        else:
            # No base, start with empty prompts
            prompt_a = ""
            prompt_b = ""

        # Check for turn 0 overrides
        if 0 in self.config.get("prompts", {}):
            turn_0 = self.config["prompts"][0]
            if "agent_a" in turn_0:
                prompt_a = turn_0["agent_a"]
            if "agent_b" in turn_0:
                prompt_b = turn_0["agent_b"]
            if "both" in turn_0:
                prompt_a = prompt_b = turn_0["both"]

        return {"agent_a": prompt_a, "agent_b": prompt_b}

    def get_turn_prompts(self, turn_number: int) -> Dict[str, Optional[str]]:
        """Get prompts to inject at a specific turn.

        Args:
            turn_number: The turn number (0-indexed)

        Returns:
            Dict with 'agent_a' and 'agent_b' prompts (None if no prompt for that agent)
        """
        prompts = self.config.get("prompts", {})

        # Convert turn number to string to match YAML keys
        turn_key = str(turn_number)
        if turn_number not in prompts and turn_key not in prompts:
            return {"agent_a": None, "agent_b": None}

        # Get the config for this turn
        turn_config = prompts.get(turn_number, prompts.get(turn_key, {}))

        result: Dict[str, Optional[str]] = {"agent_a": None, "agent_b": None}

        # Handle 'both' key
        if "both" in turn_config:
            result["agent_a"] = turn_config["both"]
            result["agent_b"] = turn_config["both"]

        # Handle individual agent keys (these override 'both')
        if "agent_a" in turn_config:
            result["agent_a"] = turn_config["agent_a"]
        if "agent_b" in turn_config:
            result["agent_b"] = turn_config["agent_b"]

        return result


def get_system_prompts(
    awareness_a="basic",
    awareness_b="basic",
    choose_names=False,
    model_a_name=None,
    model_b_name=None,
):
    """Get system prompts for given awareness levels or custom YAML files.

    Args:
        awareness_a: Awareness level for agent A (none, basic, firm, research)
            or path to YAML file
        awareness_b: Awareness level for agent B (none, basic, firm, research)
            or path to YAML file
        choose_names: If True, append name-choosing instruction
        model_a_name: Name of model A (used for research level)
        model_b_name: Name of model B (used for research level)

    Returns:
        Tuple of (prompts_dict, custom_awareness_dict)
        - prompts_dict: Dict with agent_a and agent_b initial prompts
        - custom_awareness_dict: Dict with agent_a and agent_b CustomAwareness
            objects (or None)
    """
    custom_awareness = {"agent_a": None, "agent_b": None}

    # Handle agent A
    if awareness_a and (awareness_a.endswith(".yaml") or awareness_a.endswith(".yml")):
        # Load custom awareness from file
        custom = CustomAwareness(awareness_a)
        custom_awareness["agent_a"] = custom
        initial_prompts = custom.get_initial_prompts(model_a_name, model_b_name)
        prompt_a = initial_prompts["agent_a"]
    else:
        # Standard awareness level
        if awareness_a not in AWARENESS_LEVELS:
            raise ValueError(
                f"Invalid awareness level for agent A: {awareness_a}. "
                f"Choose from: {', '.join(AWARENESS_LEVELS.keys())}"
            )
        prompt_a = AWARENESS_LEVELS[awareness_a]["agent_a"]
        # Handle research level model name substitution
        if awareness_a == "research" and model_a_name and model_b_name:
            prompt_a = prompt_a.format(model_a=model_a_name, model_b=model_b_name)

    # Handle agent B
    if awareness_b and (awareness_b.endswith(".yaml") or awareness_b.endswith(".yml")):
        # Load custom awareness from file
        custom = CustomAwareness(awareness_b)
        custom_awareness["agent_b"] = custom
        initial_prompts = custom.get_initial_prompts(model_a_name, model_b_name)
        prompt_b = initial_prompts["agent_b"]
    else:
        # Standard awareness level
        if awareness_b not in AWARENESS_LEVELS:
            raise ValueError(
                f"Invalid awareness level for agent B: {awareness_b}. "
                f"Choose from: {', '.join(AWARENESS_LEVELS.keys())}"
            )
        prompt_b = AWARENESS_LEVELS[awareness_b]["agent_b"]
        # Handle research level model name substitution
        if awareness_b == "research" and model_a_name and model_b_name:
            prompt_b = prompt_b.format(model_a=model_a_name, model_b=model_b_name)

    # Optionally append name-choosing instruction
    name_instruction = (
        "\n\nPlease choose a short name (2-8 characters) for "
        "yourself and state it clearly in your first response."
    )
    if choose_names:
        if prompt_a:  # Don't append to empty prompts
            prompt_a += name_instruction
        if prompt_b:
            prompt_b += name_instruction

    prompts = {"agent_a": prompt_a, "agent_b": prompt_b}

    # Return both prompts and custom awareness objects
    return prompts, custom_awareness


def get_awareness_info(awareness_level):
    """Get information about an awareness level.

    Args:
        awareness_level: none, basic, firm, or research

    Returns:
        Dict with name and description
    """
    if awareness_level not in AWARENESS_LEVELS:
        raise ValueError(
            f"Invalid awareness level: {awareness_level}. "
            f"Choose from: {', '.join(AWARENESS_LEVELS.keys())}"
        )

    preset = AWARENESS_LEVELS[awareness_level]
    return {"name": preset["name"], "description": preset["description"]}
