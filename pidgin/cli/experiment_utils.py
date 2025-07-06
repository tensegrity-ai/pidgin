# pidgin/cli/experiment_utils.py
"""Utility functions for experiment management."""

import time
import json
from pathlib import Path
from typing import Optional

from rich.console import Console

from ..io.paths import get_experiments_dir
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
    
    # Read metadata
    metadata_path = exp_dir / 'metadata.json'
    if not metadata_path.exists():
        console.print(f"[{NORD_RED}]No metadata found for experiment[/{NORD_RED}]")
        return False
        
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    if metadata.get('status') not in ['running', 'created']:
        console.print(f"[{NORD_YELLOW}]Experiment is {metadata.get('status', 'unknown')}[/{NORD_YELLOW}]")
        return False
    
    console.print(f"[bold {NORD_CYAN}]◆ Monitoring: {metadata.get('name', experiment_id)}[/bold {NORD_CYAN}]")
    console.print(f"[{NORD_YELLOW}][Ctrl+C to stop monitoring][/{NORD_YELLOW}]\n")
    
    # Simple status monitoring
    try:
        while True:
            # Reload metadata
            with open(metadata_path) as f:
                metadata = json.load(f)
            
            status = metadata.get('status', 'unknown')
            if status not in ['running', 'created']:
                console.print(f"\n[{NORD_GREEN}]Experiment {status}[/{NORD_GREEN}]")
                break
            
            # Show simple status
            completed = metadata.get('completed_conversations', 0)
            failed = metadata.get('failed_conversations', 0) 
            total = metadata.get('total_conversations', 0)
            
            console.print(f"Status: {completed}/{total} complete, {failed} failed", end='\r')
            
            # Wait before refresh
            time.sleep(2)
            
    except KeyboardInterrupt:
        console.print(f"\n[{NORD_YELLOW}]Stopped monitoring[/{NORD_YELLOW}]")
        return True
    
    return True