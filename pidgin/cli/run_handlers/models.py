"""Data models for run command configuration."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentConfig:
    """Configuration for agent models and parameters."""

    agent_a: Optional[str] = None
    agent_b: Optional[str] = None
    temperature: Optional[float] = None
    temp_a: Optional[float] = None
    temp_b: Optional[float] = None
    awareness: str = "basic"
    awareness_a: Optional[str] = None
    awareness_b: Optional[str] = None
    think: bool = False
    think_a: bool = False
    think_b: bool = False
    think_budget: Optional[int] = None


@dataclass
class ConversationConfig:
    """Configuration for conversation parameters."""

    prompt: Optional[str] = None
    turns: int = 5  # Default from constants
    repetitions: int = 1
    choose_names: bool = False
    prompt_tag: str = "[HUMAN]"
    meditation: bool = False


@dataclass
class ConvergenceConfig:
    """Configuration for convergence detection."""

    convergence_threshold: Optional[float] = None
    convergence_action: Optional[str] = None
    convergence_profile: str = "balanced"


@dataclass
class DisplayConfig:
    """Configuration for display and output options."""

    quiet: bool = False
    tail: bool = False
    notify: bool = False
    show_system_prompts: bool = False


@dataclass
class ExecutionConfig:
    """Configuration for execution parameters."""

    name: Optional[str] = None
    output: Optional[str] = None
    max_parallel: int = 1
    allow_truncation: bool = False


@dataclass
class RunConfig:
    """Complete configuration for run command."""

    agents: AgentConfig
    conversation: ConversationConfig
    convergence: ConvergenceConfig
    display: DisplayConfig
    execution: ExecutionConfig
    spec_file: Optional[str] = None

    @classmethod
    def from_cli_args(cls, **kwargs) -> "RunConfig":
        """Create RunConfig from CLI arguments.

        Args:
            **kwargs: All CLI arguments from the run command

        Returns:
            RunConfig instance with organized parameters
        """
        return cls(
            agents=AgentConfig(
                agent_a=kwargs.get("agent_a"),
                agent_b=kwargs.get("agent_b"),
                temperature=kwargs.get("temperature"),
                temp_a=kwargs.get("temp_a"),
                temp_b=kwargs.get("temp_b"),
                awareness=kwargs.get("awareness", "basic"),
                awareness_a=kwargs.get("awareness_a"),
                awareness_b=kwargs.get("awareness_b"),
                think=kwargs.get("think", False),
                think_a=kwargs.get("think_a", False),
                think_b=kwargs.get("think_b", False),
                think_budget=kwargs.get("think_budget"),
            ),
            conversation=ConversationConfig(
                prompt=kwargs.get("prompt"),
                turns=kwargs.get("turns", 5),
                repetitions=kwargs.get("repetitions", 1),
                choose_names=kwargs.get("choose_names", False),
                prompt_tag=kwargs.get("prompt_tag", "[HUMAN]"),
                meditation=kwargs.get("meditation", False),
            ),
            convergence=ConvergenceConfig(
                convergence_threshold=kwargs.get("convergence_threshold"),
                convergence_action=kwargs.get("convergence_action"),
                convergence_profile=kwargs.get("convergence_profile", "balanced"),
            ),
            display=DisplayConfig(
                quiet=kwargs.get("quiet", False),
                tail=kwargs.get("tail", False),
                notify=kwargs.get("notify", False),
                show_system_prompts=kwargs.get("show_system_prompts", False),
            ),
            execution=ExecutionConfig(
                name=kwargs.get("name"),
                output=kwargs.get("output"),
                max_parallel=kwargs.get("max_parallel", 1),
                allow_truncation=kwargs.get("allow_truncation", False),
            ),
            spec_file=kwargs.get("spec_file"),
        )
