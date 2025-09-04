"""Launch and manage experiment daemon."""

import json
from datetime import datetime
from typing import Optional, Set

from rich.console import Console

from ..config.models import get_model_config
from ..experiments import ExperimentConfig, ExperimentManager
from ..io.paths import get_experiments_dir
from ..providers.api_key_manager import APIKeyError, APIKeyManager
from ..ui.display_utils import DisplayUtils

# Import ORIGINAL_CWD from main module
from . import ORIGINAL_CWD
from .constants import NORD_DARK
from .notify import send_notification


class DaemonLauncher:
    """Start and manage experiment daemon."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.display = DisplayUtils(self.console)

    def validate_before_start(self, config: ExperimentConfig) -> None:
        """Validate configuration and API keys before starting daemon.

        Args:
            config: The experiment configuration

        Raises:
            Exception: If validation fails
        """
        from ..io.jsonl_reader import JSONLExperimentReader
        from .name_generator import generate_experiment_name

        jsonl_reader = JSONLExperimentReader(get_experiments_dir())
        experiments = jsonl_reader.list_experiments()
        existing_names = {exp.get("name") for exp in experiments if exp.get("name")}

        # Try up to 10 times to find a unique name
        max_retries = 10
        retry_count = 0
        original_name = config.name

        while config.name in existing_names:
            retry_count += 1
            if retry_count > max_retries:
                self.display.error(
                    f"Failed to generate unique name after {max_retries} attempts",
                    context=f"Original name: '{original_name}'",
                    use_panel=False,
                )
                raise ValueError("Could not generate unique experiment name")

            # Generate new name and update config
            new_name = generate_experiment_name()
            config.name = new_name

            if retry_count == 1:
                # First retry, show that we're generating a new name
                self.display.info(
                    f"Name '{original_name}' already exists, generating new name...",
                    use_panel=False,
                )

        # If we had to generate a new name, show it
        if retry_count > 0:
            self.display.info(
                f"Using generated name: {config.name} (original '{original_name}' was already in use)",
                use_panel=False,
            )

        # Validate configuration
        errors = config.validate()
        if errors:
            error_msg = "Configuration errors:\n\n"
            for error in errors:
                error_msg += f"  • {error}\n"
            self.display.error(error_msg.rstrip(), use_panel=True)
            raise ValueError("Configuration validation failed")

        # Validate API keys before starting daemon
        providers = self._get_required_providers(config)
        try:
            APIKeyManager.validate_required_providers(list(providers))
        except APIKeyError as e:
            # Show friendly error message in the CLI
            self.display.error(str(e), title="Missing API Keys", use_panel=True)
            raise

    def start_daemon(self, config: ExperimentConfig) -> str:
        """Start experiment daemon and return experiment ID.

        Args:
            config: The experiment configuration

        Returns:
            The experiment ID

        Raises:
            Exception: If daemon fails to start
        """
        # Validate before starting
        self.validate_before_start(config)

        # Always run via daemon
        base_dir = get_experiments_dir()
        manager = ExperimentManager(base_dir=base_dir)

        try:
            # Always start via manager (creates daemon + PID file)
            exp_id = manager.start_experiment(config, working_dir=ORIGINAL_CWD)

            # Show start message
            self.console.print(f"\n[#a3be8c]✓ Started: {exp_id}[/#a3be8c]")

            return exp_id

        except (RuntimeError, OSError) as e:
            self.display.error(f"Failed to start experiment: {e!s}", use_panel=True)
            raise

    def show_quiet_mode_info(self, exp_id: str, name: str) -> None:
        """Show commands for quiet mode operation.

        Args:
            exp_id: The experiment ID
            name: The experiment name
        """
        self.console.print(
            "\n[#4c566a]Running in background. Check progress:[/#4c566a]"
        )
        cmd_lines = []
        cmd_lines.append("pidgin monitor              # Monitor all experiments")
        cmd_lines.append(f"pidgin stop {name}    # Stop by name")
        cmd_lines.append(f"pidgin stop {exp_id[:8]}  # Stop by ID")
        # Use relative path with full prefix for better glob matching
        cmd_lines.append(f"tail -f pidgin_output/experiments/{exp_id}*/*.jsonl")
        self.display.info("\n".join(cmd_lines), title="Commands", use_panel=True)

    def show_interactive_mode_info(self) -> None:
        """Show info for interactive mode."""
        self.console.print(
            f"[{NORD_DARK}]Ctrl+C to exit display • experiment continues[/{NORD_DARK}]"
        )
        self.console.print()

    async def run_display_and_handle_completion(
        self,
        exp_id: str,
        name: str,
        display_mode: str,
        notify: bool,
        repetitions: int,
    ) -> None:
        """Run display and handle completion notifications.

        Args:
            exp_id: The experiment ID
            name: The experiment name
            display_mode: The display mode to use
            notify: Whether to send notifications
            repetitions: Total number of repetitions expected
        """
        # Import the display runners
        from ..experiments.display_runner import run_display

        manager = ExperimentManager(base_dir=get_experiments_dir())

        try:
            exp_dir_name = manager.get_experiment_directory(exp_id)
            if not exp_dir_name:
                self.display.error(f"Could not find directory for experiment {exp_id}")
                return

            # Run the display (this will tail JSONL files and show live updates)
            await run_display(exp_dir_name, display_mode)

            # After display exits, show completion info
            self._show_completion_info(exp_dir_name, exp_id, name, notify, repetitions)

        except KeyboardInterrupt:
            # Ctrl+C just exits display, not the experiment
            self.console.print()
            self.display.info(
                "Display exited. Experiment continues running in background.",
                use_panel=False,
            )
            self.console.print("\n[#4c566a]Check progress with:[/#4c566a]")
            self.console.print("  pidgin monitor")
            self.console.print(f"  pidgin stop {name}")

    def _get_required_providers(self, config: ExperimentConfig) -> Set[str]:
        """Get set of required providers from config.

        Args:
            config: The experiment configuration

        Returns:
            Set of provider names
        """
        providers = set()
        agent_a_config = get_model_config(config.agent_a_model)
        agent_b_config = get_model_config(config.agent_b_model)
        if agent_a_config:
            providers.add(agent_a_config.provider)
        if agent_b_config:
            providers.add(agent_b_config.provider)
        return providers  # type: ignore[return-value]

    def _show_completion_info(
        self,
        exp_dir_name: str,
        exp_id: str,
        name: str,
        notify: bool,
        repetitions: int,
    ) -> None:
        """Show completion information after display exits.

        Args:
            exp_dir_name: The experiment directory name
            exp_id: The experiment ID
            name: The experiment name
            notify: Whether to send notifications
            repetitions: Total number of repetitions expected
        """
        exp_dir = get_experiments_dir() / exp_dir_name
        manifest_path = exp_dir / "manifest.json"

        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)

                # Extract statistics from manifest
                completed = manifest.get("completed_conversations", 0)
                failed = manifest.get("failed_conversations", 0)
                total = manifest.get("total_conversations", repetitions)
                status = manifest.get("status", "completed")

                # Calculate duration
                start_time = manifest.get("started_at")
                end_time = manifest.get("completed_at")
                if start_time and end_time:
                    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    duration = (end_dt - start_dt).total_seconds()
                else:
                    duration = 0

                # Display completion info
                self.display.experiment_complete(
                    name=name,
                    experiment_id=exp_id,
                    completed=completed,
                    failed=failed,
                    total=total,
                    duration_seconds=duration,
                    status=status,
                    experiment_dir=str(exp_dir),
                )

                if notify and status == "completed":
                    send_notification(
                        title="Pidgin Experiment Complete",
                        message=(
                            f"Experiment '{name}' has finished "
                            f"({completed}/{total} conversations)"
                        ),
                    )
                else:
                    # Terminal bell notification
                    print("\a", end="", flush=True)
            except (OSError, FileNotFoundError, json.JSONDecodeError):
                # If can't read manifest, just note that display exited
                self.display.info(
                    ("Display exited. Experiment continues running in background."),
                    use_panel=False,
                )
        else:
            self.display.info(
                "Display exited. Experiment continues running in background.",
                use_panel=False,
            )
