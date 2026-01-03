"""Setup and validation for run command."""

from typing import Optional, Tuple

from ...experiments import ExperimentConfig
from ...ui.display_utils import DisplayUtils
from ..config_builder import ConfigBuilder
from ..display_manager import DisplayManager
from ..model_selector import ModelSelector


class SetupHandler:
    """Handles setup and validation for run command."""

    def __init__(self, console):
        """Initialize setup handler.

        Args:
            console: Rich console for output
        """
        self.console = console
        self.display = DisplayUtils(console)
        self.display_manager = DisplayManager(console)
        self.model_selector = ModelSelector()
        self.config_builder = ConfigBuilder()

    def validate_display_mode(
        self, quiet: bool, tail: bool, max_parallel: int
    ) -> Optional[Tuple[str, bool, bool]]:
        """Validate and determine display mode.

        Args:
            quiet: Quiet mode flag
            tail: Tail mode flag
            max_parallel: Max parallel conversations

        Returns:
            Tuple of (display_mode, quiet, notify) or None if validation fails
        """
        if not self.display_manager.validate_display_flags(quiet, tail):
            return None

        display_mode, quiet, notify = self.display_manager.determine_display_mode(
            quiet, tail, max_parallel
        )
        return display_mode, quiet, notify

    def handle_meditation_mode(
        self, meditation: bool, agent_a: str, agent_b: str
    ) -> Tuple[str, str]:
        """Handle meditation mode setup.

        Args:
            meditation: Meditation mode flag
            agent_a: Agent A model ID
            agent_b: Agent B model ID

        Returns:
            Tuple of (agent_a, agent_b) possibly modified for meditation
        """
        return self.display_manager.handle_meditation_mode(meditation, agent_a, agent_b)

    def select_models(
        self, agent_a: Optional[str], agent_b: Optional[str]
    ) -> Optional[Tuple[str, str]]:
        """Interactively select models if not provided.

        Args:
            agent_a: Agent A model ID or None
            agent_b: Agent B model ID or None

        Returns:
            Tuple of (agent_a, agent_b) or None if selection cancelled
        """
        if not agent_a:
            try:
                agent_a = self.model_selector.select_model(
                    "Select first agent (Agent A)"
                )
                if not agent_a:
                    return None
            except (KeyboardInterrupt, EOFError) as e:
                self.display_manager.handle_model_selection_error(e, type(e).__name__)
                return None
            except (RuntimeError, ValueError) as e:
                self.display_manager.handle_model_selection_error(e, "Exception")
                return None

        if not agent_b:
            try:
                agent_b = self.model_selector.select_model(
                    "Select second agent (Agent B)"
                )
                if not agent_b:
                    return None
            except (KeyboardInterrupt, EOFError) as e:
                self.display_manager.handle_model_selection_error(e, type(e).__name__)
                return None
            except (RuntimeError, ValueError) as e:
                self.display_manager.handle_model_selection_error(e, "Exception")
                return None

        # Validate models
        try:
            self.model_selector.validate_models(agent_a, agent_b)
        except ValueError as e:
            self.display.error(str(e), use_panel=False)
            return None

        return agent_a, agent_b

    def build_experiment_config(
        self,
        agent_a: str,
        agent_b: str,
        display_mode: str,
        max_parallel: int,
        quiet: bool,
        **kwargs,
    ) -> Optional[Tuple[ExperimentConfig, str, str, str]]:
        """Build experiment configuration.

        Args:
            agent_a: Agent A model ID
            agent_b: Agent B model ID
            display_mode: Display mode
            max_parallel: Max parallel conversations
            quiet: Quiet mode flag
            **kwargs: Additional configuration parameters

        Returns:
            Tuple of (config, agent_a_name, agent_b_name, initial_prompt) or None if error
        """
        # Determine experiment display mode
        experiment_display_mode = (
            self.display_manager.determine_experiment_display_mode(
                display_mode, max_parallel, quiet
            )
        )

        try:
            config, agent_a_name, agent_b_name = self.config_builder.build_config(
                agent_a=agent_a,
                agent_b=agent_b,
                display_mode=experiment_display_mode,
                **kwargs,
            )

            # Extract initial prompt
            initial_prompt = config.custom_prompt or ""

            return config, agent_a_name, agent_b_name, initial_prompt

        except ValueError as e:
            self.display.error(str(e), use_panel=False)
            return None
