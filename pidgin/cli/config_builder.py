"""Build ExperimentConfig from CLI arguments."""

from typing import Optional, Tuple

# Create display instance
from rich.console import Console

from ..config.config import Config
from ..config.defaults import get_smart_convergence_defaults
from ..config.resolution import resolve_temperatures
from ..experiments import ExperimentConfig
from ..ui.display_utils import DisplayUtils
from .helpers import (
    build_initial_prompt,
    validate_model_id,
)
from .name_generator import generate_experiment_name

console = Console()
display = DisplayUtils(console)


class ConfigBuilder:
    """Build ExperimentConfig from CLI arguments."""

    def build_config(
        self,
        agent_a: str,
        agent_b: str,
        repetitions: int,
        max_turns: int,
        temperature: Optional[float] = None,
        temp_a: Optional[float] = None,
        temp_b: Optional[float] = None,
        prompt: Optional[str] = None,
        name: Optional[str] = None,
        max_parallel: int = 1,
        convergence_threshold: Optional[float] = None,
        convergence_action: Optional[str] = None,
        convergence_profile: str = "balanced",
        awareness: str = "basic",
        awareness_a: Optional[str] = None,
        awareness_b: Optional[str] = None,
        choose_names: bool = False,
        display_mode: str = "chat",
        prompt_tag: Optional[str] = None,
        allow_truncation: bool = False,
        think: bool = False,
        think_a: bool = False,
        think_b: bool = False,
        think_budget: Optional[int] = None,
    ) -> Tuple[ExperimentConfig, str, str]:
        """Build experiment configuration from CLI arguments.

        Returns:
            Tuple of (config, agent_a_name, agent_b_name)
        """
        # Validate models
        agent_a_id, agent_a_name = validate_model_id(agent_a)
        agent_b_id, agent_b_name = validate_model_id(agent_b)

        # Handle temperature settings
        resolved_temp_a, resolved_temp_b = resolve_temperatures(
            temperature, temp_a, temp_b
        )

        # Build initial prompt
        initial_prompt = build_initial_prompt(prompt)

        # Set convergence profile in config
        config = Config()
        config.set("convergence.profile", convergence_profile)

        # Add smart convergence defaults for API models
        final_convergence_threshold = convergence_threshold
        final_convergence_action = convergence_action

        if convergence_threshold is None:
            default_threshold, default_action = get_smart_convergence_defaults(
                agent_a_id, agent_b_id
            )
            if default_threshold is not None:
                final_convergence_threshold = default_threshold
                if convergence_action is None:
                    final_convergence_action = default_action
                # Log this default
                display.dim(
                    f"Using default convergence threshold: {default_threshold} "
                    f"→ {default_action}"
                )

        # Default convergence action
        if final_convergence_action is None:
            final_convergence_action = "stop"  # Always use 'stop' as default

        # Generate fun name if not provided
        final_name = name
        if not final_name:
            final_name = generate_experiment_name()
            display.dim(f"Generated experiment name: {final_name}")

        # Create experiment configuration
        experiment_config = ExperimentConfig(
            name=final_name,
            agent_a_model=agent_a_id,
            agent_b_model=agent_b_id,
            repetitions=repetitions,
            max_turns=max_turns,
            temperature_a=resolved_temp_a,
            temperature_b=resolved_temp_b,
            think=think,
            think_a=think_a,
            think_b=think_b,
            think_budget=think_budget,
            custom_prompt=initial_prompt,
            max_parallel=max_parallel,
            convergence_threshold=final_convergence_threshold,
            convergence_action=final_convergence_action,
            awareness=awareness,
            awareness_a=awareness_a,
            awareness_b=awareness_b,
            choose_names=choose_names,
            display_mode=display_mode,
            prompt_tag=prompt_tag,
            allow_truncation=allow_truncation,
        )

        return experiment_config, agent_a_name, agent_b_name

    def show_config_info(
        self,
        config: ExperimentConfig,
        agent_a_name: str,
        agent_b_name: str,
        initial_prompt: str,
    ):
        """Display configuration information."""
        from .helpers import format_model_display

        config_lines = []
        config_lines.append(f"Name: {config.name}")
        config_lines.append(
            f"Models: {format_model_display(config.agent_a_model)} ↔ "
            f"{format_model_display(config.agent_b_model)}"
        )
        config_lines.append(f"Conversations: {config.repetitions}")
        config_lines.append(f"Turns per conversation: {config.max_turns}")

        if config.max_parallel > 1:
            config_lines.append(f"Parallel execution: {config.max_parallel}")

        if initial_prompt:
            if len(initial_prompt) > 50:
                config_lines.append(f"Initial prompt: {initial_prompt[:50]}...")
            else:
                config_lines.append(f"Initial prompt: {initial_prompt}")

        if config.temperature_a is not None or config.temperature_b is not None:
            temp_parts = []
            if config.temperature_a is not None:
                temp_parts.append(f"A: {config.temperature_a}")
            if config.temperature_b is not None:
                temp_parts.append(f"B: {config.temperature_b}")
            config_lines.append(f"Temperature: {', '.join(temp_parts)}")

        if config.convergence_threshold:
            config_lines.append(
                f"Convergence: {config.convergence_threshold} → {config.convergence_action}"
            )

        display.info(
            "\n".join(config_lines), title="◆ Experiment Configuration", use_panel=True
        )
