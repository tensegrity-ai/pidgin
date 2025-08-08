"""Execution logic for run command."""

import asyncio

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
        agent_a_id: str,
        agent_b_id: str,
        agent_a_name: str,
        agent_b_name: str,
        repetitions: int,
        max_turns: int,
        temp_a: float,
        temp_b: float,
        initial_prompt: str,
        dimensions: list,
        name: str,
        max_parallel: int,
        convergence_threshold: float,
        convergence_action: str,
        awareness: str,
        awareness_a: str,
        awareness_b: str,
        choose_names: bool,
        quiet: bool,
        notify: bool,
        display_mode: str,
        first_speaker_id: str,
        output_dir: str,
        prompt_tag: str,
        allow_truncation: bool,
    ):
        """Run conversations using the unified execution path.

        Args:
            agent_a_id: Agent A model ID
            agent_b_id: Agent B model ID
            agent_a_name: Agent A display name
            agent_b_name: Agent B display name
            repetitions: Number of conversations
            max_turns: Max turns per conversation
            temp_a: Temperature for agent A
            temp_b: Temperature for agent B
            initial_prompt: Initial prompt
            dimensions: Conversation dimensions
            name: Experiment name
            max_parallel: Max parallel conversations
            convergence_threshold: Convergence threshold
            convergence_action: Action on convergence
            awareness: Awareness level
            awareness_a: Agent A awareness override
            awareness_b: Agent B awareness override
            choose_names: Let agents choose names
            quiet: Quiet mode
            notify: Send notification
            display_mode: Display mode
            first_speaker_id: First speaker
            output_dir: Output directory
            prompt_tag: Prompt tag
            allow_truncation: Allow message truncation
        """
        # Create experiment configuration
        config = ExperimentConfig(
            name=name,
            agent_a_model=agent_a_id,
            agent_b_model=agent_b_id,
            repetitions=repetitions,
            max_turns=max_turns,
            temperature_a=temp_a,
            temperature_b=temp_b,
            custom_prompt=initial_prompt if initial_prompt != "Hello" else None,
            dimensions=list(dimensions) if dimensions else None,
            max_parallel=max_parallel,
            convergence_threshold=convergence_threshold,
            convergence_action=convergence_action,
            awareness=awareness,
            awareness_a=awareness_a,
            awareness_b=awareness_b,
            choose_names=choose_names,
            first_speaker=first_speaker_id,
            display_mode=display_mode,
            prompt_tag=prompt_tag,
            allow_truncation=allow_truncation,
        )

        # Show configuration
        self.config_builder.show_config_info(config, agent_a_name, agent_b_name, initial_prompt)

        # Launch daemon
        try:
            exp_id = self.daemon_launcher.start_daemon(config)
        except Exception:
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