"""Minimal event-driven dashboard to test the connection."""

import asyncio
from datetime import datetime, timedelta

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.align import Align
from rich.text import Text

from ..core.event_bus import EventBus
from .minimal_state import MinimalStateManager


class MinimalSequentialDashboard:
    """Minimal dashboard that just shows events are flowing."""
    
    def __init__(self, event_bus: EventBus, experiment_id: str):
        self.event_bus = event_bus
        self.experiment_id = experiment_id
        
        # Create state manager and subscribe
        self.state_manager = MinimalStateManager(experiment_id)
        self.state_manager.subscribe_to_bus(event_bus)
        
        self.console = Console()
        self.running = True
        self.start_time = datetime.now()
        
    def _make_panel(self) -> Panel:
        """Create a simple panel showing current state."""
        state = self.state_manager.state
        elapsed = datetime.now() - self.start_time
        
        # Build content
        lines = [
            f"Experiment: {state.experiment_name}",
            f"Total Conversations: {state.total_conversations}",
            f"",
            f"Events Received: {state.total_events}",
            f"Dashboard Running: {self._format_duration(elapsed)}",
            f"",
            "Event Types Seen:"
        ]
        
        # Show event types
        for event_type, count in sorted(state.event_types_seen.items()):
            lines.append(f"  {event_type}: {count}")
        
        # If no events yet, show loading message
        if state.total_events == 0:
            lines.append("")
            lines.append("[yellow]Waiting for events to start flowing...[/yellow]")
            lines.append("[dim]If this persists, EventBus may not be connected[/dim]")
        
        content = "\n".join(lines)
        
        return Panel(
            content,
            title="◆ MINIMAL EVENT DASHBOARD",
            border_style="green" if state.total_events > 0 else "yellow"
        )
    
    def _format_duration(self, td: timedelta) -> str:
        """Format duration nicely."""
        total_seconds = int(td.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    
    async def run(self):
        """Run the minimal dashboard."""
        print(f"[DEBUG] Dashboard starting for experiment {self.experiment_id}")
        
        # Give events a moment to start
        await asyncio.sleep(1)
        
        with Live(self._make_panel(), console=self.console, refresh_per_second=2) as live:
            while self.running:
                try:
                    # Update display
                    live.update(self._make_panel())
                    
                    # Exit after 60 seconds for testing
                    if (datetime.now() - self.start_time).total_seconds() > 60:
                        self.running = False
                    
                    await asyncio.sleep(0.5)
                    
                except KeyboardInterrupt:
                    print("\n[DEBUG] Dashboard interrupted")
                    break
        
        print(f"[DEBUG] Dashboard ended. Total events seen: {self.state_manager.state.total_events}")
        return {'detached': True, 'stopped': False}