# pidgin/cli/__init__.py
"""Main CLI entry point."""

import os
import click
from rich.console import Console

from .constants import BANNER
from .chat import chat, models
from .experiment import experiment
from .tools import transcribe, report, compare

console = Console()

# Store the original working directory before any imports change it
ORIGINAL_CWD = os.getcwd()

@click.group()
@click.version_option()
def cli():
    """Pidgin - AI conversation orchestrator.
    
    Start AI-to-AI conversations, run experiments, and analyze emergent behaviors.
    """
    pass

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
