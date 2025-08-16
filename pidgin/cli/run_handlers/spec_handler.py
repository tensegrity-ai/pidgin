"""Handle YAML spec file loading and processing."""

from typing import Optional, Tuple

import yaml

from ...config.models import get_model_config
from ...experiments import ExperimentConfig
from ...ui.display_utils import DisplayUtils
from ..spec_loader import SpecLoader


class SpecHandler:
    """Handles YAML spec file loading and conversion."""

    def __init__(self, console):
        """Initialize spec handler.

        Args:
            console: Rich console for output
        """
        self.spec_loader = SpecLoader()
        self.display = DisplayUtils(console)

    def process_spec_file(
        self, spec_file: str
    ) -> Optional[Tuple[ExperimentConfig, str, str, Optional[str], bool]]:
        """Process a YAML spec file.

        Args:
            spec_file: Path to YAML spec file

        Returns:
            Tuple of (config, agent_a_name, agent_b_name, output_dir, notify) or None if error
        """
        if not spec_file.endswith((".yaml", ".yml")):
            return None

        try:
            # Load and validate spec
            spec = self.spec_loader.load_spec(spec_file)
            self.spec_loader.validate_spec(spec)

            # Convert to config
            config = self.spec_loader.spec_to_config(spec)

            # Show spec info
            self.spec_loader.show_spec_info(spec_file, config)

            # Get model display names
            agent_a_config = get_model_config(config.agent_a_model)
            agent_b_config = get_model_config(config.agent_b_model)
            agent_a_name = (
                agent_a_config.display_name if agent_a_config else config.agent_a_model
            )
            agent_b_name = (
                agent_b_config.display_name if agent_b_config else config.agent_b_model
            )

            # Extract additional fields not in ExperimentConfig
            output_dir = spec.get("output")
            notify = spec.get("notify", False)

            return config, agent_a_name, agent_b_name, output_dir, notify

        except (FileNotFoundError, yaml.YAMLError, ValueError):
            # Errors are already displayed by spec_loader
            return None
        except Exception as e:
            self.display.error(f"Unexpected error: {e}")
            return None
