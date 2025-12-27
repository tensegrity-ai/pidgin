"""Configuration types for experiments."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExperimentConfig:
    """Configuration for an experiment run."""

    # Required fields
    name: str
    agent_a_model: str
    agent_b_model: str

    # Prompt configuration (matching CLI)
    custom_prompt: Optional[str] = None  # Custom prompt or path to .md file

    # Experiment parameters
    max_turns: int = 50  # Match CLI default
    repetitions: int = 10

    # Temperature settings (matching CLI)
    temperature: Optional[float] = None  # Temperature for both models
    temperature_a: Optional[float] = None  # Override for model A
    temperature_b: Optional[float] = None  # Override for model B

    # Extended thinking settings (matching CLI)
    think: bool = False  # Enable thinking for both agents
    think_a: bool = False  # Override for agent A
    think_b: bool = False  # Override for agent B
    think_budget: Optional[int] = None  # Max thinking tokens (default: 10000)

    # Awareness levels (matching CLI)
    awareness: str = "basic"  # Default for both agents
    awareness_a: Optional[str] = None  # Override for agent A
    awareness_b: Optional[str] = None  # Override for agent B

    # Parallel execution
    max_parallel: int = 1  # Default to sequential execution (1 conversation at a time)

    # Agent capabilities
    choose_names: bool = False

    # Convergence settings
    convergence_threshold: Optional[float] = (
        None  # Stop at threshold (None = use config default of 0.85)
    )
    convergence_action: str = "stop"  # 'stop', 'warn', or 'continue'

    # Display settings
    display_mode: str = (
        "none"  # Display mode for conversations: none, quiet, tail, chat
    )

    # Prompt settings
    prompt_tag: Optional[str] = (
        None  # Tag to prefix initial prompt (None = use config default)
    )

    # Context management
    allow_truncation: bool = False  # Allow message truncation to fit context windows

    # Branch metadata
    branch_from_conversation: Optional[str] = None  # Source conversation ID
    branch_from_turn: Optional[int] = None  # Turn number to branch from
    branch_messages: Optional[List[Any]] = None  # Pre-populated messages

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def get_conversation_config(self, repetition: int) -> Dict[str, Any]:
        """Get configuration for a specific conversation repetition.

        Args:
            repetition: 0-indexed repetition number

        Returns:
            Configuration dict for this specific conversation
        """
        config = self.dict()

        # Add repetition info
        config["repetition_number"] = repetition

        return config

    def validate(self) -> List[str]:
        """Validate configuration and return any errors."""
        errors = []

        if self.repetitions < 1:
            errors.append("repetitions must be at least 1")

        if self.max_turns < 1:
            errors.append("max_turns must be at least 1")

        # Validate awareness levels (matching CLI choices)
        valid_awareness = ("none", "basic", "firm", "research")

        # Check if awareness is a valid level or a YAML file path
        if self.awareness and not (
            self.awareness in valid_awareness
            or self.awareness.endswith(".yaml")
            or self.awareness.endswith(".yml")
        ):
            errors.append(
                f"awareness must be one of: {', '.join(valid_awareness)} or a YAML file"
            )

        if self.awareness_a and not (
            self.awareness_a in valid_awareness
            or self.awareness_a.endswith(".yaml")
            or self.awareness_a.endswith(".yml")
        ):
            errors.append(
                f"awareness_a must be one of: {', '.join(valid_awareness)} "
                f"or a YAML file"
            )

        if self.awareness_b and not (
            self.awareness_b in valid_awareness
            or self.awareness_b.endswith(".yaml")
            or self.awareness_b.endswith(".yml")
        ):
            errors.append(
                f"awareness_b must be one of: {', '.join(valid_awareness)} "
                f"or a YAML file"
            )

        if self.convergence_action not in ("stop", "warn", "continue"):
            errors.append("convergence_action must be 'stop', 'warn', or 'continue'")

        if self.convergence_threshold is not None:
            if not 0 <= self.convergence_threshold <= 1:
                errors.append("convergence_threshold must be between 0 and 1")

        if self.temperature is not None:
            if not 0 <= self.temperature <= 2:
                errors.append("temperature must be between 0 and 2")

        if self.temperature_a is not None:
            if not 0 <= self.temperature_a <= 2:
                errors.append("temperature_a must be between 0 and 2")

        if self.temperature_b is not None:
            if not 0 <= self.temperature_b <= 2:
                errors.append("temperature_b must be between 0 and 2")

        return errors
