# pidgin/cli/__init__.py
"""Main CLI entry point."""

import os

# Force color output for rich-click
os.environ["FORCE_COLOR"] = "1"
os.environ["CLICOLOR_FORCE"] = "1"

# Store the original working directory before any imports that might change it
# When running with python -m, the working directory may be changed
ORIGINAL_CWD = os.environ.get("PWD", os.getcwd())
# Set it in environment for other modules to use
os.environ["PIDGIN_ORIGINAL_CWD"] = ORIGINAL_CWD

# Configure rich-click BEFORE importing
# NOTE: The following imports violate E402 (module level import not at top)
# This is intentional - we MUST configure rich-click settings before importing
# it as click, otherwise the configuration won't take effect.

import rich_click.rich_click as rc

# Force terminal and color detection
rc.COLOR_SYSTEM = "truecolor"
rc.FORCE_TERMINAL = True

# Configure rich console directly
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

rc.CONSOLE = Console(force_terminal=True, color_system="truecolor")

rc.USE_RICH_MARKUP = True
rc.SHOW_ARGUMENTS = True
rc.GROUP_ARGUMENTS_OPTIONS = True
rc.SHOW_METAVARS_COLUMN = False
rc.APPEND_METAVARS_HELP = True
rc.MAX_WIDTH = 100

# Nord color scheme
rc.STYLE_OPTION = "bold #8fbcbb"  # Nord7 teal
rc.STYLE_ARGUMENT = "bold #88c0d0"  # Nord8 light blue
rc.STYLE_COMMAND = "bold #5e81ac"  # Nord10 blue
rc.STYLE_SWITCH = "#a3be8c"  # Nord14 green
rc.STYLE_METAVAR = "#d8dee9"  # Nord4 light gray
rc.STYLE_USAGE = "bold #8fbcbb"
rc.STYLE_OPTION_DEFAULT = "#4c566a"  # Nord3 dim gray
rc.STYLE_REQUIRED_SHORT = "bold #bf616a"  # Nord11 red
rc.STYLE_REQUIRED_LONG = "bold #bf616a"
rc.STYLE_HELPTEXT_FIRST_LINE = "bold"
rc.STYLE_HELPTEXT = "#d8dee9"  # Nord4 light gray
rc.STYLE_OPTION_HELP = "#d8dee9"  # Nord4 light gray for option descriptions

# Now import as click
import rich_click as click

from ..ui.display_utils import DisplayUtils
from .branch import branch
from .config import config
from .constants import BANNER
from .models import models
from .monitor import monitor
from .run import run
from .stop import stop

console = Console()
display = DisplayUtils(console)


