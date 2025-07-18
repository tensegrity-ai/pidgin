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
import rich_click as click  # noqa: E402

from ..ui.display_utils import DisplayUtils  # noqa: E402
from .branch import branch  # noqa: E402
from .constants import BANNER  # noqa: E402
from .info import info  # noqa: E402
from .monitor import monitor  # noqa: E402
from .run import run  # noqa: E402
from .stop import stop  # noqa: E402

console = Console()
display = DisplayUtils(console)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option()
def cli():
    """AI conversation research tool for studying emergent communication patterns.

    Pidgin enables controlled experiments between AI agents to discover how they
    develop communication patterns, convergence behaviors, and linguistic
    adaptations.

    [bold]QUICK START:[/bold]
    pidgin run -a claude -b gpt

    [bold]EXAMPLES:[/bold]

    [#4c566a]From YAML spec:[/#4c566a]
        pidgin run experiment.yaml

    [#4c566a]Single conversation:[/#4c566a]
        pidgin run -a opus -b gpt-4.1 -t 50 -p "Discuss philosophy"

    [#4c566a]Multiple conversations (experiment):[/#4c566a]
        pidgin run -a claude -b gpt -r 20 --name "test"

    [#4c566a]Using dimensional prompts:[/#4c566a]
        pidgin run -a claude -b gpt -d peers:philosophy:analytical

    [#4c566a]Monitor experiments:[/#4c566a]
        pidgin monitor

    [bold]CONFIGURATION:[/bold]

    • Configuration files: ~/.pidgin/ or ./.pidgin/
    """


# Register commands
cli.add_command(run)
cli.add_command(stop)
cli.add_command(monitor)
cli.add_command(info)
cli.add_command(branch)


def main():
    """Main entry point."""
    # Check if help is being requested
    import sys

    if "--help" in sys.argv or "-h" in sys.argv or len(sys.argv) == 1:
        console.print(BANNER)

    # Run the CLI
    cli()


if __name__ == "__main__":
    main()
