# pidgin/cli/attach.py
"""Attach command for monitoring running experiments."""

import asyncio

import rich_click as click
from rich.console import Console

from .experiment_utils import attach_to_experiment

console = Console()


@click.command()
@click.argument('experiment_id')
@click.option('--tail', is_flag=True, help='Show event stream (like tail -f)')
def attach(experiment_id, tail):
    """Attach to a running experiment (like screen -r).
    
    Shows live progress of a running experiment. Ctrl+C to detach.
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Attach with progress bar (default):[/#4c566a]
        pidgin attach exp_abc123
    
    [#4c566a]Attach with event stream:[/#4c566a]
        pidgin attach exp_abc123 --tail
    """
    # Run the async attach function
    try:
        asyncio.run(attach_to_experiment(experiment_id, tail))
    except KeyboardInterrupt:
        # Already handled in attach_to_experiment
        pass