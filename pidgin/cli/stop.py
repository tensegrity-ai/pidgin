# pidgin/cli/stop.py
"""Stop command for terminating experiments."""

import os
import signal
import asyncio
from pathlib import Path

import rich_click as click
from rich.console import Console

from .constants import NORD_GREEN, NORD_RED, NORD_YELLOW, NORD_CYAN
from ..database.event_store import EventStore
from ..experiments import ExperimentManager

console = Console()

# Import ORIGINAL_CWD from main module
from . import ORIGINAL_CWD


@click.command()
@click.argument('experiment_id', required=False)
@click.option('--all', is_flag=True, help='Stop all running experiments')
def stop(experiment_id, all):
    """Stop a running experiment gracefully.
    
    Use --all to stop all running experiments at once.
    """
    if all:
        # Stop all logic from stop_all command
        console.print(f"[bold {NORD_RED}]WARNING: Stopping ALL experiments[/bold {NORD_RED}]")
        console.print(f"[{NORD_YELLOW}]This will stop ALL running experiments![/{NORD_YELLOW}]\n")
        
        # Find all daemon PIDs
        active_dir = Path(ORIGINAL_CWD) / "pidgin_output" / "experiments" / "active"
        daemon_pids = []
        
        if active_dir.exists():
            for pid_file in active_dir.glob("*.pid"):
                try:
                    with open(pid_file) as f:
                        pid = int(f.read().strip())
                        daemon_pids.append((pid, pid_file.stem))
                except:
                    pass
        
        console.print(f"[{NORD_CYAN}]Found {len(daemon_pids)} running daemons[/{NORD_CYAN}]")
        
        # Kill each daemon
        for pid, exp_id in daemon_pids:
            try:
                os.kill(pid, signal.SIGTERM)
                console.print(f"[{NORD_YELLOW}]  → Stopped {exp_id} (PID: {pid})[/{NORD_YELLOW}]")
            except ProcessLookupError:
                console.print(f"[{NORD_YELLOW}]  ! {exp_id} already dead (PID: {pid})[/{NORD_YELLOW}]")
            except Exception as e:
                console.print(f"[{NORD_RED}]  [FAIL] Failed to stop {exp_id}: {e}[/{NORD_RED}]")
        
        # Clean up database
        console.print(f"\n[{NORD_CYAN}]Updating database...[/{NORD_CYAN}]")
        
        # Mark all running experiments as failed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            storage = EventStore(
                db_path=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments" / "experiments.duckdb"
            )
            experiments = loop.run_until_complete(storage.list_experiments(status_filter='running'))
            for exp in experiments:
                loop.run_until_complete(storage.update_experiment_status(exp['experiment_id'], 'failed'))
                console.print(f"[{NORD_GREEN}]  [OK] Marked '{exp['name']}' as failed[/{NORD_GREEN}]")
            loop.run_until_complete(storage.close())
        finally:
            loop.close()
        
        console.print(f"\n[bold {NORD_GREEN}][OK] All experiments stopped[/bold {NORD_GREEN}]")
    else:
        if not experiment_id:
            console.print(f"[{NORD_RED}]Error: Either provide an experiment ID or use --all[/{NORD_RED}]")
            return
            
        manager = ExperimentManager(
            base_dir=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments"
        )
        
        console.print(f"[{NORD_YELLOW}]→ Stopping experiment {experiment_id}...[/{NORD_YELLOW}]")
        
        if manager.stop_experiment(experiment_id):
            console.print(f"[{NORD_GREEN}][OK] Stopped experiment {experiment_id}[/{NORD_GREEN}]")
        else:
            console.print(f"[{NORD_RED}][FAIL] Failed to stop experiment {experiment_id}[/{NORD_RED}]")
            console.print(f"[{NORD_YELLOW}]  (It may not be running)[/{NORD_YELLOW}]")