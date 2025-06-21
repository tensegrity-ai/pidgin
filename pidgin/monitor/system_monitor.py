# pidgin/monitor/system_monitor.py
"""System-wide monitor for experiments and API usage."""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.progress import Progress, BarColumn, TextColumn

from ..experiments.shared_state import SharedState
from ..providers.token_tracker import get_token_tracker
from ..experiments.storage import ExperimentStore


class SystemMonitor:
    """Monitor all experiments and API usage."""
    
    # Nord colors
    COLORS = {
        'bg': '#2e3440',
        'dim': '#4c566a', 
        'text': '#d8dee9',
        'bright': '#eceff4',
        'info': '#88c0d0',
        'success': '#a3be8c',
        'warning': '#ebcb8b',
        'error': '#bf616a',
        'primary': '#5e81ac',
    }
    
    def __init__(self, refresh_rate: float = 2.0):
        self.refresh_rate = refresh_rate
        self.console = Console()
        self.storage = ExperimentStore()
        self.token_tracker = get_token_tracker()
        
    def create_layout(self) -> Layout:
        """Create the monitor layout."""
        layout = Layout()
        
        # Split into main sections
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=1)
        )
        
        # Split body into columns
        layout["body"].split_row(
            Layout(name="api_usage", ratio=1),
            Layout(name="experiments", ratio=2),
        )
        
        # Split experiments into active and summary
        layout["body"]["experiments"].split_column(
            Layout(name="active", ratio=2),
            Layout(name="summary", ratio=1)
        )
        
        return layout
    
    def render_header(self) -> Panel:
        """Render the header."""
        content = Align.center(
            f"[bold {self.COLORS['info']}]◆ PIDGIN SYSTEM MONITOR ◆[/bold {self.COLORS['info']}]\n"
            f"[{self.COLORS['dim']}]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/{self.COLORS['dim']}]",
            vertical="middle"
        )
        return Panel(content, style=self.COLORS['dim'])
    
    def render_api_usage(self) -> Panel:
        """Render API usage and limits."""
        table = Table(title="API Usage & Limits", show_header=True, expand=True)
        table.add_column("Provider", style=self.COLORS['text'])
        table.add_column("Usage", justify="right", style=self.COLORS['info'])
        table.add_column("Limit", justify="right", style=self.COLORS['dim'])
        table.add_column("Status", justify="center")
        
        providers = ["anthropic", "openai", "google", "xai"]
        
        for provider in providers:
            stats = self.token_tracker.get_usage_stats(provider)
            current_rate = int(stats['current_rate'])
            rate_limit = stats['rate_limit']
            usage_pct = stats['usage_percentage']
            
            # Format numbers with commas
            usage_str = f"{current_rate:,}"
            limit_str = f"{rate_limit:,}"
            
            # Determine status
            if stats['in_backoff']:
                status = f"[{self.COLORS['error']}]BACKOFF[/{self.COLORS['error']}]"
            elif usage_pct > 90:
                status = f"[{self.COLORS['error']}]MAXED[/{self.COLORS['error']}]"
            elif usage_pct > 70:
                status = f"[{self.COLORS['warning']}]HIGH[/{self.COLORS['warning']}]"
            else:
                status = f"[{self.COLORS['success']}]OK[/{self.COLORS['success']}]"
            
            # Add progress bar
            progress_bar = self._make_progress_bar(usage_pct)
            
            table.add_row(
                provider.capitalize(),
                usage_str,
                limit_str,
                f"{progress_bar} {status}"
            )
            
            # Add error count if any
            if stats['consecutive_errors'] > 0:
                table.add_row(
                    "",
                    f"[{self.COLORS['error']}]{stats['consecutive_errors']} errors[/{self.COLORS['error']}]",
                    "",
                    ""
                )
        
        # Add cost estimate section
        table.add_section()
        table.add_row(
            "[bold]Est. Cost/Hour[/bold]",
            "[bold]$0.00[/bold]",  # TODO: Calculate from token usage
            "",
            ""
        )
        
        return Panel(table, title="◇ API Usage", border_style=self.COLORS['primary'])
    
    def render_active_experiments(self) -> Panel:
        """Render active experiments with SharedState data."""
        table = Table(show_header=True, expand=True)
        table.add_column("ID", style=self.COLORS['dim'], width=8)
        table.add_column("Name", style=self.COLORS['info'])
        table.add_column("Models", style=self.COLORS['text'])
        table.add_column("Progress", justify="center")
        table.add_column("Conv", justify="center", style=self.COLORS['warning'])
        table.add_column("Status", justify="center")
        
        # Get active experiments
        experiments = self.storage.list_experiments(limit=10)
        active_count = 0
        
        for exp in experiments:
            if exp['status'] != 'running':
                continue
                
            active_count += 1
            exp_id = exp['experiment_id'][:8]
            name = exp['name'][:20]
            
            # Try to get SharedState data
            if SharedState.exists(exp['experiment_id']):
                try:
                    state = SharedState(exp['experiment_id'])
                    metrics = state.get_metrics()
                    state.close()
                    
                    if metrics:
                        # Use real-time data
                        progress = f"{metrics.completed_conversations}/{metrics.total_conversations}"
                        
                        # Get latest convergence
                        conv = metrics.convergence_scores[-1] if metrics.convergence_scores else 0
                        conv_str = f"{conv:.2f}"
                        if conv > 0.8:
                            conv_str = f"[{self.COLORS['error']}]{conv_str}![/{self.COLORS['error']}]"
                        
                        models = f"{metrics.agent_a_model} ↔ {metrics.agent_b_model}"
                        status = f"[{self.COLORS['success']}]●[/{self.COLORS['success']}] Turn {metrics.turn_count}"
                    else:
                        # Fallback to DB data
                        progress = f"{exp['completed_conversations']}/{exp['total_conversations']}"
                        conv_str = "-"
                        models = f"{exp.get('agent_a_model', '?')} ↔ {exp.get('agent_b_model', '?')}"
                        status = f"[{self.COLORS['warning']}]●[/{self.COLORS['warning']}] Active"
                except:
                    # Fallback to DB data
                    progress = f"{exp['completed_conversations']}/{exp['total_conversations']}"
                    conv_str = "-"
                    models = f"{exp.get('agent_a_model', '?')} ↔ {exp.get('agent_b_model', '?')}"
                    status = f"[{self.COLORS['dim']}]●[/{self.COLORS['dim']}] Unknown"
            else:
                # No SharedState - use DB
                progress = f"{exp['completed_conversations']}/{exp['total_conversations']}"
                conv_str = "-"
                models = f"{exp.get('agent_a_model', '?')} ↔ {exp.get('agent_b_model', '?')}"
                status = f"[{self.COLORS['dim']}]●[/{self.COLORS['dim']}] No data"
            
            table.add_row(exp_id, name, models, progress, conv_str, status)
        
        if active_count == 0:
            table.add_row(
                "[dim]No active experiments[/dim]",
                "", "", "", "", ""
            )
        
        return Panel(table, title=f"◇ Active Experiments ({active_count})", 
                    border_style=self.COLORS['success'])
    
    def render_summary(self) -> Panel:
        """Render experiment summary statistics."""
        # Get overall stats
        all_experiments = self.storage.list_experiments(limit=1000)
        
        total = len(all_experiments)
        running = sum(1 for e in all_experiments if e['status'] == 'running')
        completed = sum(1 for e in all_experiments if e['status'] == 'completed')
        failed = sum(1 for e in all_experiments if e['status'] == 'failed')
        
        total_conversations = sum(e.get('total_conversations', 0) for e in all_experiments)
        completed_conversations = sum(e.get('completed_conversations', 0) for e in all_experiments)
        
        # Calculate database size
        db_path = Path("./pidgin_output/experiments/experiments.db")
        db_size = db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0
        
        content = f"""[bold]System Statistics[/bold]

Experiments:
  Total: {total}
  Running: [{self.COLORS['success']}]{running}[/{self.COLORS['success']}]
  Completed: [{self.COLORS['info']}]{completed}[/{self.COLORS['info']}]
  Failed: [{self.COLORS['error']}]{failed}[/{self.COLORS['error']}]

Conversations:
  Total: {total_conversations:,}
  Completed: {completed_conversations:,}
  Success Rate: {(completed_conversations/total_conversations*100):.1f}%

Storage:
  Database: {db_size:.1f} MB
  Output Dir: ./pidgin_output/
"""
        
        return Panel(content, title="◇ Summary", border_style=self.COLORS['dim'])
    
    def render_footer(self) -> Panel:
        """Render footer with controls."""
        return Panel(
            "[bold]Press Ctrl+C to exit[/bold]",
            style=self.COLORS['dim']
        )
    
    def _make_progress_bar(self, percentage: float, width: int = 10) -> str:
        """Create a text progress bar."""
        filled = int(width * percentage / 100)
        empty = width - filled
        
        if percentage > 90:
            color = self.COLORS['error']
        elif percentage > 70:
            color = self.COLORS['warning']
        else:
            color = self.COLORS['success']
            
        bar = f"[{color}]{'▓' * filled}[/{color}]{'░' * empty}"
        return f"{bar} {percentage:3.0f}%"
    
    async def run(self):
        """Run the monitor."""
        layout = self.create_layout()
        
        with Live(layout, console=self.console, refresh_per_second=0.5) as live:
            while True:
                try:
                    # Update all panels
                    layout["header"].update(self.render_header())
                    layout["body"]["api_usage"].update(self.render_api_usage())
                    layout["body"]["experiments"]["active"].update(self.render_active_experiments())
                    layout["body"]["experiments"]["summary"].update(self.render_summary())
                    layout["footer"].update(self.render_footer())
                    
                    await asyncio.sleep(self.refresh_rate)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    # Show error but keep running
                    self.console.print(f"[red]Error: {e}[/red]")
                    await asyncio.sleep(5)


def main():
    """Run the system monitor."""
    monitor = SystemMonitor()
    asyncio.run(monitor.run())


if __name__ == "__main__":
    main()