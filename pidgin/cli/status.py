# pidgin/cli/status.py
"""Status command for checking experiment progress."""

import json
import asyncio
import time
from datetime import datetime
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.table import Table

from .constants import NORD_GREEN, NORD_RED, NORD_BLUE, NORD_YELLOW, NORD_CYAN
from ..io.paths import get_experiments_dir
from ..experiments.optimized_state_builder import get_state_builder
from ..experiments.manifest import ManifestManager

console = Console()


@click.command()
@click.argument('experiment_id', required=False)
@click.option('--watch', '-w', is_flag=True, help='Watch experiment until completion')
@click.option('--notify', '-n', is_flag=True, help='Terminal bell when complete')
def status(experiment_id, watch, notify):
    """Check status of an experiment.
    
    Shows detailed status of a specific experiment or all running experiments.
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Check all running experiments:[/#4c566a]
        pidgin status
    
    [#4c566a]Check specific experiment:[/#4c566a]
        pidgin status abc123
    
    [#4c566a]Watch experiment until completion:[/#4c566a]
        pidgin status abc123 --watch --notify
    """
    state_builder = get_state_builder()
    exp_base = get_experiments_dir()
    
    if experiment_id:
        # Show specific experiment
        exp_state = None
        exp_dir = None
        
        # Find matching experiment directory
        matching_dirs = list(exp_base.glob(f"*{experiment_id}*"))
        
        if len(matching_dirs) == 1:
            exp_dir = matching_dirs[0]
            exp_state = state_builder.get_experiment_state(exp_dir)
        elif len(matching_dirs) > 1:
            console.print(f"[{NORD_RED}]Multiple experiments match '{experiment_id}':[/{NORD_RED}]")
            for d in matching_dirs:
                console.print(f"  • {d.name}")
            return
        
        if not exp_state:
            console.print(f"[{NORD_RED}]No experiment found with ID '{experiment_id}'[/{NORD_RED}]")
            return
        
        # Display experiment details
        console.print(f"\n[bold {NORD_BLUE}]◆ Experiment: {exp_state.name}[/bold {NORD_BLUE}]")
        console.print(f"  ID: {exp_state.experiment_id}")
        console.print(f"  Status: {exp_state.status}")
        console.print(f"  Progress: {exp_state.completed_conversations + exp_state.failed_conversations}/{exp_state.total_conversations}")
        
        # Get models from first conversation
        if exp_state.conversations:
            first_conv = next(iter(exp_state.conversations.values()))
            console.print(f"  Models: {first_conv.agent_a_model} ↔ {first_conv.agent_b_model}")
        
        if exp_state.status == 'running' and exp_state.started_at:
            # Calculate estimated time
            completed = exp_state.completed_conversations + exp_state.failed_conversations
            if completed > 0:
                elapsed = datetime.now(exp_state.started_at.tzinfo) - exp_state.started_at
                avg_time = elapsed / completed
                remaining = (exp_state.total_conversations - completed) * avg_time
                console.print(f"  Estimated time remaining: {str(remaining).split('.')[0]}")
        
        if watch and exp_state.status in ['running', 'created']:
            console.print(f"\n[{NORD_YELLOW}]Watching experiment... Press Ctrl+C to stop[/{NORD_YELLOW}]")
            
            # Watch loop
            try:
                while True:
                    time.sleep(5)  # Check every 5 seconds
                    
                    # Refresh experiment state
                    state_builder.clear_cache()  # Force refresh
                    exp_state = state_builder.get_experiment_state(exp_dir)
                    
                    if exp_state.status not in ['running', 'created']:
                        console.print(f"\n[{NORD_GREEN}]✓ Experiment completed with status: {exp_state.status}[/{NORD_GREEN}]")
                        if notify:
                            # Try desktop notification
                            try:
                                from .notify import notify_experiment_complete
                                notify_experiment_complete(exp_state.name, exp_state.status)
                            except:
                                # Fallback to terminal bell
                                print('\a', end='', flush=True)
                        break
                    
                    # Update progress
                    completed = exp_state.completed_conversations + exp_state.failed_conversations
                    console.print(f"\r  Progress: {completed}/{exp_state.total_conversations}", end='')
                    
            except KeyboardInterrupt:
                console.print(f"\n[{NORD_YELLOW}]Stopped watching[/{NORD_YELLOW}]")
        
    else:
        # Show all running experiments
        experiments = state_builder.list_experiments(exp_base, status_filter=['running'])
        
        if not experiments:
            console.print(f"[{NORD_YELLOW}]No running experiments.[/{NORD_YELLOW}]")
            console.print(f"[{NORD_CYAN}]Use 'pidgin list --all' to see all experiments.[/{NORD_CYAN}]")
            return
        
        # Create summary table
        table = Table(title="Running Experiments")
        table.add_column("ID", style=NORD_CYAN)
        table.add_column("Name", style=NORD_GREEN)
        table.add_column("Progress")
        table.add_column("Models")
        table.add_column("Time Running")
        
        for exp in experiments:
            # Format progress with percentage
            total = exp.total_conversations
            completed = exp.completed_conversations + exp.failed_conversations
            percentage = (completed / total * 100) if total > 0 else 0
            progress = f"{completed}/{total} ({percentage:.0f}%)"
            
            # Format models
            models = "? ↔ ?"
            if exp.conversations:
                first_conv = next(iter(exp.conversations.values()))
                models = f"{first_conv.agent_a_model} ↔ {first_conv.agent_b_model}"
            
            # Calculate time running
            time_str = "-"
            if exp.started_at:
                elapsed = datetime.now(exp.started_at.tzinfo) - exp.started_at
                time_str = str(elapsed).split('.')[0]
            
            table.add_row(
                exp.experiment_id[:8],
                exp.name,
                progress,
                models,
                time_str
            )
        
        console.print(table)
        console.print(f"\n[{NORD_CYAN}]Use 'pidgin status <id>' for details[/{NORD_CYAN}]")