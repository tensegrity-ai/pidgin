# pidgin/cli/spec_loader.py
"""YAML spec file loading and validation for experiments."""

from pathlib import Path
from typing import Any, Dict

import yaml
from rich.console import Console

from ..config.models import get_model_config
from ..experiments import ExperimentConfig
from ..ui.display_utils import DisplayUtils
from .constants import DEFAULT_TURNS
from .helpers import validate_model_id
from .name_generator import generate_experiment_name


class SpecLoader:
    """Handle YAML spec file loading and validation."""

    def __init__(self):
        self.console = Console()
        self.display = DisplayUtils(self.console)

    def load_spec(self, spec_file: Path) -> Dict[str, Any]:
        """Load YAML spec file.

        Args:
            spec_file: Path to the YAML spec file

        Returns:
            Loaded specification dictionary

        Raises:
            FileNotFoundError: If spec file doesn't exist
            yaml.YAMLError: If YAML is invalid
            Exception: For other loading errors
        """
        try:
            with open(spec_file) as f:
                spec = yaml.safe_load(f)
            return spec
        except FileNotFoundError:
            self.display.error(f"Spec file not found: {spec_file}")
            raise
        except yaml.YAMLError as e:
            self.display.error(f"Invalid YAML in {spec_file}: {e}")
            raise
        except (PermissionError, OSError) as e:
            self.display.error(f"Error loading spec: {e}")
            raise

    def validate_spec(self, spec: Dict[str, Any]) -> None:
        """Validate spec has required fields.

        Args:
            spec: Specification dictionary to validate

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Check for required model fields
        if "agent_a_model" not in spec or "agent_b_model" not in spec:
            # Also check for shorthand
            if "agent_a" in spec and "agent_b" in spec:
                spec["agent_a_model"] = spec.pop("agent_a")
                spec["agent_b_model"] = spec.pop("agent_b")
            else:
                raise ValueError(
                    "Missing required fields: must specify agent_a_model "
                    "and agent_b_model (or agent_a and agent_b)"
                )

        # Validate models
        try:
            validate_model_id(spec["agent_a_model"])
            validate_model_id(spec["agent_b_model"])
        except ValueError as e:
            raise ValueError(f"Invalid model: {e}")

    def spec_to_config(self, spec: Dict[str, Any]) -> ExperimentConfig:
        """Convert spec dictionary to ExperimentConfig.

        Args:
            spec: Validated specification dictionary

        Returns:
            ExperimentConfig instance
        """
        # Validate models and get IDs
        agent_a_id, _ = validate_model_id(spec["agent_a_model"])
        agent_b_id, _ = validate_model_id(spec["agent_b_model"])

        # Map fields with defaults
        name = spec.get("name", generate_experiment_name())
        repetitions = spec.get("repetitions", 1)
        max_turns = spec.get("max_turns", spec.get("turns", DEFAULT_TURNS))

        # Temperature handling
        temp_a = spec.get("temperature_a", spec.get("temperature"))
        temp_b = spec.get("temperature_b", spec.get("temperature"))

        # Prompt handling
        initial_prompt = spec.get("custom_prompt", spec.get("prompt"))
        dimensions = spec.get("dimensions", spec.get("dimension"))

        # Ensure dimensions is a list if it's a string
        if isinstance(dimensions, str):
            dimensions = [dimensions]

        # Convergence settings
        convergence_threshold = spec.get("convergence_threshold")
        convergence_action = spec.get(
            "convergence_action", "stop" if convergence_threshold else None
        )

        # Awareness settings
        awareness = spec.get("awareness", "basic")
        awareness_a = spec.get("awareness_a")
        awareness_b = spec.get("awareness_b")

        # Other settings
        choose_names = spec.get("choose_names", False)
        max_parallel = spec.get("max_parallel", 1)
        display_mode = spec.get("display_mode", "chat")
        prompt_tag = spec.get("prompt_tag", "[HUMAN]")
        allow_truncation = spec.get("allow_truncation", False)

        return ExperimentConfig(
            name=name,
            agent_a_model=agent_a_id,
            agent_b_model=agent_b_id,
            repetitions=repetitions,
            max_turns=max_turns,
            temperature_a=temp_a,
            temperature_b=temp_b,
            custom_prompt=initial_prompt,
            max_parallel=max_parallel,
            convergence_threshold=convergence_threshold,
            convergence_action=convergence_action,
            awareness=awareness,
            awareness_a=awareness_a,
            awareness_b=awareness_b,
            choose_names=choose_names,
            display_mode=display_mode,
            prompt_tag=prompt_tag,
            allow_truncation=allow_truncation,
        )

    def show_spec_info(self, spec_file: Path, config: ExperimentConfig) -> None:
        """Display information about loaded spec.

        Args:
            spec_file: Path to the spec file
            config: Loaded experiment configuration
        """
        agent_a_config = get_model_config(config.agent_a_model)
        agent_b_config = get_model_config(config.agent_b_model)
        agent_a_name = (
            agent_a_config.display_name if agent_a_config else config.agent_a_model
        )
        agent_b_name = (
            agent_b_config.display_name if agent_b_config else config.agent_b_model
        )

        self.display.info(
            f"Loading experiment from: {spec_file}",
            context=(
                f"Name: {config.name}\n"
                f"Agents: {agent_a_name} ↔ {agent_b_name}\n"
                f"Repetitions: {config.repetitions}"
            ),
        )
