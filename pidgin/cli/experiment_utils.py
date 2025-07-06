# pidgin/cli/experiment_utils.py
"""Utility functions for experiment management."""

import time
import json
from pathlib import Path
from typing import Optional

from rich.console import Console

from ..io.paths import get_experiments_dir
from ..experiments.optimized_state_builder import get_state_builder
from .constants import NORD_RED, NORD_YELLOW, NORD_CYAN, NORD_GREEN

console = Console()


async def attach_to_experiment(experiment_id: str, tail: bool = False, exp_dir: Path = None):
    """Attach to a running experiment - simplified version.
    
    Args:
        experiment_id: Experiment ID (can be partial)
        tail: Whether to show event stream (ignored for now)
        exp_dir: Optional pre-resolved experiment directory
        
    Returns:
        True if successfully attached and detached, False if error
    """
    # Find experiment directory if not provided
    if not exp_dir:
        exp_base = get_experiments_dir()
        
        # Handle partial ID match
        matching_dirs = list(exp_base.glob(f"{experiment_id}*"))
        if not matching_dirs:
            console.print(f"[{NORD_RED}]No experiment found matching '{experiment_id}'[/{NORD_RED}]")
            return False
        
        if len(matching_dirs) > 1:
            console.print(f"[{NORD_RED}]Multiple experiments match '{experiment_id}':[/{NORD_RED}]")
            for d in matching_dirs:
                console.print(f"  • {d.name}")
            return False
        
        exp_dir = matching_dirs[0]
    
    # Get experiment state
    state_builder = get_state_builder()
    exp_state = state_builder.get_experiment_state(exp_dir)
    
    if not exp_state:
        console.print(f"[{NORD_RED}]No experiment found[/{NORD_RED}]")
        return False
    
    if exp_state.status not in ['running', 'created']:
        console.print(f"[{NORD_YELLOW}]Experiment is {exp_state.status}[/{NORD_YELLOW}]")
        return False
    
    console.print(f"[bold {NORD_CYAN}]◆ Monitoring: {exp_state.name}[/bold {NORD_CYAN}]")
    console.print(f"[{NORD_YELLOW}][Ctrl+C to stop monitoring][/{NORD_YELLOW}]\n")
    
    # Simple status monitoring using optimized state
    try:
        while True:
            # Clear cache to get fresh data
            state_builder.clear_cache()
            exp_state = state_builder.get_experiment_state(exp_dir)
            
            if exp_state.status not in ['running', 'created']:
                console.print(f"\n[{NORD_GREEN}]Experiment {exp_state.status}[/{NORD_GREEN}]")
                break
            
            # Show status
            completed = exp_state.completed_conversations
            failed = exp_state.failed_conversations
            total = exp_state.total_conversations
            
            console.print(f"Status: {completed}/{total} complete, {failed} failed", end='\r')
            
            # Wait before refresh
            time.sleep(2)
            
    except KeyboardInterrupt:
        console.print(f"\n[{NORD_YELLOW}]Stopped monitoring[/{NORD_YELLOW}]")
        return True
    
    return True