class CustomGroup(click.Group):
    """Custom Click group with enhanced help formatting."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Override help formatting to add panels."""
        # Print the basic description
        console.print(
            "\n[bold #8fbcbb]Usage:[/bold #8fbcbb] pidgin [OPTIONS] COMMAND [ARGS]...\n"
        )
        console.print(
            "[#d8dee9]AI conversation research tool for studying emergent communication patterns.[/#d8dee9]"
        )
        console.print(
            "[#d8dee9]Pidgin enables controlled experiments between AI agents to discover how they[/#d8dee9]"
        )
        console.print(
            "[#d8dee9]develop communication patterns, convergence behaviors, and linguistic adaptations.[/#d8dee9]\n"
        )

        # Calculate max panel width
        terminal_width = console.width
        max_panel_width = min(100, terminal_width - 4)  # Cap at 100 chars, leave margin

        # Quick Start section
        quick_start = Text("pidgin run -a claude -b gpt", style="cyan")
        console.print(
            Panel(
                quick_start,
                title="[bold #a3be8c]Quick Start[/bold #a3be8c]",
                border_style="#4c566a",
                padding=(0, 2),
                width=max_panel_width,
            )
        )

        # Examples panel
        examples_content = """[cyan]From YAML spec:[/cyan]         pidgin run experiment.yaml
[cyan]Single conversation:[/cyan]    pidgin run -a opus -b gpt-4.1 -t 50 -p "Discuss philosophy"
[cyan]Multiple conversations:[/cyan] pidgin run -a claude -b gpt -r 20 --name "test"
[cyan]With custom prompt:[/cyan]     pidgin run -a claude -b gpt -p "Explore philosophy together"
[cyan]Monitor experiments:[/cyan]    pidgin monitor"""

        # Configuration panel
        config_content = """• Configuration files: ~/.config/pidgin/
• Environment variables: ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.
• Output directory: ./pidgin/
• Database: ./pidgin/experiments.duckdb"""

        # Display panels with consistent width
        console.print(
            "\n",
            Panel(
                examples_content,
                title="[bold #88c0d0]Examples[/bold #88c0d0]",
                border_style="#4c566a",
                padding=(1, 2),
                width=max_panel_width,
            ),
        )

        console.print(
            "\n",
            Panel(
                config_content,
                title="[bold #8fbcbb]Configuration[/bold #8fbcbb]",
                border_style="#4c566a",
                padding=(1, 2),
                width=max_panel_width,
            ),
        )

        # Options section
        console.print("\n[bold #5e81ac]Options:[/bold #5e81ac]")
        console.print(
            "  [#a3be8c]--version[/#a3be8c]         Show the version and exit."
        )
        console.print(
            "  [#a3be8c]-h, --help[/#a3be8c]        Show this message and exit."
        )

        # Commands section with panel
        commands_text = """[bold #5e81ac]run[/bold #5e81ac]         Run AI conversations between two agents.
[bold #5e81ac]branch[/bold #5e81ac]      Branch a conversation from any point with parameter changes.
[bold #5e81ac]monitor[/bold #5e81ac]     System health monitor reading from JSONL files.
[bold #5e81ac]stop[/bold #5e81ac]        Stop a running experiment gracefully.
[bold #5e81ac]models[/bold #5e81ac]      List all available AI models.
[bold #5e81ac]config[/bold #5e81ac]      Create configuration file with example settings."""

        console.print(
            "\n",
            Panel(
                commands_text,
                title="[bold #5e81ac]Commands[/bold #5e81ac]",
                border_style="#4c566a",
                padding=(1, 2),
                width=max_panel_width,
            ),
        )

        # Footer hint
        console.print(
            "\n[dim]Use 'pidgin COMMAND --help' for more information about a command.[/dim]\n"
        )


@click.group(cls=CustomGroup, context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option()
def cli() -> None:
    """AI conversation research tool for studying emergent communication patterns.

    Pidgin enables controlled experiments between AI agents to discover how they
    develop communication patterns, convergence behaviors, and linguistic
    adaptations.

    QUICK START: pidgin run -a claude -b gpt

    EXAMPLES:
    From YAML spec:          pidgin run experiment.yaml
    Single conversation:     pidgin run -a opus -b gpt-4.1 -t 50 -p "Discuss philosophy"
    Multiple conversations:  pidgin run -a claude -b gpt -r 20 --name "test"
    Using dimensions:        pidgin run -a claude -b gpt -d peers:philosophy:analytical
    Monitor experiments:     pidgin monitor

    CONFIGURATION:
    • Configuration files: ~/.config/pidgin/
    • Environment variables: ANTHROPIC_API_KEY, OPENAI_API_KEY
    • Output directory: ./pidgin/
    """


# Register commands
cli.add_command(run)
cli.add_command(stop)
cli.add_command(monitor)
cli.add_command(models)
cli.add_command(config)
cli.add_command(branch)


def main() -> None:
    # Check if help is being requested
    import sys

    if "--help" in sys.argv or "-h" in sys.argv or len(sys.argv) == 1:
        console.print(BANNER)

    # Run the CLI
    cli()


if __name__ == "__main__":
    main()
