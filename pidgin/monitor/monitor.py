"""System monitor that reads from JSONL files and displays errors."""

import asyncio

from rich.console import Console, Group
from rich.live import Live

from ..cli.constants import NORD_CYAN
from ..io.logger import get_logger
from ..io.paths import get_experiments_dir
from .display_builder import DisplayBuilder
from .error_tracker import ErrorTracker
from .experiment_reader import ExperimentReader
from .file_reader import FileReader
from .metrics_calculator import MetricsCalculator

logger = get_logger("monitor")
console = Console()

# Monitor refresh settings
REFRESH_INTERVAL_SECONDS = 1
LIVE_REFRESH_PER_SECOND = 0.5  # How often Rich Live updates the display
ERROR_RETRY_DELAY_SECONDS = 5  # Wait time after errors before retrying


class Monitor:
    """Monitor system state from JSONL files with error tracking."""

    def __init__(self, console_instance=None):
        """Initialize monitor with all components.

        Args:
            console_instance: Optional Rich console instance
        """
        self.exp_base = get_experiments_dir()
        self.running = True
        self.refresh_count = 0
        self.no_output_dir = False
        self.console = console_instance or console

        # Initialize all components
        self.display_builder = DisplayBuilder(self.console, self.exp_base)
        self.error_tracker = ErrorTracker()
        self.experiment_reader = ExperimentReader(self.exp_base)
        self.file_reader = FileReader()
        self.metrics_calculator = MetricsCalculator()

        # Check if experiments directory exists
        if not self.exp_base.exists():
            self.no_output_dir = True

    async def run(self):
        """Run the monitor loop."""
        # Clear screen initially
        console.clear()

        with Live(
            self.build_display(), refresh_per_second=LIVE_REFRESH_PER_SECOND
        ) as live:
            while self.running:
                try:
                    # Check if directory has been created
                    if self.no_output_dir and self.exp_base.exists():
                        self.no_output_dir = False
                        logger.info(f"Experiments directory created: {self.exp_base}")

                    # Update display
                    self.refresh_count += 1
                    self.display_builder.refresh_count = self.refresh_count
                    live.update(self.build_display())
                    await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

                except KeyboardInterrupt:
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"Monitor error: {e}")
                    await asyncio.sleep(ERROR_RETRY_DELAY_SECONDS)

    def build_display(self) -> Group:
        """Build the display as a group of panels.

        Returns:
            Group of Rich panels for display
        """
        # Always build header first
        header = self.display_builder.build_header()

        # If no output directory, show a helpful message
        if self.no_output_dir or not self.exp_base.exists():
            logger.debug(
                f"Showing no experiments message. no_output_dir={self.no_output_dir}, "
                f"exists={self.exp_base.exists()}"
            )
            message_panel = self.display_builder.build_no_experiments_message()
            return Group(header, message_panel)

        # Get current states
        experiments = self.experiment_reader.get_experiment_states()

        # Get recent errors
        errors = self.error_tracker.get_recent_errors(minutes=10)

        # Build sections
        summary_panel = self.display_builder.build_summary_panel(
            experiments, self.metrics_calculator
        )
        errors_panel = self.display_builder.build_errors_panel(
            errors, self.error_tracker
        )
        experiments_panel = self.display_builder.build_experiments_panel(
            experiments, self.metrics_calculator
        )
        conversations_panel = self.display_builder.build_conversations_panel(
            experiments
        )

        # Return a group of panels that will auto-size to their content
        return Group(
            header, summary_panel, errors_panel, experiments_panel, conversations_panel
        )


def main():
    """Main entry point for the monitor CLI."""
    import sys

    # Print startup message
    print(f"[{NORD_CYAN}]◆ Starting system monitor[/{NORD_CYAN}]...")
    print(f"[{NORD_CYAN}]Press Ctrl+C to exit[/{NORD_CYAN}]")

    # Create and run monitor
    monitor = Monitor()

    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        print("\n[{NORD_CYAN}]Monitor stopped.[/{NORD_CYAN}]")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Monitor failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
