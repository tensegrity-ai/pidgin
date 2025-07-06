# pidgin/cli/list_experiments.py
"""List command for experiment sessions."""

import rich_click as click
from rich.console import Console
from rich.table import Table

from .constants import NORD_GREEN, NORD_RED, NORD_BLUE, NORD_YELLOW, NORD_CYAN
from ..io.paths import get_experiments_dir
from ..experiments.state_builder import StateBuilder

console = Console()


@click.command(name='list')
@click.option("--all", is_flag=True, help="Show completed experiments too")
def list_experiments(all):
    """List experiment sessions (like screen -list).
    
    Shows active experiment sessions with their status and progress.
    """
    # Build states from JSONL files
    exp_base = get_experiments_dir()
    experiment_states = []
    
    # Find all experiment directories
    for exp_dir in exp_base.glob("exp_*"):
        if exp_dir.is_dir():
            state = StateBuilder.from_experiment_dir(exp_dir)
            if state:
                # Filter based on --all flag
                if all or state.status in ['running', 'created']:
                    experiment_states.append(state)
    
    if not experiment_states:
        if all:
            console.print(f"[{NORD_YELLOW}]No experiments found.[/{NORD_YELLOW}]")
        else:
            console.print(f"[{NORD_YELLOW}]No running experiments.[/{NORD_YELLOW}]")
            console.print(f"[{NORD_CYAN}]Use --all to see completed experiments.[/{NORD_CYAN}]")
        return
    
    # Create table
    table = Table(title="Experiment Sessions")
    table.add_column("ID", style=NORD_CYAN)
    table.add_column("Name", style=NORD_GREEN)
    table.add_column("Status", style=NORD_YELLOW)
    table.add_column("Progress")
    table.add_column("Models")
    table.add_column("Started")
    
    # Sort by started time, most recent first
    experiment_states.sort(key=lambda s: s.started_at or s.created_at, reverse=True)
    
    for state in experiment_states:
        # Format progress
        completed, total = state.progress
        progress = f"{completed}/{total}"
        
        # Format status with color
        status_color = {
            'running': NORD_GREEN,
            'completed': NORD_BLUE,
            'failed': NORD_RED,
            'interrupted': NORD_YELLOW,
            'created': NORD_CYAN
        }.get(state.status, 'white')
        status_display = f"[{status_color}]{state.status}[/{status_color}]"
        
        # Format models from first conversation (they're all the same in an experiment)
        if state.conversations:
            first_conv = next(iter(state.conversations.values()))
            models = f"{first_conv.agent_a_model} ↔ {first_conv.agent_b_model}"
        else:
            models = "? ↔ ?"
        
        # Format time
        time_str = "-"
        if state.started_at:
            time_str = state.started_at.strftime("%Y-%m-%d %H:%M")
        elif state.created_at:
            time_str = state.created_at.strftime("%Y-%m-%d %H:%M")
        
        table.add_row(
            state.experiment_id[:8],  # Show shortened ID
            state.name,
            status_display,
            progress,
            models,
            time_str
        )
    
    console.print(table)
    
    if not all:
        console.print(f"\n[{NORD_CYAN}]Tip: Use 'pidgin attach <id>' to monitor a running experiment[/{NORD_CYAN}]")