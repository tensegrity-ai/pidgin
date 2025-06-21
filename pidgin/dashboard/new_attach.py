# pidgin/dashboard/attach.py
"""Dashboard attachment using SharedState."""

import asyncio
from typing import Dict, Any
from rich.console import Console

from ..experiments.shared_state import SharedState
from .dashboard import Dashboard


async def attach_dashboard_to_experiment(experiment_id: str, experiment_name: str) -> Dict[str, Any]:
    """Attach dashboard to running experiment via SharedState.
    
    Args:
        experiment_id: The experiment ID to monitor
        experiment_name: Human-friendly name for display
        
    Returns:
        Dict with result status (detached, completed, etc)
    """
    console = Console()
    
    # Wait a moment for the daemon to create SharedState
    max_attempts = 10
    for attempt in range(max_attempts):
        if SharedState.exists(experiment_id):
            break
        if attempt == 0:
            console.print(f"[yellow]Waiting for experiment to initialize...[/yellow]")
        await asyncio.sleep(0.5)
    
    # Check if experiment exists
    if not SharedState.exists(experiment_id):
        console.print(f"[red]No running experiment found: {experiment_name}[/red]")
        console.print(f"[dim]Experiment ID: {experiment_id}[/dim]")
        return {"error": "not_found"}
    
    # Connect to shared state
    try:
        shared_state = SharedState(experiment_id)
    except Exception as e:
        console.print(f"[red]Failed to connect to experiment: {e}[/red]")
        return {"error": "connection_failed"}
    
    # Create and run dashboard
    dashboard = Dashboard(shared_state, experiment_id, experiment_name)
    
    try:
        result = await dashboard.run()
        return result
    finally:
        shared_state.close()