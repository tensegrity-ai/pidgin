# pidgin/cli/list_experiments.py
"""List command for experiment sessions."""

import rich_click as click
from rich.console import Console
from rich.table import Table
from ..ui.display_utils import DisplayUtils

from .constants import NORD_GREEN, NORD_RED, NORD_BLUE, NORD_YELLOW, NORD_CYAN
from ..io.paths import get_experiments_dir
from ..experiments.optimized_state_builder import get_state_builder
from ..constants import ExperimentStatus
from ..ui.display_utils import DisplayUtils

console = Console()
display = DisplayUtils(console)
display = DisplayUtils(console)


@click.command(name='list')
@click.option("--all", is_flag=True, help="Show completed experiments too")
def list_experiments(all):
    """List experiment sessions (like screen -list).
    
    Shows active experiment sessions with their status and progress.
    """
    # Use optimized state builder
    state_builder = get_state_builder()
    exp_base = get_experiments_dir()
    
    # Get experiments with optional status filter
    if all:
        experiment_states = state_builder.list_experiments(exp_base)
    else:
        experiment_states = state_builder.list_experiments(
            exp_base, 
            status_filter=[ExperimentStatus.RUNNING, ExperimentStatus.CREATED]
        )
    
    if not experiment_states:
        if all:
            display.warning("No experiments found.", use_panel=False)
        else:
            display.warning("No running experiments.", use_panel=False)
            display.dim("Use --all to see completed experiments.")
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
        display.dim("\nTip: Use 'pidgin attach <id or name>' to monitor a running experiment")