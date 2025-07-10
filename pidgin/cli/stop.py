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
from ..constants import ExperimentStatus
from ..ui.display_utils import DisplayUtils

console = Console()
display = DisplayUtils(console)

# Import ORIGINAL_CWD from main module
from . import ORIGINAL_CWD


@click.command()
@click.argument('experiment_id', required=False)
@click.option('--all', is_flag=True, help='Stop all running experiments')
def stop(experiment_id, all):
    """Stop a running experiment gracefully.
    
    You can use the experiment ID, shortened ID, or name.
    Use --all to stop all running experiments at once.
    """
    if all:
        # Stop all logic from stop_all command
        display.warning(
            "Stopping ALL experiments",
            context="This will stop ALL running experiments!",
            use_panel=False
        )
        
        # Find all daemon PIDs
        active_dir = Path(ORIGINAL_CWD) / "pidgin_output" / "experiments" / "active"
        daemon_pids = []
        
        if active_dir.exists():
            for pid_file in active_dir.glob("*.pid"):
                try:
                    with open(pid_file) as f:
                        pid = int(f.read().strip())
                        daemon_pids.append((pid, pid_file.stem))
                except (OSError, ValueError):
                    # PID file is inaccessible or contains invalid data
                    pass
        
        display.status(f"Found {len(daemon_pids)} running daemons", style="nord8")
        
        # Kill each daemon
        for pid, exp_id in daemon_pids:
            try:
                os.kill(pid, signal.SIGTERM)
                display.dim(f"  → Stopped {exp_id} (PID: {pid})")
            except ProcessLookupError:
                display.dim(f"  ! {exp_id} already dead (PID: {pid})")
            except Exception as e:
                display.error(f"Failed to stop {exp_id}: {e}", use_panel=False)
        
        # Clean up database
        console.print()  # Add spacing
        display.status("Updating database...", style="nord8")
        
        # Mark all running experiments as failed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            storage = EventStore(
                db_path=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments" / "experiments.duckdb"
            )
            experiments = loop.run_until_complete(storage.list_experiments(status_filter=ExperimentStatus.RUNNING))
            for exp in experiments:
                loop.run_until_complete(storage.update_experiment_status(exp['experiment_id'], ExperimentStatus.FAILED))
                display.success(f"Marked '{exp['name']}' as failed")
            loop.run_until_complete(storage.close())
        finally:
            loop.close()
        
        console.print()  # Add spacing
        display.success("All experiments stopped")
    else:
        if not experiment_id:
            display.error("Either provide an experiment ID or use --all", use_panel=False)
            return
            
        manager = ExperimentManager(
            base_dir=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments"
        )
        
        display.status(f"Stopping experiment {experiment_id}...", style="nord13")
        
        if manager.stop_experiment(experiment_id):
            display.success(f"Stopped experiment {experiment_id}")
        else:
            display.error(
                f"Failed to stop experiment {experiment_id}",
                context="It may not be running",
                use_panel=False
            )