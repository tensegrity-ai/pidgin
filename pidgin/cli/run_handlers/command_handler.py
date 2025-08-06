"""Main command handler for run command."""

from typing import Optional

from .execution import ExecutionHandler
from .setup import SetupHandler
from .spec_handler import SpecHandler


class CommandHandler:
    """Handles the main run command logic."""

    def __init__(self, console):
        """Initialize command handler.

        Args:
            console: Rich console for output
        """
        self.console = console
        self.spec_handler = SpecHandler(console)
        self.setup_handler = SetupHandler(console)
        self.execution_handler = ExecutionHandler(console)

    def handle_command(
        self,
        spec_file: Optional[str],
        agent_a: Optional[str],
        agent_b: Optional[str],
        prompt: Optional[str],
        turns: int,
        repetitions: int,
        temperature: Optional[float],
        temp_a: Optional[float],
        temp_b: Optional[float],
        output: Optional[str],
        dimension: tuple,
        convergence_threshold: Optional[float],
        convergence_action: Optional[str],
        convergence_profile: str,
        first_speaker: str,
        choose_names: bool,
        awareness: str,
        awareness_a: Optional[str],
        awareness_b: Optional[str],
        show_system_prompts: bool,
        meditation: bool,
        quiet: bool,
        tail: bool,
        notify: bool,
        name: Optional[str],
        max_parallel: int,
        prompt_tag: str,
        allow_truncation: bool,
    ):
        """Handle the run command with all its options.

        Args:
            All command line arguments from the click command
        """
        # Check if a YAML spec file was provided
        if spec_file:
            spec_result = self.spec_handler.process_spec_file(spec_file)
            if spec_result:
                config, agent_a_name, agent_b_name, spec_output_dir, spec_notify = spec_result
                
                # Run the experiment from spec
                self.execution_handler.run_conversations(
                    config.agent_a_model,
                    config.agent_b_model,
                    agent_a_name,
                    agent_b_name,
                    config.repetitions,
                    config.max_turns,
                    config.temperature_a,
                    config.temperature_b,
                    config.custom_prompt or "Hello",
                    config.dimensions,
                    config.name,
                    config.max_parallel,
                    config.convergence_threshold,
                    config.convergence_action,
                    config.awareness,
                    config.awareness_a,
                    config.awareness_b,
                    config.choose_names,
                    config.display_mode == "quiet",
                    config.display_mode == "quiet" or spec_notify,
                    config.display_mode,
                    config.first_speaker,
                    spec_output_dir or output,
                    config.prompt_tag,
                    config.allow_truncation,
                )
                return
            elif spec_file.endswith((".yaml", ".yml")):
                # Error already displayed by spec_handler
                return

        # Handle display mode
        display_result = self.setup_handler.validate_display_mode(quiet, tail, max_parallel)
        if not display_result:
            return
        display_mode, quiet, notify_flag = display_result

        # Merge notify flags
        notify = notify or notify_flag

        # Handle meditation mode
        agent_a, agent_b = self.setup_handler.handle_meditation_mode(meditation, agent_a, agent_b)

        # Interactive model selection if needed
        models = self.setup_handler.select_models(agent_a, agent_b)
        if not models:
            return
        agent_a, agent_b = models

        # Build configuration
        config_result = self.setup_handler.build_experiment_config(
            agent_a=agent_a,
            agent_b=agent_b,
            display_mode=display_mode,
            max_parallel=max_parallel,
            quiet=quiet,
            repetitions=repetitions,
            max_turns=turns,
            temperature=temperature,
            temp_a=temp_a,
            temp_b=temp_b,
            prompt=prompt,
            dimensions=list(dimension) if dimension else None,
            name=name,
            convergence_threshold=convergence_threshold,
            convergence_action=convergence_action,
            convergence_profile=convergence_profile,
            awareness=awareness,
            awareness_a=awareness_a,
            awareness_b=awareness_b,
            choose_names=choose_names,
            first_speaker=first_speaker,
            prompt_tag=prompt_tag,
            allow_truncation=allow_truncation,
        )
        
        if not config_result:
            return
        
        config, agent_a_name, agent_b_name, initial_prompt = config_result

        # Run conversations
        self.execution_handler.run_conversations(
            config.agent_a_model,
            config.agent_b_model,
            agent_a_name,
            agent_b_name,
            config.repetitions,
            config.max_turns,
            config.temperature_a,
            config.temperature_b,
            initial_prompt,
            config.dimensions,
            config.name,
            config.max_parallel,
            config.convergence_threshold,
            config.convergence_action,
            config.awareness,
            config.awareness_a,
            config.awareness_b,
            config.choose_names,
            quiet,
            notify,
            display_mode,
            config.first_speaker,
            output,
            config.prompt_tag,
            config.allow_truncation,
        )