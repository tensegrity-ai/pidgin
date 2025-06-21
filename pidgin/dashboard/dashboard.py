# pidgin/dashboard/dashboard.py
"""Clean dashboard implementation using SharedState."""

import asyncio
from datetime import datetime
from typing import Dict, Any, List

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

from ..experiments.shared_state import SharedState, SharedMetrics


class Dashboard:
    """Dashboard that displays experiment progress from SharedState."""
    
    # Nord color palette
    COLORS = {
        'dim': '#4c566a',
        'text': '#d8dee9',
        'success': '#a3be8c',
        'warning': '#ebcb8b',
        'error': '#bf616a',
        'info': '#88c0d0',
        'accent': '#5e81ac',
    }
    
    # Unicode blocks for sparklines
    SPARKS = " ▁▂▃▄▅▆▇█"
    
    def __init__(self, shared_state: SharedState, experiment_id: str, experiment_name: str):
        """Initialize dashboard.
        
        Args:
            shared_state: SharedState instance to read from
            experiment_id: Experiment ID
            experiment_name: Human-friendly experiment name
        """
        self.shared_state = shared_state
        self.experiment_id = experiment_id
        self.experiment_name = experiment_name
        self.console = Console()
        self.running = True
        self.start_time = datetime.now()
        
    def create_layout(self) -> Layout:
        """Create the dashboard layout."""
        layout = Layout()
        
        # Main vertical split
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=1)
        )
        
        # Split body into two columns
        layout["body"].split_row(
            Layout(name="metrics", ratio=2),
            Layout(name="messages", ratio=1)
        )
        
        # Split metrics into two rows
        layout["body"]["metrics"].split_column(
            Layout(name="progress", size=4),
            Layout(name="sparklines")
        )
        
        return layout
    
    def render_header(self, metrics: SharedMetrics) -> Panel:
        """Render experiment header."""
        elapsed = datetime.now() - self.start_time
        elapsed_str = f"{int(elapsed.total_seconds() // 60)}m {int(elapsed.total_seconds() % 60)}s"
        
        status_color = {
            "running": self.COLORS['success'],
            "completed": self.COLORS['info'],
            "failed": self.COLORS['error'],
            "error": self.COLORS['error']
        }.get(metrics.status, self.COLORS['warning'])
        
        header_text = (
            f"[bold]◆ {self.experiment_name}[/bold]  "
            f"[{self.COLORS['dim']}]({self.experiment_id[:8]})[/{self.COLORS['dim']}]  "
            f"[{status_color}]{metrics.status.upper()}[/{status_color}]  "
            f"[{self.COLORS['dim']}]{elapsed_str}[/{self.COLORS['dim']}]"
        )
        
        return Panel(
            Align.center(header_text),
            style=self.COLORS['accent'],
            box=Panel.get_box("MINIMAL")
        )
    
    def render_progress(self, metrics: SharedMetrics) -> Panel:
        """Render progress information."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Label", style=self.COLORS['dim'])
        table.add_column("Value", style=self.COLORS['text'])
        
        # Progress bar
        progress_pct = (metrics.completed_conversations / metrics.total_conversations * 100) if metrics.total_conversations > 0 else 0
        progress_bar = self._make_progress_bar(progress_pct, width=20)
        
        table.add_row(
            "Progress:",
            f"{progress_bar} {metrics.completed_conversations}/{metrics.total_conversations} ({progress_pct:.0f}%)"
        )
        
        # Current conversation
        if metrics.current_conversation_id:
            conv_num = int(metrics.current_conversation_id.split('_')[-1]) + 1
            table.add_row(
                "Current:",
                f"Conversation {conv_num}, Turn {metrics.turn_count}"
            )
        
        # Models
        table.add_row(
            "Models:",
            f"{metrics.agent_a_model} ↔ {metrics.agent_b_model}"
        )
        
        return Panel(table, title="PROGRESS", border_style=self.COLORS['dim'])
    
    def render_sparklines(self, metrics: SharedMetrics) -> Panel:
        """Render metrics with sparklines."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style=self.COLORS['info'])
        table.add_column("Graph", style=self.COLORS['text'])
        table.add_column("Value", style=self.COLORS['warning'])
        
        # Convergence
        if metrics.convergence_scores:
            spark = self._make_sparkline(metrics.convergence_scores[-20:])
            current = metrics.convergence_scores[-1]
            color = self.COLORS['error'] if current > 0.8 else self.COLORS['warning']
            table.add_row(
                "Convergence",
                spark,
                f"[{color}]{current:.3f}[/{color}]"
            )
        
        # Similarity
        if metrics.similarity_scores:
            spark = self._make_sparkline(metrics.similarity_scores[-20:])
            current = metrics.similarity_scores[-1]
            table.add_row(
                "Similarity",
                spark,
                f"{current:.3f}"
            )
        
        # Vocabulary
        if metrics.vocabulary_scores:
            spark = self._make_sparkline(metrics.vocabulary_scores[-20:])
            current = metrics.vocabulary_scores[-1]
            table.add_row(
                "Vocabulary",
                spark,
                f"{current:.1%}"
            )
        
        return Panel(table, title="METRICS", border_style=self.COLORS['dim'])
    
    def render_messages(self, metrics: SharedMetrics) -> Panel:
        """Render recent messages."""
        lines = []
        
        if not metrics.last_messages:
            lines.append("[dim]No messages yet...[/dim]")
        else:
            for msg in metrics.last_messages[-5:]:  # Last 5 messages
                agent = msg.get('agent', '?')
                content = msg.get('content', '')
                
                # Color based on agent
                agent_color = self.COLORS['success'] if agent == 'A' else self.COLORS['info']
                
                # Format message
                lines.append(f"[{agent_color}]{agent}:[/{agent_color}] {content}")
                lines.append("")  # Empty line between messages
        
        content = "\n".join(lines).strip()
        return Panel(
            content,
            title="RECENT MESSAGES",
            border_style=self.COLORS['dim'],
            height=15  # Fixed height to prevent jumping
        )
    
    def render_footer(self) -> Panel:
        """Render footer."""
        return Panel(
            "[bold]Press Ctrl+C to detach[/bold]",
            style=self.COLORS['dim'],
            box=Panel.get_box("MINIMAL")
        )
    
    def _make_sparkline(self, values: List[float], width: int = 20) -> str:
        """Create a Unicode sparkline."""
        if not values or len(values) < 2:
            return "─" * width
        
        # Normalize values
        min_val = min(values)
        max_val = max(values)
        
        if max_val == min_val:
            return "─" * len(values)
        
        sparkline = ""
        for v in values[-width:]:
            normalized = (v - min_val) / (max_val - min_val)
            index = int(normalized * (len(self.SPARKS) - 1))
            sparkline += self.SPARKS[index]
        
        return sparkline.ljust(width)
    
    def _make_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create a progress bar."""
        filled = int(width * percentage / 100)
        empty = width - filled
        
        return f"[{self.COLORS['success']}]{'█' * filled}[/{self.COLORS['success']}][{self.COLORS['dim']}]{'░' * empty}[/{self.COLORS['dim']}]"
    
    async def run(self) -> Dict[str, Any]:
        """Run the dashboard loop."""
        layout = self.create_layout()
        
        # Create a loading panel
        loading_panel = Panel(
            Align.center(
                f"[{self.COLORS['info']}]◆ Initializing experiment '{self.experiment_name}'...[/{self.COLORS['info']}]\n\n"
                f"[{self.COLORS['dim']}]Waiting for data from experiment {self.experiment_id[:8]}[/{self.COLORS['dim']}]",
                vertical="middle"
            ),
            title="LOADING",
            border_style=self.COLORS['warning'],
            height=10
        )
        
        try:
            with Live(
                layout,
                console=self.console,
                refresh_per_second=2,
                screen=True
            ) as live:
                # Show loading state initially
                layout["header"].update(loading_panel)
                layout["body"]["metrics"]["progress"].update(Panel("[dim]Waiting...[/dim]"))
                layout["body"]["metrics"]["sparklines"].update(Panel("[dim]Waiting...[/dim]"))
                layout["body"]["messages"].update(Panel("[dim]Waiting...[/dim]"))
                
                has_data = False
                
                while self.running:
                    # Read latest metrics
                    metrics = self.shared_state.get_metrics()
                    
                    if not metrics:
                        # Still no data - keep showing loading
                        await asyncio.sleep(0.5)
                        continue
                    
                    # We have data! Update flag
                    if not has_data:
                        has_data = True
                        # Clear loading state
                    
                    # Update all panels with real data
                    layout["header"].update(self.render_header(metrics))
                    layout["body"]["metrics"]["progress"].update(self.render_progress(metrics))
                    layout["body"]["metrics"]["sparklines"].update(self.render_sparklines(metrics))
                    layout["body"]["messages"].update(self.render_messages(metrics))
                    layout["footer"].update(self.render_footer())
                    
                    # Check if experiment is done
                    if metrics.status in ['completed', 'failed', 'stopped']:
                        await asyncio.sleep(3)  # Show final state
                        self.running = False
                        break
                    
                    await asyncio.sleep(0.5)
                    
        except KeyboardInterrupt:
            # Ctrl+C - detach
            self.running = False
            return {"detached": True}
        
        return {"completed": True}