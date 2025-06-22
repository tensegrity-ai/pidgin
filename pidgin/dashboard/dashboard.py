# pidgin/dashboard/dashboard.py
"""Real-time experiment dashboard using SharedState."""

import asyncio
import sys
from typing import Optional
from datetime import datetime
from collections import deque

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

from .attach import attach_to_experiment, find_running_experiments
from ..experiments.shared_state import SharedState


class ExperimentDashboard:
    """Live dashboard showing experiment progress via SharedState."""
    
    def __init__(self, experiment_id: str, shared_state: SharedState):
        """Initialize dashboard.
        
        Args:
            experiment_id: Experiment to monitor
            shared_state: Connected SharedState instance
        """
        self.experiment_id = experiment_id
        self.shared_state = shared_state
        self.console = Console()
        self.running = True
        
    def _create_layout(self) -> Layout:
        """Create dashboard layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=1)
        )
        
        # Split main into three columns
        layout["main"].split_row(
            Layout(name="progress", ratio=1),
            Layout(name="metrics", ratio=1),
            Layout(name="messages", ratio=1)
        )
        
        return layout
    
    def _make_header(self, data: dict) -> Panel:
        """Create header with experiment info."""
        status = data.get('status', 'unknown')
        models = data.get('models', {})
        
        # Color based on status
        status_color = {
            'initializing': 'yellow',
            'running': 'green',
            'completed': 'blue',
            'failed': 'red',
            'interrupted': 'orange'
        }.get(status, 'white')
        
        header_text = (
            f"[bold]Experiment:[/bold] {self.experiment_id}  "
            f"[bold]Status:[/bold] [{status_color}]{status}[/{status_color}]  "
            f"[bold]Models:[/bold] {models.get('agent_a', '?')} ↔ {models.get('agent_b', '?')}"
        )
        
        return Panel(header_text, style="bold blue")
    
    def _make_progress_panel(self, data: dict) -> Panel:
        """Create progress panel."""
        conv_count = data.get('conversation_count', {})
        total = conv_count.get('total', 0)
        completed = conv_count.get('completed', 0)
        
        if total > 0:
            progress = completed / total
            bar_width = 20
            filled = int(progress * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            percent = f"{progress * 100:.1f}%"
        else:
            bar = "░" * 20
            percent = "0.0%"
        
        content = f"""[bold]Conversations:[/bold]
{completed} / {total} completed

[bold]Progress:[/bold]
{bar} {percent}

[bold]Current:[/bold]
Turn {data.get('current_turn', 0)}"""
        
        return Panel(content, title="Progress", border_style="green")
    
    def _make_metrics_panel(self, data: dict) -> Panel:
        """Create metrics panel with sparklines."""
        metrics = data.get('metrics', {})
        
        def sparkline(values, width=15):
            """Create a simple sparkline."""
            if not values:
                return "─" * width
            
            chars = "▁▂▃▄▅▆▇█"
            min_val = min(values)
            max_val = max(values)
            
            if max_val == min_val:
                return "─" * width
            
            # Resample to fit width
            if len(values) > width:
                # Take last 'width' values
                values = values[-width:]
            
            line = ""
            for val in values:
                idx = int((val - min_val) / (max_val - min_val) * (len(chars) - 1))
                line += chars[idx]
            
            return line.ljust(width)
        
        # Get metric histories
        convergence = metrics.get('convergence', [])
        similarity = metrics.get('similarity', [])
        vocabulary = metrics.get('vocabulary', [])
        
        content = f"""[bold]Convergence:[/bold]
{sparkline(convergence)} {convergence[-1]:.3f if convergence else 0:.3f}

[bold]Similarity:[/bold]
{sparkline(similarity)} {similarity[-1]:.3f if similarity else 0:.3f}

