"""Live experiment monitoring dashboard using Rich."""

import asyncio
import sys
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.text import Text
from rich.align import Align

from .storage import ExperimentStore


class ExperimentDashboard:
    """Real-time experiment monitoring with Rich."""
    
    # Unicode blocks for sparklines
    SPARKS = " ▁▂▃▄▅▆▇█"
    
    # Status glyphs (Nord theme)
    GLYPHS = {
        "active": "◆",
        "complete": "◇", 
        "failed": "⊗",
        "queued": "○",
        "paused": "⊘",
        "rate_limited": "▲",
    }
    
    # Nord colors
    COLORS = {
        "dim": "#4c566a",
        "text": "#d8dee9",
        "cyan": "#88c0d0",
        "red": "#bf616a",
        "yellow": "#ebcb8b",
        "green": "#a3be8c",
        "blue": "#5e81ac",
    }
    
    def __init__(self, experiment_id: str, refresh_interval: float = 2.0):
        """Initialize dashboard for an experiment.
        
        Args:
            experiment_id: Experiment to monitor
            refresh_interval: Seconds between updates
        """
        self.experiment_id = experiment_id
        self.refresh_interval = refresh_interval
        self.storage = ExperimentStore()
        
        self.console = Console()
        self.layout = self._build_layout()
        self.running = True
        self.detached = False
        self.stopped = False
        
        # Caches to avoid recalculating everything
        self.sparkline_cache: Dict[str, List[float]] = defaultdict(lambda: [])
        self.metric_history: Dict[str, List[float]] = defaultdict(lambda: [])
        
    def _build_layout(self) -> Layout:
        """Create the dashboard layout."""
        # Determine terminal size
        width = self.console.width
        height = self.console.height
        
        if width >= 140:
            # Full layout with side panels
            layout = Layout(name="root")
            layout.split_column(
                Layout(name="header", size=4),
                Layout(name="body"),
                Layout(name="footer", size=1)
            )
            
            # Split body into main and sidebar
            layout["body"].split_row(
                Layout(name="main", ratio=3),
                Layout(name="sidebar", ratio=1)
            )
            
            # Split main into conversations and statistics
            layout["body"]["main"].split_column(
                Layout(name="conversations", ratio=2),
                Layout(name="statistics", ratio=3)
            )
            
            # Sidebar contains metrics
            layout["body"]["sidebar"].update(Panel("", title="CONVERGENCE METRICS"))
            
        elif width >= 110:
            # Vertical stack
            layout = Layout(name="root")
            layout.split_column(
                Layout(name="header", size=4),
                Layout(name="conversations", size=15),
                Layout(name="metrics", size=12),
                Layout(name="statistics", size=15),
                Layout(name="footer", size=1)
            )
        else:
            # Minimal layout
            layout = Layout(name="root")
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="conversations", size=12),
                Layout(name="statistics", size=10),
                Layout(name="footer", size=1)
            )
            
        return layout
    
    async def run(self):
        """Run the dashboard until stopped."""
        # Only do terminal setup if we have a real terminal
        old_settings = None
        try:
            if hasattr(sys.stdin, 'fileno'):
                import termios
                import tty
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
        except:
            # Not a terminal, keyboard input won't work
            pass
        
        try:
            with Live(self.layout, refresh_per_second=0.5, screen=True) as live:
                while self.running:
                    # Update display
                    await self._update_all_panels()
                    
                    # Check for keyboard input (non-blocking) if we have a terminal
                    if old_settings is not None:
                        import select
                        if select.select([sys.stdin], [], [], 0)[0]:
                            key = sys.stdin.read(1).lower()
                            
                            if key == 'd':
                                # Detach - just exit cleanly
                                self.running = False
                                self.detached = True
                            elif key == 's':
                                # Stop experiment
                                self.storage.stop_experiment(self.experiment_id)
                                self.running = False
                                self.stopped = True
                    
                    await asyncio.sleep(self.refresh_interval)
                    
        finally:
            # Restore terminal settings
            if old_settings is not None:
                import termios
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    
    async def _update_all_panels(self):
        """Update all dashboard panels with latest data."""
        # Fetch latest data
        experiment = self.storage.get_experiment(self.experiment_id)
        if not experiment:
            self.layout["header"].update(
                Panel("[red]Experiment not found![/red]", 
                      title="ERROR", 
                      style="red")
            )
            return
            
        # Update each panel
        self.layout["header"].update(self._render_header(experiment))
        
        # Get active conversations
        active_convs = self.storage.get_active_conversations(self.experiment_id)
        self.layout["conversations"].update(self._render_conversations(active_convs))
        
        # Update metrics panel if it exists
        try:
            if "metrics" in self.layout:
                metrics = self._aggregate_metrics(active_convs)
                self.layout["metrics"].update(self._render_metrics(metrics))
            elif "body" in self.layout and "sidebar" in self.layout["body"]:
                metrics = self._aggregate_metrics(active_convs)
                self.layout["body"]["sidebar"].update(self._render_metrics(metrics))
        except KeyError:
            pass
            
        # Update statistics
        try:
            if "statistics" in self.layout:
                stats = self.storage.calculate_experiment_statistics(self.experiment_id)
                self.layout["statistics"].update(self._render_statistics(stats))
            elif "body" in self.layout and "main" in self.layout["body"] and "statistics" in self.layout["body"]["main"]:
                stats = self.storage.calculate_experiment_statistics(self.experiment_id)
                self.layout["body"]["main"]["statistics"].update(self._render_statistics(stats))
        except KeyError:
            pass
            
        self.layout["footer"].update(self._render_footer())
    
    def _render_header(self, experiment: Dict) -> Panel:
        """Render experiment progress header."""
        total = experiment['total_conversations']
        completed = experiment['completed_conversations'] 
        failed = experiment['failed_conversations']
        
        # Calculate timing
        if experiment.get('started_at'):
            started = datetime.fromisoformat(experiment['started_at'])
            runtime = datetime.now() - started
        else:
            runtime = timedelta(0)
        
        if completed > 0 and runtime.total_seconds() > 0:
            avg_time = runtime / completed
            eta = avg_time * (total - completed)
            eta_str = f"ETA: {self._format_duration(eta)}"
            rate = f"{completed/runtime.total_seconds()*60:.1f} conv/min"
        else:
            eta_str = "ETA: calculating..."
            rate = "-- conv/min"
        
        # Progress bar using block characters
        progress = completed / total if total > 0 else 0
        bar_width = 30
        filled = int(bar_width * progress)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        # Status counts  
        active = self.storage.get_active_conversation_count(self.experiment_id)
        queued = total - completed - failed - active
        
        # Create header text
        header = Text()
        header.append(f"{experiment['name']}\n", style="bold")
        header.append(f"{bar} ", style=self.COLORS['cyan'])
        header.append(f"{completed}/{total} ({progress*100:.1f}%)\n", style=self.COLORS['text'])
        header.append(f"{self.GLYPHS['active']} Active: {active}  ", style=self.COLORS['green'])
        header.append(f"{self.GLYPHS['complete']} Done: {completed}  ", style=self.COLORS['cyan'])
        header.append(f"{self.GLYPHS['failed']} Failed: {failed}  ", style=self.COLORS['red'])
        header.append(f"{self.GLYPHS['queued']} Queue: {queued}  ", style=self.COLORS['dim'])
        header.append(f"│ {rate} │ {eta_str}", style=self.COLORS['dim'])
        
        return Panel(header, expand=True, style=self.COLORS['text'])
    
    def _render_conversations(self, conversations: List[Dict]) -> Panel:
        """Render active conversations table."""
        table = Table(show_header=True, header_style="bold", expand=True)
        
        # Adjust columns based on width
        if self.console.width >= 140:
            table.add_column("ID", width=6, style=self.COLORS['dim'])
            table.add_column("Models", width=20)
            table.add_column("Turn", width=8, justify="center")
            table.add_column("VOv", width=6, justify="right")
            table.add_column("Conv", width=6, justify="right") 
            table.add_column("Len", width=6, justify="right")
            table.add_column("Last Message", no_wrap=False)
        else:
            table.add_column("ID", width=4, style=self.COLORS['dim'])
            table.add_column("Turn", width=6, justify="center")
            table.add_column("VOv%", width=5, justify="right")
            table.add_column("Message", width=30)
        
        for conv in conversations[:12]:  # Limit display
            conv_id = conv['conversation_id'][:6]
            
            # Get latest metrics
            latest = self.storage.get_latest_turn_metrics(conv['conversation_id'])
            
            if latest:
                vocab_overlap = f"{int(latest.get('vocabulary_overlap', 0) * 100)}"
                convergence = f"{latest.get('convergence_score', 0):.2f}"
                msg_len = str(int(latest.get('avg_message_length', 0)))
            else:
                vocab_overlap = "-"
                convergence = "-"
                msg_len = "-"
            
            # Turn progress
            turn_num = conv.get('turn_number', 0)
            max_turns = conv.get('max_turns', 50)
            turn_str = f"{turn_num}/{max_turns}"
            
            # Status coloring
            if conv.get('rate_limited'):
                status_style = self.COLORS['yellow']
                turn_str = f"[{self.COLORS['yellow']}]⊘ {turn_str}[/]"
            elif latest and latest.get('convergence_score', 0) > 0.8:
                status_style = self.COLORS['green'] 
                turn_str = f"[{self.COLORS['green']}]▲ {turn_str}[/]"
            else:
                status_style = self.COLORS['cyan']
            
            # Last message preview
            last_msg = self.storage.get_last_message(conv['conversation_id'])
            if last_msg:
                msg_preview = self._truncate(last_msg, 50)
            else:
                msg_preview = "[dim]waiting...[/dim]"
            
            if self.console.width >= 140:
                models = f"{conv['agent_a_model'][:8]}↔{conv['agent_b_model'][:8]}"
                table.add_row(
                    conv_id,
                    models,
                    turn_str,
                    vocab_overlap + "%",
                    convergence,
                    msg_len,
                    msg_preview
                )
            else:
                table.add_row(
                    conv_id[:4],
                    turn_str,
                    vocab_overlap + "%",
                    msg_preview
                )
        
        return Panel(table, title="ACTIVE CONVERSATIONS", expand=True, 
                    style=self.COLORS['text'])
    
    def _render_metrics(self, metrics: Dict) -> Panel:
        """Render convergence metrics panel with sparklines."""
        lines = []
        
        # Update metric history
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                self.metric_history[key].append(value)
                # Keep last 20 values
                if len(self.metric_history[key]) > 20:
                    self.metric_history[key].pop(0)
        
        # Sparklines for key metrics
        metric_configs = [
            ('vocabulary_overlap', 'Vocab Overlap', '%', 100),
            ('convergence_score', 'Convergence', '', 1),
            ('avg_message_length', 'Msg Length', '', None),
            ('type_token_ratio', 'TTR', '', 1),
            ('mimicry_score', 'Mimicry', '', 1),
        ]
        
        for metric_key, label, suffix, multiplier in metric_configs:
            if metric_key in self.metric_history:
                values = self.metric_history[metric_key][-10:]
                if values:
                    spark = self._make_sparkline(values)
                    current = values[-1]
                    if multiplier:
                        display_val = f"{int(current * multiplier)}{suffix}"
                    else:
                        display_val = f"{int(current)}{suffix}"
                    
                    lines.append(f"{label:.<16} {spark} {display_val:>6}")
        
        # Separator
        lines.append("─" * 30)
        
        # Current statistics
        lines.append("Current State:")
        high_conv = metrics.get('high_convergence_count', 0)
        short_msg = metrics.get('short_message_count', 0) 
        high_mimicry = metrics.get('high_mimicry_count', 0)
        
        lines.append(f"High convergence: {high_conv} convs")
        lines.append(f"Short messages: {short_msg} convs")
        lines.append(f"High mimicry: {high_mimicry} convs")
        
        text = Text("\n".join(lines), style=self.COLORS['text'])
        return Panel(text, title="CONVERGENCE METRICS", expand=True)
    
    def _render_statistics(self, stats: Dict) -> Panel:
        """Render experiment statistics panel."""
        # Get experiment details
        exp = self.storage.get_experiment(self.experiment_id)
        model_a = exp.get('config', {}).get('agent_a_model', 'Unknown')
        model_b = exp.get('config', {}).get('agent_b_model', 'Unknown')
        
        # Build content
        content = Text()
        content.append(f"Models: {model_a} ↔ {model_b}\n\n", style="bold")
        
        # Two columns
        left_lines = []
        right_lines = []
        
        # Vocabulary overlap distribution
        left_lines.append("Vocabulary Overlap Distribution:")
        overlap_dist = stats.get('overlap_distribution', {})
        for bucket, label in [
            ('0_20', '0-20%'), ('20_40', '20-40%'), ('40_60', '40-60%'),
            ('60_80', '60-80%'), ('80_100', '80-100%')
        ]:
            count = overlap_dist.get(bucket, 0)
            if overlap_dist and any(overlap_dist.values()):
                bar_len = int(count / max(overlap_dist.values()) * 15)
                bar = "█" * bar_len + "░" * (15 - bar_len)
            else:
                bar = "░" * 15
            left_lines.append(f"{label:>7}: {bar} {count:>3}")
        
        # Message length distribution
        left_lines.append("\nMessage Length Distribution:")
        length_dist = stats.get('length_distribution', {})
        for bucket, label in [
            ('under_50', '<50'), ('50_100', '50-100'),
            ('100_150', '100-150'), ('over_150', '>150')
        ]:
            count = length_dist.get(bucket, 0)
            if length_dist and any(length_dist.values()):
                bar_len = int(count / max(length_dist.values()) * 15)
                bar = "▓" * bar_len + "░" * (15 - bar_len)
            else:
                bar = "░" * 15
            left_lines.append(f"{label:>7}: {bar} {count:>3}")
        
        # Word frequency evolution
        word_changes = stats.get('word_frequency_changes', {})
        right_lines.append("Frequent Words (Early → Late):")
        right_lines.append("")
        
        early_words = word_changes.get('early_words', [])[:5]
        late_words = word_changes.get('late_words', [])[:5]
        
        if early_words:
            right_lines.append("Early: " + ", ".join(f'"{w}"' for w in early_words))
        if late_words:
            right_lines.append("Late:  " + ", ".join(f'"{w}"' for w in late_words))
        
        right_lines.append("\nTop Word Frequency Changes:")
        for word, (start, end) in word_changes.get('top_changes', [])[:8]:
            change = end - start
            arrow = "↑" if change > 0 else "↓"
            right_lines.append(f'"{word}": {start} {arrow} {end} ({change:+d})')
        
        # Combine columns
        max_left = max(len(line) for line in left_lines) if left_lines else 0
        combined_lines = []
        for i in range(max(len(left_lines), len(right_lines))):
            left = left_lines[i] if i < len(left_lines) else ""
            right = right_lines[i] if i < len(right_lines) else ""
            combined_lines.append(f"{left:<{max_left}}    {right}")
        
        content.append("\n".join(combined_lines))
        
        return Panel(content, title="EXPERIMENT STATISTICS", expand=True,
                    style=self.COLORS['text'])
    
    def _render_footer(self) -> Panel:
        """Render footer with controls."""
        footer = Text()
        footer.append("[D]", style="bold")
        footer.append("etach  ", style=self.COLORS['dim'])
        footer.append("[S]", style="bold") 
        footer.append("top experiment", style=self.COLORS['dim'])
        
        return Panel(footer, style=self.COLORS['dim'], expand=True)
    
    # Helper methods
    
    def _make_sparkline(self, values: List[float], width: int = 8) -> str:
        """Create Unicode sparkline from values."""
        if not values:
            return " " * width
            
        # Pad if too few values
        if len(values) < width:
            padding = [values[0]] * (width - len(values)) if values else [0] * width
            values = padding + values
            
        # Resample if too many values
        if len(values) > width:
            step = len(values) / width
            values = [values[int(i * step)] for i in range(width)]
            
        # Normalize to 0-8 range
        min_v = min(values)
        max_v = max(values)
        
        if max_v == min_v:
            return self.SPARKS[4] * width
            
        normalized = [(v - min_v) / (max_v - min_v) for v in values]
        return "".join(self.SPARKS[int(n * 8)] for n in normalized)
    
    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text with ellipsis."""
        if len(text) <= max_len:
            return text
        return text[:max_len-1] + "…"
    
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration as human-readable string."""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def _aggregate_metrics(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Aggregate metrics across active conversations."""
        if not conversations:
            return {}
            
        metrics = {
            'vocabulary_overlap': [],
            'convergence_score': [],
            'avg_message_length': [],
            'type_token_ratio': [],
            'mimicry_score': []
        }
        
        # Collect metrics from each conversation
        for conv in conversations:
            latest = self.storage.get_latest_turn_metrics(conv['conversation_id'])
            if latest:
                for key in metrics:
                    if key in latest:
                        metrics[key].append(latest[key])
        
        # Calculate aggregates
        aggregated = {}
        for key, values in metrics.items():
            if values:
                aggregated[key] = sum(values) / len(values)
        
        # Count thresholds
        aggregated['high_convergence_count'] = sum(
            1 for conv in conversations 
            if self.storage.get_latest_turn_metrics(conv['conversation_id']) 
            and self.storage.get_latest_turn_metrics(conv['conversation_id']).get('convergence_score', 0) > 0.8
        )
        
        aggregated['short_message_count'] = sum(
            1 for conv in conversations
            if self.storage.get_latest_turn_metrics(conv['conversation_id'])
            and self.storage.get_latest_turn_metrics(conv['conversation_id']).get('avg_message_length', 100) < 50
        )
        
        aggregated['high_mimicry_count'] = sum(
            1 for conv in conversations
            if self.storage.get_latest_turn_metrics(conv['conversation_id'])
            and self.storage.get_latest_turn_metrics(conv['conversation_id']).get('mimicry_score', 0) > 0.7
        )
        
        return aggregated
    
    def stop(self):
        """Stop the dashboard."""
        self.running = False


async def run_dashboard(experiment_id: str):
    """Run the experiment dashboard."""
    dashboard = ExperimentDashboard(experiment_id)
    await dashboard.run()
    
    # Return status to caller
    return {
        'detached': dashboard.detached,
        'stopped': dashboard.stopped
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        asyncio.run(run_dashboard(sys.argv[1]))
    else:
        print("Usage: python dashboard.py <experiment_id>")