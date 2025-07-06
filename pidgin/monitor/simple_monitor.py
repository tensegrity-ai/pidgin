"""Simple system monitor that reads from JSONL files."""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel

from ..experiments.optimized_state_builder import get_state_builder
from ..io.paths import get_experiments_dir
from ..io.logger import get_logger

logger = get_logger("simple_monitor")
console = Console()


class SimpleMonitor:
    """Monitor system state from JSONL files without database access."""
    
    def __init__(self):
        self.exp_base = get_experiments_dir()
        self.running = True
        self.state_builder = get_state_builder()
        
    async def run(self):
        """Run the monitor loop."""
        with Live(self.build_display(), refresh_per_second=0.5) as live:
            while self.running:
                try:
                    # Check for quit
                    # Note: In a real implementation, we'd handle keyboard input
                    # For now, just update display
                    live.update(self.build_display())
                    await asyncio.sleep(2)  # Update every 2 seconds
                    
                except KeyboardInterrupt:
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"Monitor error: {e}")
                    await asyncio.sleep(5)  # Wait longer on error
    
    def build_display(self) -> Layout:
        """Build the display layout."""
        layout = Layout()
        
        # Get current states
        experiments = self.get_experiment_states()
        
        # Build sections
        header = self.build_header()
        experiments_panel = self.build_experiments_panel(experiments)
        stats_panel = self.build_stats_panel(experiments)
        
        # Arrange layout
        layout.split_column(
            Layout(header, size=3),
            Layout(experiments_panel, size=15),
            Layout(stats_panel)
        )
        
        return layout
    
    def get_experiment_states(self) -> List[Any]:
        """Get all running experiment states efficiently."""
        # Clear cache periodically for fresh data
        self.state_builder.clear_cache()
        
        # Get only running experiments
        return self.state_builder.list_experiments(
            self.exp_base, 
            status_filter=['running']
        )
    
    def build_header(self) -> Panel:
        """Build header panel."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return Panel(
            f"[bold cyan]Pidgin System Monitor[/bold cyan] | {timestamp} | Press Ctrl+C to exit",
            style="cyan"
        )
    
    def build_experiments_panel(self, experiments: List[Any]) -> Panel:
        """Build experiments overview panel."""
        if not experiments:
            return Panel("[yellow]No running experiments[/yellow]", title="Active Experiments")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("ID", style="cyan", width=10)
        table.add_column("Name", style="green", width=30)
        table.add_column("Progress", width=20)
        table.add_column("Current", width=15)
        table.add_column("Rate", width=15)
        table.add_column("Est. Time", width=15)
        
        for exp in experiments:
            # Calculate progress
            completed, total = exp.progress
            progress_pct = (completed / total * 100) if total > 0 else 0
            progress_str = f"{completed}/{total} ({progress_pct:.0f}%)"
            
            # Current conversation
            active_convs = [c for c in exp.conversations.values() if c.status == 'running']
            current_str = f"{len(active_convs)} active" if active_convs else "starting..."
            
            # Calculate rate
            rate_str = "-"
            eta_str = "-"
            if exp.started_at and completed > 0:
                elapsed = datetime.now() - exp.started_at
                rate = completed / elapsed.total_seconds() * 3600  # Per hour
                rate_str = f"{rate:.1f}/hr"
                
                # ETA
                if completed < total:
                    remaining = total - completed
                    eta_seconds = remaining / rate * 3600
                    eta = timedelta(seconds=int(eta_seconds))
                    eta_str = str(eta).split('.')[0]
            
            table.add_row(
                exp.experiment_id[:8],
                exp.name[:30],
                progress_str,
                current_str,
                rate_str,
                eta_str
            )
        
        return Panel(table, title=f"Active Experiments ({len(experiments)})")
    
    def build_stats_panel(self, experiments: List[Any]) -> Panel:
        """Build statistics panel."""
        stats = []
        
        # Total conversations
        total_convs = sum(exp.total_conversations for exp in experiments)
        completed_convs = sum(exp.completed_conversations for exp in experiments)
        failed_convs = sum(exp.failed_conversations for exp in experiments)
        active_convs = sum(exp.active_conversations for exp in experiments)
        
        stats.append(f"[bold]Total Conversations:[/bold] {completed_convs + failed_convs}/{total_convs}")
        stats.append(f"[green]Completed:[/green] {completed_convs}")
        stats.append(f"[red]Failed:[/red] {failed_convs}")
        stats.append(f"[yellow]Active:[/yellow] {active_convs}")
        
        # Convergence stats
        high_convergence_count = 0
        for exp in experiments:
            for conv in exp.conversations.values():
                if conv.last_convergence and conv.last_convergence > 0.7:
                    high_convergence_count += 1
        
        if high_convergence_count > 0:
            stats.append(f"\n[orange1][WARNING] High Convergence:[/orange1] {high_convergence_count} conversations")
        
        # System load estimate (based on active conversations)
        if active_convs > 0:
            load_color = "green" if active_convs < 5 else "yellow" if active_convs < 10 else "red"
            stats.append(f"\n[{load_color}]System Load:[/{load_color}] {active_convs} concurrent conversations")
        
        return Panel("\n".join(stats), title="System Statistics")