[bold]Vocabulary:[/bold]
{sparkline(vocabulary)} {vocabulary[-1]:.3f if vocabulary else 0:.3f}"""
        
        return Panel(content, title="Metrics", border_style="cyan")
    
    def _make_messages_panel(self, data: dict) -> Panel:
        """Create recent messages panel."""
        metrics = data.get('metrics', {})
        messages = metrics.get('last_messages', [])
        
        if not messages:
            content = "[dim]No messages yet...[/dim]"
        else:
            lines = []
            for msg in messages[-6:]:  # Show last 6
                agent = msg.get('agent', '?')
                text = msg.get('content', '')
                # Truncate long messages
                if len(text) > 50:
                    text = text[:47] + "..."
                
                color = "yellow" if agent == "A" else "cyan"
                lines.append(f"[{color}]{agent}:[/{color}] {text}")
            
            content = "\n\n".join(lines)
        
        return Panel(content, title="Recent Messages", border_style="yellow")
    
    def _make_footer(self) -> Panel:
        """Create footer with controls."""
        return Panel(
            "[dim]Press Ctrl+C to detach from dashboard[/dim]",
            style="dim"
        )
    
    async def run(self):
        """Run the dashboard."""
        layout = self._create_layout()
        
        try:
            with Live(
                layout,
                console=self.console,
                refresh_per_second=2,
                screen=True
            ) as live:
                while self.running:
                    try:
                        # Get latest data from SharedState
                        data = self.shared_state.get_all_data()
                        
                        # Update all panels
                        layout["header"].update(self._make_header(data))
                        layout["progress"].update(self._make_progress_panel(data))
                        layout["metrics"].update(self._make_metrics_panel(data))
                        layout["messages"].update(self._make_messages_panel(data))
                        layout["footer"].update(self._make_footer())
                        
                        # Check if complete
                        status = data.get('status', 'unknown')
                        if status in ['completed', 'failed', 'interrupted']:
                            # Show for a few more seconds then exit
                            await asyncio.sleep(3)
                            self.running = False
                            break
                        
                        await asyncio.sleep(0.5)
                        
                    except KeyboardInterrupt:
                        self.running = False
                        break
                    except Exception as e:
                        # Don't crash on errors
                        await asyncio.sleep(1)
                        
        except KeyboardInterrupt:
            pass
        finally:
            # Clear the screen
            self.console.clear()
            self.console.print(f"\n[green]✓[/green] Detached from experiment {self.experiment_id}")
            
            # Show final status
            try:
                final_data = self.shared_state.get_all_data()
                status = final_data.get('status', 'unknown')
                conv_count = final_data.get('conversation_count', {})
                
                self.console.print(f"  Status: {status}")
                self.console.print(f"  Completed: {conv_count.get('completed', 0)}/{conv_count.get('total', 0)} conversations")
            except:
                pass


async def run_dashboard(experiment_id: Optional[str] = None):
    """Main entry point for dashboard.
    
    Args:
        experiment_id: Specific experiment to attach to, or None to find one
    """
    console = Console()
    
    # If no experiment specified, try to find one
    if not experiment_id:
        console.print("[yellow]No experiment specified, looking for running experiments...[/yellow]")
        running = find_running_experiments()
        
        if not running:
            console.print("[red]No running experiments found.[/red]")
            console.print("[dim]Start an experiment with: pidgin experiment start ...[/dim]")
            return
        
        if len(running) == 1:
            experiment_id = running[0]
            console.print(f"[green]Found experiment: {experiment_id}[/green]")
        else:
            # Multiple experiments, show menu
            console.print(f"\n[bold]Found {len(running)} running experiments:[/bold]")
            for i, exp_id in enumerate(running):
                console.print(f"  {i+1}. {exp_id}")
            
            choice = console.input("\nSelect experiment (1-{}): ".format(len(running)))
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(running):
                    experiment_id = running[idx]
                else:
                    console.print("[red]Invalid selection[/red]")
                    return
            except ValueError:
                console.print("[red]Invalid selection[/red]")
                return
    
    # Try to attach to the experiment
    console.print(f"\n[cyan]Attaching to experiment {experiment_id}...[/cyan]")
    
    result = await attach_to_experiment(experiment_id)
    
    if not result['success']:
        console.print(f"[red]Failed to attach: {result['error']}[/red]")
        return
    
    # Create and run dashboard
    dashboard = ExperimentDashboard(experiment_id, result['shared_state'])
    
    try:
        await dashboard.run()
    except Exception as e:
        console.print(f"[red]Dashboard error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Handle command line usage
    import sys
    
    exp_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        asyncio.run(run_dashboard(exp_id))
    except KeyboardInterrupt:
        print("\n[Interrupted]")