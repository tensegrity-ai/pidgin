# pidgin/cli/monitor.py
"""System-wide monitor command."""

import asyncio
import rich_click as click
from rich.console import Console

console = Console()


@click.command()
def monitor():
    """System-wide monitor for experiments and API usage.
    
    Shows a real-time overview of:
    - API usage and rate limits for all providers
    - Active experiments with live metrics
    - System statistics and health
    - Estimated costs
    
    This gives you a bird's eye view of your Pidgin system,
    helping you manage rate limits and track experiment progress.
    
    [bold]FEATURES:[/bold]
    • Live updates from database
    • Rate limit warnings with visual bars
    • Convergence alerts
    • Cost tracking (coming soon)
    
    Press 'q' to quit, 'r' to refresh, 'e' to export stats.
    """
    from ..monitor.system_monitor import SystemMonitor
    
    console.print("[#8fbcbb]◆ Starting system monitor...[/#8fbcbb]")
    console.print("[#4c566a]Press 'q' to exit[/#4c566a]\n")
    
    monitor = SystemMonitor()
    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        console.print("\n[#4c566a]Monitor stopped[/#4c566a]")