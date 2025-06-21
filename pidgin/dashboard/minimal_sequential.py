"""Enhanced dashboard with turn counter and sparkline."""

import asyncio
from datetime import datetime, timedelta
from typing import List

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.table import Table

from ..core.event_bus import EventBus
from .minimal_state import MinimalStateManager


class MinimalSequentialDashboard:
    """Dashboard showing progress and convergence."""
    
    # Unicode blocks for sparklines
    SPARKS = " ▁▂▃▄▅▆▇█"
    
    def __init__(self, event_bus: EventBus, experiment_id: str):
        self.event_bus = event_bus
        self.experiment_id = experiment_id
        
        self.state_manager = MinimalStateManager(experiment_id)
        self.state_manager.subscribe_to_bus(event_bus)
        
        self.console = Console()
        self.running = True
        self.start_time = datetime.now()
        
    def _make_sparkline(self, values: List[float], width: int = 10) -> str:
        """Create sparkline from values."""
        if not values:
            return "─" * width
            
        # Get last 'width' values
        recent = list(values)[-width:]
        if len(recent) < 2:
            return "─" * width
            
        min_val = min(recent)
        max_val = max(recent)
        
        if max_val == min_val:
            return "─" * width
            
        sparkline = ""
        for v in recent:
            index = int((v - min_val) / (max_val - min_val) * (len(self.SPARKS) - 1))
            sparkline += self.SPARKS[index]
            
        return sparkline.ljust(width)
    
    def _make_panel(self) -> Panel:
        """Create dashboard panel with metrics."""
        state = self.state_manager.state
        elapsed = datetime.now() - self.start_time
        
        # Create a table for better layout
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="cyan")
        table.add_column("Value", style="white")
        
        # Experiment info
        table.add_row("Experiment:", state.experiment_name)
        table.add_row("Progress:", f"{state.completed_conversations}/{state.total_conversations} conversations")
        
        # Current status
        if state.current_conversation > 0:
            table.add_row("Current:", f"Conversation {state.current_conversation}, Turn {state.current_turn}")
        
        table.add_row("", "")  # Spacer
        
        # Convergence with sparkline!
        if state.convergence_history:
            sparkline = self._make_sparkline(list(state.convergence_history))
            table.add_row("Convergence:", f"{sparkline} {state.latest_convergence:.3f}")
        
        table.add_row("", "")  # Spacer
        
        # Debug info
        table.add_row("Events:", f"{state.total_events} total")
        table.add_row("Running:", self._format_duration(elapsed))
        
        # Status indicator
        if state.total_events == 0:
            status = "[yellow]Waiting for events...[/yellow]"
        elif 'MetricsCalculatedEvent' in state.event_types_seen:
            status = "[green]Metrics flowing! ✓[/green]"
        else:
            status = "[yellow]Waiting for metrics...[/yellow]"
        
        return Panel(
            Align.center(table, vertical="middle"),
            title="◆ EXPERIMENT DASHBOARD - PHASE 2",
            subtitle=status,
            border_style="green" if state.total_events > 0 else "yellow"
        )
    
    def _format_duration(self, td: timedelta) -> str:
        """Format duration nicely."""
        total_seconds = int(td.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    
    async def run(self):
        """Run the dashboard."""
        print(f"[DEBUG] Dashboard starting for experiment {self.experiment_id}")
        await asyncio.sleep(1)  # Let events start
        
        with Live(self._make_panel(), console=self.console, refresh_per_second=2) as live:
            while self.running:
                try:
                    live.update(self._make_panel())
                    
                    # Auto-exit when experiment completes
                    state = self.state_manager.state
                    if (state.completed_conversations >= state.total_conversations and 
                        state.total_conversations > 0):
                        await asyncio.sleep(2)  # Show final state
                        self.running = False
                    
                    await asyncio.sleep(0.5)
                    
                except KeyboardInterrupt:
                    print("\n[DEBUG] Dashboard interrupted")
                    break
        
        print(f"[DEBUG] Dashboard ended. Total events seen: {self.state_manager.state.total_events}")
        return {'detached': True, 'stopped': False}