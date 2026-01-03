"""Main command handler for run command."""

from .execution import ExecutionHandler
from .models import RunConfig
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

    def handle_command(self, config: RunConfig):
        """Handle the run command with all its options.

        Args:
            config: RunConfig containing all command parameters
        """
        # Check if a YAML spec file was provided
        if config.spec_file:
            spec_result = self.spec_handler.process_spec_file(config.spec_file)
            if spec_result:
                config, agent_a_name, agent_b_name, spec_output_dir, spec_notify = (
                    spec_result
                )

                # Run the experiment from spec
                self.execution_handler.run_conversations(
                    config,
                    agent_a_name,
                    agent_b_name,
                    config.conversation.prompt or "",
                    config.display.quiet,
                    config.display.quiet or spec_notify,
                    "quiet" if config.display.quiet else "normal",
                    spec_output_dir or config.execution.output,
                )
                return
            elif config.spec_file.endswith((".yaml", ".yml")):
                # Error already displayed by spec_handler
                return

        # Handle display mode
        display_result = self.setup_handler.validate_display_mode(
            config.display.quiet, config.display.tail, config.execution.max_parallel
        )
        if not display_result:
            return
        display_mode, quiet, notify_flag = display_result

        # Merge notify flags
        notify = config.display.notify or notify_flag

        # Handle meditation mode
        agent_a, agent_b = self.setup_handler.handle_meditation_mode(
            config.conversation.meditation, config.agents.agent_a, config.agents.agent_b
        )

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
            max_parallel=config.execution.max_parallel,
            quiet=quiet,
            repetitions=config.conversation.repetitions,
            max_turns=config.conversation.turns,
            temperature=config.agents.temperature,
            temp_a=config.agents.temp_a,
            temp_b=config.agents.temp_b,
            think=config.agents.think,
            think_a=config.agents.think_a,
            think_b=config.agents.think_b,
            think_budget=config.agents.think_budget,
            prompt=config.conversation.prompt,
            name=config.execution.name,
            convergence_threshold=config.convergence.convergence_threshold,
            convergence_action=config.convergence.convergence_action,
            convergence_profile=config.convergence.convergence_profile,
            awareness=config.agents.awareness,
            awareness_a=config.agents.awareness_a,
            awareness_b=config.agents.awareness_b,
            choose_names=config.conversation.choose_names,
            prompt_tag=config.conversation.prompt_tag,
            allow_truncation=config.execution.allow_truncation,
        )

        if not config_result:
            return

        experiment_config, agent_a_name, agent_b_name, initial_prompt = config_result

        # Run conversations
        self.execution_handler.run_conversations(
            experiment_config,
            agent_a_name,
            agent_b_name,
            initial_prompt,
            quiet,
            notify,
            display_mode,
            config.execution.output,
        )
