# pidgin/cli/__init__.py
"""Main CLI entry point."""

import os

# Force color output for rich-click
os.environ['FORCE_COLOR'] = '1'
os.environ['CLICOLOR_FORCE'] = '1'

# Store the original working directory before any imports that might change it
# When running with python -m, the working directory may be changed
ORIGINAL_CWD = os.environ.get('PWD', os.getcwd())

# Configure rich-click BEFORE importing
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
import rich_click as click

from .constants import BANNER
from .chat import chat, models
from .experiment import experiment
from .tools import transcribe, report, compare

console = Console()

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option()
def cli():
    """AI conversation research tool for studying emergent communication patterns.

    Pidgin enables controlled experiments between AI agents to discover how they
    develop communication patterns, convergence behaviors, and linguistic adaptations.

    [bold]QUICK START:[/bold]
    pidgin chat -a claude -b gpt -t 20

    [bold]EXAMPLES:[/bold]

    [#4c566a]Basic conversation with custom prompt:[/#4c566a]
        pidgin chat -a opus -b gpt-4.1 -t 50 -p "Discuss philosophy"

    [#4c566a]Using dimensional prompts:[/#4c566a]
        pidgin chat -a claude -b gpt -d peers:philosophy:analytical

    [#4c566a]Let agents choose names:[/#4c566a]
        pidgin chat -a claude -b gpt --choose-names

    [#4c566a]High convergence monitoring:[/#4c566a]
        pidgin chat -a claude -b gpt -t 100 --convergence-threshold 0.8

    [bold]CONFIGURATION:[/bold]

    • Configuration files: ~/.pidgin/ or ./.pidgin/
    • Create templates: pidgin init
    """
    pass


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
def init():
    """Initialize configuration directory with template files.

    Creates a .pidgin/ directory in your current folder with template
    configuration files for:

    • Custom dimensions (planned)

    After running this command, edit the YAML files to add your own content.
    """
    from pathlib import Path
    from datetime import datetime
    
    config_dir = Path.cwd() / ".pidgin"
    created_files = []
    
    # Create directory
    if not config_dir.exists():
        config_dir.mkdir(parents=True)
        console.print(f"Created directory: {config_dir}")
    

    # Dimensions template
    dim_path = config_dir / "dimensions.yaml"
    if not dim_path.exists():
        dim_content = f"""# Pidgin Custom Dimensions
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#
# Define custom dimensions for prompt generation.
# (This feature is planned for future releases)
#
# For now, use the built-in dimensions:
#   Context: peers, teaching, debate, interview, collaboration, neutral
#   Topic: philosophy, language, science, creativity, meta
#   Mode: analytical, intuitive, exploratory, focused

dimensions:
  # Future feature - custom dimensions will go here
"""
        with open(dim_path, "w") as f:
            f.write(dim_content)
        created_files.append(dim_path)
    
    # Report results
    if created_files:
        console.print("\n[bold #a3be8c]✓ Configuration templates created:[/bold #a3be8c]")
        for file in created_files:
            console.print(f"  • {file.relative_to(Path.cwd())}")
        console.print("\n[#4c566a]Edit these files to add your own content.[/#4c566a]")
    else:
        console.print("[#ebcb8b]All configuration files already exist.[/#ebcb8b]")
        console.print(f"[#4c566a]Check {config_dir.relative_to(Path.cwd())}/[/#4c566a]")


# Register commands
cli.add_command(chat)
cli.add_command(models)
cli.add_command(experiment)
cli.add_command(transcribe)
cli.add_command(report)
cli.add_command(compare)

def main():
    """Main entry point."""
    # Only show banner if not in quiet mode
    if not os.environ.get('PIDGIN_QUIET'):
        console.print(BANNER)
    
    # Run the CLI
    cli()

if __name__ == "__main__":
    main()
