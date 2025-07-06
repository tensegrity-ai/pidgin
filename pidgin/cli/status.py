# pidgin/cli/status.py
"""Status command for checking experiment progress."""

import json
import asyncio
from datetime import datetime
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.table import Table

from .constants import NORD_GREEN, NORD_RED, NORD_BLUE, NORD_YELLOW, NORD_CYAN
from .jsonl_reader import JSONLExperimentReader
from ..io.paths import get_experiments_dir

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
    if experiment_id:
        # Show specific experiment - always use JSONL to avoid locks
        jsonl_reader = JSONLExperimentReader(get_experiments_dir())
        exp = jsonl_reader.get_experiment_status(experiment_id)
        
        if not exp:
            # Try partial match
            all_exps = jsonl_reader.list_experiments()
            matches = [e for e in all_exps if e['experiment_id'].startswith(experiment_id)]
            if len(matches) == 1:
                exp = matches[0]
            elif len(matches) > 1:
                console.print(f"[{NORD_RED}]Multiple experiments match '{experiment_id}'[/{NORD_RED}]")
                return
        
        if not exp:
            console.print(f"[{NORD_RED}]No experiment found with ID '{experiment_id}'[/{NORD_RED}]")
            return
        
        # Display experiment details
        # Handle config - might be dict (from JSONL) or string (from DB)
        config = exp.get('config', {})
        if isinstance(config, str):
            config = json.loads(config) if config else {}
        elif config is None:
            config = {}
        
        console.print(f"\n[bold {NORD_BLUE}]◆ Experiment: {exp['name']}[/bold {NORD_BLUE}]")
        console.print(f"  ID: {exp['experiment_id']}")
        console.print(f"  Status: {exp['status']}")
        console.print(f"  Progress: {exp['completed_conversations']}/{exp['total_conversations']}")
        console.print(f"  Models: {config.get('agent_a_model')} ↔ {config.get('agent_b_model')}")
        
        if exp['status'] == 'running':
            # Calculate estimated time
            if exp['completed_conversations'] > 0:
                started = datetime.fromisoformat(exp['started_at'].replace('Z', '+00:00'))
                elapsed = datetime.now(started.tzinfo) - started
                avg_time = elapsed / exp['completed_conversations']
                remaining = (exp['total_conversations'] - exp['completed_conversations']) * avg_time
                console.print(f"  Estimated time remaining: {str(remaining).split('.')[0]}")
        
        if watch and exp['status'] == 'running':
            console.print(f"\n[{NORD_YELLOW}]Watching experiment... Press Ctrl+C to stop[/{NORD_YELLOW}]")
            
            # Watch loop
            try:
                while True:
                    import time
                    time.sleep(5)  # Check every 5 seconds
                    
                    # Refresh experiment data from JSONL
                    jsonl_reader = JSONLExperimentReader(get_experiments_dir())
                    exp = jsonl_reader.get_experiment_status(exp['experiment_id'])
                    
                    if exp['status'] != 'running':
                        console.print(f"\n[{NORD_GREEN}]✓ Experiment completed with status: {exp['status']}[/{NORD_GREEN}]")
                        if notify:
                            # Try desktop notification
                            try:
                                from .notify import notify_experiment_complete
                                notify_experiment_complete(exp['name'], exp['status'])
                            except:
                                # Fallback to terminal bell
                                print('\a', end='', flush=True)
                        break
                    
                    # Update progress
                    console.print(f"\r  Progress: {exp['completed_conversations']}/{exp['total_conversations']}", end='')
                    
            except KeyboardInterrupt:
                console.print(f"\n[{NORD_YELLOW}]Stopped watching[/{NORD_YELLOW}]")
        
    else:
        # Show all running experiments - always use JSONL
        jsonl_reader = JSONLExperimentReader(get_experiments_dir())
        experiments = jsonl_reader.list_experiments(status_filter='running')
        
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
            config = json.loads(exp.get('config', '{}'))
            
            # Format progress with percentage
            total = exp.get('total_conversations', 0)
            completed = exp.get('completed_conversations', 0)
            percentage = (completed / total * 100) if total > 0 else 0
            progress = f"{completed}/{total} ({percentage:.0f}%)"
            
            # Format models
            models = f"{config.get('agent_a_model', '?')} ↔ {config.get('agent_b_model', '?')}"
            
            # Calculate time running
            started = exp.get('started_at', exp.get('created_at', ''))
            if started:
                try:
                    dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                    elapsed = datetime.now(dt.tzinfo) - dt
                    time_str = str(elapsed).split('.')[0]
                except:
                    time_str = "-"
            else:
                time_str = "-"
            
            table.add_row(
                exp['experiment_id'][:8],
                exp.get('name', 'Unnamed'),
                progress,
                models,
                time_str
            )
        
        console.print(table)
        console.print(f"\n[{NORD_CYAN}]Use 'pidgin status <id>' for details[/{NORD_CYAN}]")