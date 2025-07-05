# pidgin/cli/monitor.py
"""System-wide monitor command."""

import asyncio
import rich_click as click
from rich.console import Console

console = Console()


@click.command()
def monitor():
    """System health monitor reading from JSONL files.
    
    Shows a live overview of:
    - Active experiments and their progress
    - System load (concurrent conversations)
    - Convergence warnings
    - Completion estimates
    
    This reads directly from JSONL files to avoid database locks,
    providing a real-time view without interfering with running experiments.
    
    [bold]FEATURES:[/bold]
    • Live updates every 2 seconds
    • No database access (lock-free)
    • Progress tracking and ETAs
    • System load indicators
    
    Press Ctrl+C to exit.
    """
    from ..monitor.simple_monitor import SimpleMonitor
    
    console.print("[#8fbcbb]◆ Starting system monitor...[/#8fbcbb]")
    console.print("[#4c566a]Press Ctrl+C to exit[/#4c566a]\n")
    
    monitor = SimpleMonitor()
    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        console.print("\n[#4c566a]Monitor stopped[/#4c566a]")