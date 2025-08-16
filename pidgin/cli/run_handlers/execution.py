"""Execution logic for run command."""

import asyncio
from typing import Optional

from ...experiments import ExperimentConfig
from ..config_builder import ConfigBuilder
from ..daemon_launcher import DaemonLauncher


class ExecutionHandler:
    """Handles execution of conversations."""

    def __init__(self, console):
        """Initialize execution handler.

        Args:
            console: Rich console for output
        """
        self.console = console
        self.daemon_launcher = DaemonLauncher(console)
        self.config_builder = ConfigBuilder()

    def run_conversations(
        self,
        config: ExperimentConfig,
        agent_a_name: str,
        agent_b_name: str,
        initial_prompt: str,
        quiet: bool,
        notify: bool,
        display_mode: str,
        output_dir: Optional[str] = None,
    ):
        """Run conversations using the unified execution path.

        Args:
            config: ExperimentConfig with all experiment parameters
            agent_a_name: Agent A display name
            agent_b_name: Agent B display name
            initial_prompt: Initial prompt for display
            quiet: Quiet mode flag
            notify: Send notification when complete
            display_mode: Display mode (chat, tail, quiet)
            output_dir: Output directory (currently unused)
        """
        # Show configuration
        self.config_builder.show_config_info(
            config, agent_a_name, agent_b_name, initial_prompt
        )

        # Launch daemon
        try:
            exp_id = self.daemon_launcher.start_daemon(config)
        except (RuntimeError, OSError):
            # Error already displayed by daemon launcher
            return

        if quiet:
            # Quiet mode: just show commands and exit
            self.daemon_launcher.show_quiet_mode_info(exp_id, config.name)
        else:
            # Non-quiet mode: show live display
            self.daemon_launcher.show_interactive_mode_info()

            # Run display and handle completion
            try:
                asyncio.run(
                    self.daemon_launcher.run_display_and_handle_completion(
                        exp_id,
                        config.name,
                        display_mode,
                        notify,
                        config.repetitions,
                    )
                )
            except KeyboardInterrupt:
                # Display was exited with Ctrl+C, but experiment continues
                # The daemon_launcher already handles showing the appropriate message
                pass
