"""Multi-panel dashboard with rich layout."""

import asyncio
from datetime import datetime, timedelta
from typing import List

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text

from ..core.event_bus import EventBus
from .minimal_state import DashboardStateManager


class Phase3Dashboard:
    """Rich multi-panel dashboard."""
    
    SPARKS = " ▁▂▃▄▅▆▇█"
    
    def __init__(self, event_bus: EventBus, experiment_id: str):
        self.event_bus = event_bus
        self.experiment_id = experiment_id
        
        self.state_manager = DashboardStateManager(experiment_id)
        self.state_manager.subscribe_to_bus(event_bus)
        
        self.console = Console()
        self.running = True
        self.start_time = datetime.now()
        
    def _make_sparkline(self, values: List[float], width: int = 10) -> str:
        """Create sparkline from values."""
        if not values or len(values) < 2:
            return "─" * width
            
        recent = list(values)[-width:]
        min_val = min(recent)
        max_val = max(recent)
        
        if max_val == min_val:
            return "─" * width
            
        sparkline = ""
        for v in recent:
            index = int((v - min_val) / (max_val - min_val) * (len(self.SPARKS) - 1))
            sparkline += self.SPARKS[index]
            
        return sparkline.ljust(width)
    
    def _create_layout(self) -> Layout:
        """Create the dashboard layout."""
        layout = Layout()
        
        # Main vertical split
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="conversation", size=8),
            Layout(name="metrics", size=10),
            Layout(name="footer", size=1)
        )
        
        # Split metrics into two columns
        layout["metrics"].split_row(
            Layout(name="turn_metrics"),
            Layout(name="message_metrics")
        )
        
        return layout
    
    def _make_header(self) -> Panel:
        """Create header with experiment info."""
        state = self.state_manager.state
        
        # Progress bar
        progress = 0
        if state.total_conversations > 0:
            progress = state.completed_conversations / state.total_conversations
            
        filled = int(progress * 10)
        bar = "█" * filled + "░" * (10 - filled)
        
        # Runtime
        runtime = datetime.now() - self.start_time
        runtime_str = f"{int(runtime.total_seconds() // 60)}m {int(runtime.total_seconds() % 60)}s"
        
        content = f"Progress: {bar} {state.completed_conversations}/{state.total_conversations} │ Turn: {state.current_turn} │ Runtime: {runtime_str}"
        
        return Panel(
            content,
            title=f"◆ EXPERIMENT: {state.experiment_name}",
            border_style="blue"
        )
    
    def _make_conversation_panel(self) -> Panel:
        """Create conversation ticker panel."""
        state = self.state_manager.state
        
        lines = []
        lines.append(f"[cyan]Conversation {state.current_conversation} │ Turn {state.current_turn}[/cyan]")
        lines.append("")
        
        # Show recent messages
        for msg in list(state.recent_messages)[-4:]:
            lines.append(f"[bold]{msg['agent']}:[/bold] {msg['preview']}")
        
        # Pad to consistent height
        while len(lines) < 6:
            lines.append("")
        
        return Panel(
            "\n".join(lines),
            title="CURRENT CONVERSATION",
            border_style="green"
        )
    
    def _make_turn_metrics_panel(self) -> Panel:
        """Create turn metrics panel."""
        state = self.state_manager.state
        
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="yellow")
        table.add_column("Sparkline", style="white") 
        table.add_column("Value", style="cyan")
        
        # Convergence
        conv_spark = self._make_sparkline(list(state.convergence_history))
        conv_val = state.latest_metrics.get('convergence_score', 0)
        table.add_row("Convergence", conv_spark, f"{conv_val:.3f}")
        
        # Vocabulary overlap
        vocab_spark = self._make_sparkline(list(state.vocabulary_overlap_history))
        vocab_val = state.latest_metrics.get('vocabulary_overlap', 0)
        table.add_row("Vocab Overlap", vocab_spark, f"{vocab_val:.3f}")
        
        # TTR Agent A
        ttr_a_spark = self._make_sparkline(list(state.ttr_a_history))
        ttr_a_val = state.ttr_a_history[-1] if state.ttr_a_history else 0
        table.add_row("TTR Agent A", ttr_a_spark, f"{ttr_a_val:.3f}")
        
        # TTR Agent B
        ttr_b_spark = self._make_sparkline(list(state.ttr_b_history))
        ttr_b_val = state.ttr_b_history[-1] if state.ttr_b_history else 0
        table.add_row("TTR Agent B", ttr_b_spark, f"{ttr_b_val:.3f}")
        
        return Panel(table, title="TURN METRICS", border_style="yellow")
    
    def _make_message_metrics_panel(self) -> Panel:
        """Create message metrics panel."""
        state = self.state_manager.state
        
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Sparkline", style="white")
        table.add_column("Value", style="yellow")
        
        # Message lengths
        len_a_spark = self._make_sparkline([float(x) for x in state.length_a_history])
        len_a_val = state.length_a_history[-1] if state.length_a_history else 0
        table.add_row("Length A", len_a_spark, f"{len_a_val}")
        
        len_b_spark = self._make_sparkline([float(x) for x in state.length_b_history])
        len_b_val = state.length_b_history[-1] if state.length_b_history else 0
        table.add_row("Length B", len_b_spark, f"{len_b_val}")
        
        # Word counts
        words_a_spark = self._make_sparkline([float(x) for x in state.words_a_history])
        words_a_val = state.words_a_history[-1] if state.words_a_history else 0
        table.add_row("Words A", words_a_spark, f"{words_a_val}")
        
        words_b_spark = self._make_sparkline([float(x) for x in state.words_b_history])
        words_b_val = state.words_b_history[-1] if state.words_b_history else 0
        table.add_row("Words B", words_b_spark, f"{words_b_val}")
        
        return Panel(table, title="MESSAGE METRICS", border_style="cyan")
    
    def _make_footer(self) -> Panel:
        """Create footer panel."""
        return Panel(
            "[dim][D]etach  [S]top  │  Events: " + str(self.state_manager.state.total_events) + "[/dim]",
            border_style="dim",
            style="dim"
        )
    
    async def run(self):
        """Run the dashboard with better interrupt handling."""
        await asyncio.sleep(1)  # Let events start
        
        layout = self._create_layout()
        
        try:
            with Live(
                layout, 
                console=self.console, 
                refresh_per_second=2,
                screen=True,  # Use alternate screen
                redirect_stdout=False,
                redirect_stderr=False
            ) as live:
                while self.running:
                    try:
                        # Update all panels
                        layout["header"].update(self._make_header())
                        layout["conversation"].update(self._make_conversation_panel())
                        layout["turn_metrics"].update(self._make_turn_metrics_panel())
                        layout["message_metrics"].update(self._make_message_metrics_panel())
                        layout["footer"].update(self._make_footer())
                        
                        # Check if complete
                        state = self.state_manager.state
                        if (state.completed_conversations >= state.total_conversations and 
                            state.total_conversations > 0):
                            await asyncio.sleep(3)
                            self.running = False
                        
                        await asyncio.sleep(0.5)
                        
                    except asyncio.CancelledError:
                        # Clean cancellation
                        self.running = False
                        break
                    except Exception:
                        # Log error but keep running
                        # Don't print to console - it interferes with Live
                        pass
                        
        except KeyboardInterrupt:
            # Clean exit on Ctrl+C
            self.running = False
        finally:
            # Ensure we return a result
            return {'detached': True, 'stopped': False}