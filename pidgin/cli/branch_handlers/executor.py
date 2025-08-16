"""Execute branched experiments."""

import asyncio
import json
from typing import Optional

from rich.console import Console

from ...config.models import get_model_config
from ...experiments import ExperimentConfig, ExperimentManager
from ...io.paths import get_experiments_dir
from ...providers.api_key_manager import APIKeyError, APIKeyManager
from ...ui.display_utils import DisplayUtils


class BranchExecutor:
    """Execute branched experiments."""

    def __init__(self, display: DisplayUtils, console: Console):
        self.display = display
        self.console = console

    def validate_config(self, config: ExperimentConfig) -> Optional[str]:
        """Validate configuration.

        Returns:
            Error message if validation fails, None if valid
        """
        errors = config.validate()
        if errors:
            return "Configuration errors:\n\n" + "\n".join(
                f"  • {error}" for error in errors
            )
        return None

    def validate_api_keys(self, config: ExperimentConfig) -> Optional[str]:
        """Validate API keys for required providers.

        Returns:
            Error message if validation fails, None if valid
        """
        providers = set()
        agent_a_config = get_model_config(config.agent_a_model)
        agent_b_config = get_model_config(config.agent_b_model)

        if agent_a_config:
            providers.add(agent_a_config.provider)
        if agent_b_config:
            providers.add(agent_b_config.provider)

        try:
            APIKeyManager.validate_required_providers(list(providers))
            return None
        except APIKeyError as e:
            return str(e)

    def execute(
        self, config: ExperimentConfig, quiet: bool, working_dir: str
    ) -> Optional[str]:
        """Execute the branch experiment.

        Returns:
            Experiment ID if successful, None if failed
        """
        # Validate
        if error := self.validate_config(config):
            self.display.error(error, use_panel=True)
            return None

        if error := self.validate_api_keys(config):
            self.display.error(error, title="Missing API Keys", use_panel=True)
            return None

        # Start experiment
        manager = ExperimentManager(base_dir=get_experiments_dir())

        try:
            exp_id = manager.start_experiment(config, working_dir=working_dir)
            self.console.print(f"\n[#a3be8c]✓ Started branch: {exp_id}[/#a3be8c]")

            if quiet:
                self._show_quiet_mode_info(exp_id, config.name)
            else:
                self._show_interactive_display(exp_id, config.name, config.repetitions)

            return exp_id

        except (RuntimeError, OSError) as e:
            self.display.error(f"Failed to start branch: {e!s}", use_panel=True)
            return None

    def _show_quiet_mode_info(self, exp_id: str, name: str):
        """Show commands for quiet mode."""
        self.console.print(
            "\n[#4c566a]Running in background. Check progress:[/#4c566a]"
        )
        cmd_lines = [
            "pidgin monitor              # Monitor all experiments",
            f"pidgin stop {name}    # Stop by name",
            f"pidgin stop {exp_id[:8]}  # Stop by ID",
        ]
        self.display.info("\n".join(cmd_lines), title="Commands", use_panel=True)

    def _show_interactive_display(self, exp_id: str, name: str, repetitions: int):
        """Show interactive display and handle completion."""
        self.console.print(
            "[#4c566a]Ctrl+C to exit display • experiment continues[/#4c566a]\n"
        )

        from ...experiments.display_runner import run_display

        try:
            asyncio.run(run_display(exp_id, "chat"))
            self._show_completion_info(exp_id, repetitions)
        except KeyboardInterrupt:
            self.console.print()
            self.display.info(
                "Display exited. Branch continues in background.", use_panel=False
            )

    def _show_completion_info(self, exp_id: str, repetitions: int):
        """Show completion information if manifest exists."""
        exp_dir = get_experiments_dir() / exp_id
        manifest_path = exp_dir / "manifest.json"

        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)

            completed = manifest.get("completed_conversations", 0)
            total = manifest.get("total_conversations", repetitions)

            self.display.info(
                f"Branch complete: {completed}/{total} conversations\nOutput: {exp_dir}",
                use_panel=True,
            )
