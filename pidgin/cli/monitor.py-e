# pidgin/cli/monitor.py
"""System-wide monitor command."""

import asyncio

import rich_click as click
from rich.console import Console

from ..ui.display_utils import DisplayUtils

console = Console()
display = DisplayUtils(console)


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
    from ..monitor import Monitor

    display.info("Starting system monitor...", use_panel=False)
    display.dim("Press Ctrl+C to exit")

    monitor = Monitor()
    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        display.dim("\nMonitor stopped")
