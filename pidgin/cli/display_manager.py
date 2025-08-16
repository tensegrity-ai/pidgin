"""Manage display modes and meditation mode."""

from typing import Optional, Tuple

from rich.console import Console

from ..ui.display_utils import DisplayUtils
from .constants import NORD_BLUE, NORD_RED


class DisplayManager:
    """Manage display modes and experiment display settings."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.display = DisplayUtils(self.console)

    def validate_display_flags(self, quiet: bool, tail: bool) -> bool:
        """Validate that only one display flag is used.

        Args:
            quiet: Whether quiet mode is enabled
            tail: Whether tail mode is enabled

        Returns:
            True if valid, False if invalid
        """
        mode_count = sum([quiet, tail])
        if mode_count > 1:
            self.console.print(
                f"[{NORD_RED}]Error: Can only use one of --quiet or --tail[/{NORD_RED}]"
            )
            return False
        return True

    def determine_display_mode(
        self, quiet: bool, tail: bool, max_parallel: int = 1
    ) -> Tuple[str, bool, bool]:
        """Determine the display mode based on flags and parallel execution.

        Args:
            quiet: Whether quiet mode is enabled
            tail: Whether tail mode is enabled
            max_parallel: Maximum parallel conversations

        Returns:
            Tuple of (display_mode, updated_quiet, notify)
        """
        notify = False

        if quiet:
            display_mode = "quiet"
            # Quiet mode should run in background and notify
            notify = True
        elif tail:
            display_mode = "tail"  # Show formatted event stream
        else:
            display_mode = "chat"  # Default: show conversation messages

        # Force quiet mode if parallel execution
        if max_parallel > 1 and not quiet:
            quiet = True
            self.display.warning(
                f"Parallel execution (max_parallel={max_parallel}) requires quiet mode",
                use_panel=False,
            )
            display_mode = "quiet"
            notify = True

        return display_mode, quiet, notify

    def determine_experiment_display_mode(
        self, display_mode: str, max_parallel: int, quiet: bool
    ) -> str:
        """Determine the display mode for the experiment configuration.

        Args:
            display_mode: The CLI display mode
            max_parallel: Maximum parallel conversations
            quiet: Whether quiet mode is enabled

        Returns:
            The experiment display mode
        """
        # For parallel execution or quiet mode, don't use interactive displays
        if max_parallel > 1 or quiet:
            experiment_display_mode = "none"
            if display_mode in ["tail", "chat"] and max_parallel > 1:
                self.display.warning(
                    f"--{display_mode} is not supported with parallel execution",
                    use_panel=False,
                )
        else:
            # Non-quiet mode can use any display mode
            experiment_display_mode = display_mode

        return experiment_display_mode

    def handle_meditation_mode(
        self, meditation: bool, agent_a: Optional[str], agent_b: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Handle meditation mode settings.

        Args:
            meditation: Whether meditation mode is enabled
            agent_a: First agent (may be None)
            agent_b: Second agent (may be None)

        Returns:
            Tuple of (agent_a, agent_b) with defaults applied if needed
        """
        if meditation:
            if not agent_a:
                agent_a = "claude"
            if not agent_b:
                agent_b = "silent"
            self.console.print(
                f"\n[{NORD_BLUE}]◆ Meditation mode: {agent_a} → silence[/{NORD_BLUE}]"
            )

        return agent_a, agent_b

    def handle_model_selection_error(
        self, error: Exception, error_type: str = "Exception"
    ) -> None:
        """Handle errors during model selection.

        Args:
            error: The exception that occurred
            error_type: Type of error (KeyboardInterrupt, EOFError, Exception)
        """
        self.console.print()  # Add newline

        if error_type in ["KeyboardInterrupt", "EOFError"]:
            self.display.warning(
                "Model selection cancelled",
                context=(
                    "Use -a and -b flags to specify models.\n"
                    "Example: pidgin run -a claude -b gpt"
                ),
                use_panel=False,
            )
        else:
            self.display.error(
                f"Error during model selection: {error}",
                context=(
                    "Use -a and -b flags to specify models directly.\n"
                    "Example: pidgin run -a claude -b gpt"
                ),
                use_panel=False,
            )
