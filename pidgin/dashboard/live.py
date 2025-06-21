"""Live experiment dashboard for real-time monitoring of AI conversations."""

import asyncio
import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque
import statistics

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.columns import Columns
from rich.box import ROUNDED, SIMPLE, HEAVY

# Nord color scheme
NORD_COLORS = {
    "nord0": "#2e3440",   # Polar Night - darkest
    "nord1": "#3b4252",   # Polar Night
    "nord2": "#434c5e",   # Polar Night
    "nord3": "#4c566a",   # Polar Night - comments/subtle
    "nord4": "#d8dee9",   # Snow Storm - main content
    "nord5": "#e5e9f0",   # Snow Storm
    "nord6": "#eceff4",   # Snow Storm - brightest
    "nord7": "#8fbcbb",   # Frost - teal
    "nord8": "#88c0d0",   # Frost - light blue
    "nord9": "#81a1c1",   # Frost - blue
    "nord10": "#5e81ac",  # Frost - dark blue
    "nord11": "#bf616a",  # Aurora - red
    "nord12": "#d08770",  # Aurora - orange
    "nord13": "#ebcb8b",  # Aurora - yellow
    "nord14": "#a3be8c",  # Aurora - green
    "nord15": "#b48ead",  # Aurora - purple
}


class ExperimentDashboard:
    """Real-time dashboard for monitoring Pidgin experiments."""
    
    def __init__(self, db_path: Path, experiment_name: Optional[str] = None,
                 refresh_interval: float = 2.0):
        """Initialize dashboard for monitoring experiments.
        
        Args:
            db_path: Path to experiments database
            experiment_name: Optional specific experiment to monitor
            refresh_interval: Seconds between updates (default 2.0)
        """
        self.db_path = db_path
        self.experiment_name = experiment_name
        self.refresh_interval = refresh_interval
        self.console = Console()
        self.should_exit = False
        self.detached = False
        self.start_time = time.time()
        
        # Sparkline histories for metrics
        self.sparkline_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        
    def connect_db(self) -> sqlite3.Connection:
        """Connect to the experiments database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _make_sparkline(self, values: List[float], width: int = 10) -> str:
        """Create a Unicode sparkline from values."""
        if not values:
            return " " * width
            
        chars = " ▁▂▃▄▅▆▇█"
        min_val = min(values) if values else 0
        max_val = max(values) if values else 0
        
        if max_val == min_val:
            return "▄" * width
            
        # Resample to width if needed
        if len(values) > width:
            indices = [int(i * len(values) / width) for i in range(width)]
            values = [values[i] for i in indices]
        elif len(values) < width:
            # Pad with spaces on left
            values = [min_val] * (width - len(values)) + values
            
        sparkline = ""
        for v in values:
            normalized = (v - min_val) / (max_val - min_val) if max_val != min_val else 0.5
            index = int(normalized * (len(chars) - 1))
            sparkline += chars[index]
            
        return sparkline
    
    def _format_duration(self, td: timedelta) -> str:
        """Format timedelta as human-readable string."""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def _shorten_model_name(self, model: str) -> str:
        """Shorten model names for compact display."""
        # Common abbreviations
        abbreviations = {
            "claude-3-5-sonnet": "Sonnet3.5",
            "claude-3-5-haiku": "Haiku",
            "claude-4-opus": "Opus",
            "claude-4-sonnet": "Sonnet4",
            "gpt-4.1": "GPT-4.1",
            "gpt-4.1-mini": "GPT-Mini",
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "4o-mini",
            "gemini-pro": "Gemini",
            "gemini-flash": "Flash",
        }
        
        for long_name, short_name in abbreviations.items():
            if long_name in model.lower():
                return short_name
        
        # Default: take first 8 chars
        return model[:8]
    
    def create_header(self, experiment_data: Dict[str, Any]) -> Panel:
        """Create header panel with experiment progress."""
        if not experiment_data:
            return Panel("No experiment data", style="red")
        
        name = experiment_data.get('name', 'Unknown')
        total = experiment_data.get('total_conversations', 0)
        completed = experiment_data.get('completed_conversations', 0)
        failed = experiment_data.get('failed_conversations', 0)
        active = experiment_data.get('active_conversations', 0)
        queued = total - completed - failed - active
        
        # Calculate runtime and ETA
        started_at = experiment_data.get('started_at')
        if started_at:
            start_time = datetime.fromisoformat(started_at)
            runtime = datetime.now() - start_time
            runtime_str = self._format_duration(runtime)
            
            # Calculate ETA
            if completed > 0:
                avg_time_per_conv = runtime / completed
                remaining = total - completed - failed
                eta = avg_time_per_conv * remaining
                eta_str = self._format_duration(eta)
            else:
                eta_str = "calculating..."
        else:
            runtime_str = "0m"
            eta_str = "unknown"
        
        # Create progress bar
        pct = (completed / total * 100) if total > 0 else 0
        filled = int(20 * completed / total) if total > 0 else 0
        progress = "█" * filled + "░" * (20 - filled)
        
        # Build header lines
        line1 = f"Experiment: {name} | {progress} {completed}/{total} ({pct:.0f}%) | Runtime: {runtime_str} | ETA: {eta_str}"
        line2 = f"◉ Active: {active}  ◎ Complete: {completed}  ⊗ Failed: {failed}  ◇ Queue: {queued}"
        
        return Panel(
            line1 + "\n" + line2,
            style=NORD_COLORS["nord4"],
            border_style=NORD_COLORS["nord10"]
        )
    
    def create_conversations_panel(self, conversations: List[Dict[str, Any]]) -> Panel:
        """Create active conversations panel with metrics."""
        table = Table(show_header=True, header_style="bold", box=SIMPLE)
        
        # Compact column headers
        table.add_column("ID", style=NORD_COLORS['nord3'], width=6)
        table.add_column("Models", style=NORD_COLORS['nord4'], width=16)
        table.add_column("Turn", style=NORD_COLORS['nord4'], width=8)
        table.add_column("Conv", style=NORD_COLORS['nord13'], width=5)
        table.add_column("VOv", style=NORD_COLORS['nord8'], width=5)
        table.add_column("Len", style=NORD_COLORS['nord4'], width=4)
        table.add_column("Last Message", style=NORD_COLORS['nord4'], no_wrap=False)
        
        if not conversations:
            table.add_row("--", "No active conversations", "--", "--", "--", "--", "Waiting for conversations to start...")
        else:
            for conv in conversations[:12]:  # Show top 12
                conv_id = conv['conversation_id'][-4:] if conv['conversation_id'] else "????"
                
                # Model names
                model_a = self._shorten_model_name(conv.get('agent_a_model', '?'))
                model_b = self._shorten_model_name(conv.get('agent_b_model', '?'))
                models = f"{model_a}⇔{model_b}"
                
                # Turn progress
                turn = conv.get('turn_number', 0)
                max_turns = conv.get('max_turns', 50)
                turn_str = f"{turn}/{max_turns}"
                
                # Metrics - now showing convergence!
                conv_score = conv.get('convergence_score', 0) or 0
                conv_str = f"{int(conv_score * 100)}%"
                
                # Color code convergence
                if conv_score > 0.85:
                    conv_str = f"[{NORD_COLORS['nord11']}]{conv_str}[/]"
                elif conv_score > 0.7:
                    conv_str = f"[{NORD_COLORS['nord13']}]{conv_str}[/]"
                
                vocab_overlap = conv.get('vocabulary_overlap', 0) or 0
                vov_str = f"{int(vocab_overlap * 100)}%"
                
                msg_len = int(conv.get('avg_message_length', 0) or 0)
                
                # Last message preview
                last_msg = conv.get('last_message', '')[:50] + "..." if conv.get('last_message') else "..."
                
                table.add_row(conv_id, models, turn_str, conv_str, vov_str, str(msg_len), last_msg)
        
        return Panel(
            table,
            title="◆ Active Conversations",
            border_style=NORD_COLORS["nord9"],
            box=ROUNDED
        )
    
    def create_metrics_panel(self, conversations: List[Dict[str, Any]]) -> Panel:
        """Create metrics panel with sparklines (only for wide displays)."""
        # Aggregate recent metrics
        conv_scores = []
        vov_scores = []
        ttrs = []
        lengths = []
        
        for conv in conversations:
            if 'convergence_score' in conv and conv['convergence_score'] is not None:
                conv_scores.append(conv['convergence_score'])
            if 'vocabulary_overlap' in conv and conv['vocabulary_overlap'] is not None:
                vov_scores.append(conv['vocabulary_overlap'])
            if 'avg_ttr' in conv and conv['avg_ttr'] is not None:
                ttrs.append(conv['avg_ttr'])
            if 'avg_message_length' in conv and conv['avg_message_length'] is not None:
                lengths.append(conv['avg_message_length'])
        
        # Update sparkline cache
        if conv_scores:
            self.sparkline_cache['convergence'].append(statistics.mean(conv_scores))
        if vov_scores:
            self.sparkline_cache['vov'].append(statistics.mean(vov_scores))
        if ttrs:
            self.sparkline_cache['ttr'].append(statistics.mean(ttrs))
        if lengths:
            self.sparkline_cache['length'].append(statistics.mean(lengths))
        
        # Create display
        lines = ["Metrics (Last 20 Updates)", "─" * 30]
        
        # Convergence sparkline
        conv_spark = self._make_sparkline(list(self.sparkline_cache['convergence']))
        conv_current = self.sparkline_cache['convergence'][-1] if self.sparkline_cache['convergence'] else 0
        lines.append(f"Convergence: {conv_spark} {conv_current:.2f}")
        
        # Vocabulary overlap
        vov_spark = self._make_sparkline(list(self.sparkline_cache['vov']))
        vov_current = self.sparkline_cache['vov'][-1] if self.sparkline_cache['vov'] else 0
        lines.append(f"Vocab Overlap: {vov_spark} {int(vov_current * 100)}%")
        
        # Type-token ratio
        ttr_spark = self._make_sparkline(list(self.sparkline_cache['ttr']))
        ttr_current = self.sparkline_cache['ttr'][-1] if self.sparkline_cache['ttr'] else 0
        lines.append(f"TTR: {ttr_spark} {ttr_current:.2f}")
        
        # Message length
        len_spark = self._make_sparkline(list(self.sparkline_cache['length']))
        len_current = self.sparkline_cache['length'][-1] if self.sparkline_cache['length'] else 0
        lines.append(f"Msg Length: {len_spark} {int(len_current)}")
        
        # Threshold counts
        lines.extend([
            "",
            "Current Thresholds:",
            f"Conv > 80%: {sum(1 for c in conversations if (c.get('convergence_score') or 0) > 0.8)}",
            f"Len < 50: {sum(1 for c in conversations if (c.get('avg_message_length') or 100) < 50)}",
            f"VOv > 70%: {sum(1 for c in conversations if (c.get('vocabulary_overlap') or 0) > 0.7)}",
        ])
        
        return Panel(
            "\n".join(lines),
            title="◇ Metrics",
            border_style=NORD_COLORS["nord7"],
            box=ROUNDED
        )
    
    def create_statistics_panel(self, experiment_data: Dict[str, Any]) -> Panel:
        """Create comprehensive statistics panel."""
        # Get statistics from database
        stats = self._get_experiment_statistics()
        
        # Left column - distributions
        left_lines = []
        
        # Vocabulary overlap distribution
        left_lines.append("Vocabulary Overlap at Turn 50:")
        overlap_dist = stats.get('overlap_distribution', {})
        for range_key in ['0-20', '20-40', '40-60', '60-80', '80-100']:
            count = overlap_dist.get(range_key, 0)
            bar = "█" * int(count / max(overlap_dist.values(), default=1) * 15) if overlap_dist else ""
            left_lines.append(f"{range_key}%: {bar:<15} {count}")
        
        left_lines.append("")
        
        # Message length distribution
        left_lines.append("Message Length Distribution:")
        length_dist = stats.get('length_distribution', {})
        for range_key, label in [('<50', 'Short'), ('50-100', 'Medium'), ('100-150', 'Long'), ('>150', 'V.Long')]:
            count = length_dist.get(range_key, 0)
            bar = "█" * int(count / max(length_dist.values(), default=1) * 10) if length_dist else ""
            left_lines.append(f"{label:<8} {bar:<10} {count}")
        
        # Right column - word frequency evolution
        right_lines = []
        right_lines.append("Word Frequency Evolution:")
        right_lines.append("")
        
        word_changes = stats.get('word_changes', {})
        if word_changes:
            right_lines.append("Turn 1-10:")
            early_words = word_changes.get('early', [])[:8]
            right_lines.append("  " + "  ".join(early_words))
            right_lines.append("")
            right_lines.append("Turn 41-50:")
            late_words = word_changes.get('late', [])[:8]
            right_lines.append("  " + "  ".join(late_words))
            right_lines.append("")
            right_lines.append("Top Changes (count):")
            for word, (early_count, late_count) in word_changes.get('changes', [])[:5]:
                arrow = "↑" if late_count > early_count else "↓"
                right_lines.append(f'  "{word}": {early_count}→{late_count} {arrow}')
        else:
            right_lines.append("Collecting data...")
        
        # Combine columns
        max_left = max(len(line) for line in left_lines)
        combined_lines = []
        for i in range(max(len(left_lines), len(right_lines))):
            left = left_lines[i] if i < len(left_lines) else ""
            right = right_lines[i] if i < len(right_lines) else ""
            combined_lines.append(f"{left:<{max_left}}  {right}")
        
        # Add model info at bottom
        model_a = experiment_data.get('config', {}).get('agent_a_model', '?')
        model_b = experiment_data.get('config', {}).get('agent_b_model', '?')
        combined_lines.extend([
            "",
            f"This Experiment: {self._shorten_model_name(model_a)} ⇔ {self._shorten_model_name(model_b)}"
        ])
        
        return Panel(
            "\n".join(combined_lines),
            title="● Statistics",
            border_style=NORD_COLORS["nord14"],
            box=ROUNDED
        )
    
    def create_footer(self) -> Panel:
        """Create footer with keyboard shortcuts."""
        return Panel(
            "[D]etach the screen            [S]top the experiment",
            style=NORD_COLORS["nord3"],
            box=SIMPLE
        )
    
    def create_layout(self) -> Layout:
        """Create adaptive dashboard layout based on terminal width."""
        layout = Layout()
        width = self.console.width
        
        if width >= 120:
            # Wide layout with side panel
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
                Layout(name="footer", size=1)
            )
            
            # Split body into main and metrics
            layout["body"].split_row(
                Layout(name="main", ratio=3),
                Layout(name="metrics", ratio=1)
            )
            
            # Main area has conversations and statistics
            layout["body"]["main"].split_column(
                Layout(name="conversations", ratio=1),
                Layout(name="statistics", ratio=1)
            )
        else:
            # Narrow layout - vertical stack
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="conversations", size=15),
                Layout(name="statistics", size=20),
                Layout(name="footer", size=1)
            )
        
        return layout
    
    def _get_experiment_data(self) -> Optional[Dict[str, Any]]:
        """Get experiment data from database."""
        try:
            with self.connect_db() as conn:
                if self.experiment_name:
                    query = """
                        SELECT e.*, 
                               COUNT(DISTINCT c.conversation_id) as total_conversations,
                               SUM(CASE WHEN c.status = 'completed' THEN 1 ELSE 0 END) as completed_conversations,
                               SUM(CASE WHEN c.status = 'failed' THEN 1 ELSE 0 END) as failed_conversations,
                               SUM(CASE WHEN c.status = 'running' THEN 1 ELSE 0 END) as active_conversations
                        FROM experiments e
                        LEFT JOIN conversations c ON e.experiment_id = c.experiment_id
                        WHERE e.name = ?
                        GROUP BY e.experiment_id
                    """
                    cursor = conn.execute(query, (self.experiment_name,))
                else:
                    # Get most recent experiment
                    query = """
                        SELECT e.*, 
                               COUNT(DISTINCT c.conversation_id) as total_conversations,
                               SUM(CASE WHEN c.status = 'completed' THEN 1 ELSE 0 END) as completed_conversations,
                               SUM(CASE WHEN c.status = 'failed' THEN 1 ELSE 0 END) as failed_conversations,
                               SUM(CASE WHEN c.status = 'running' THEN 1 ELSE 0 END) as active_conversations
                        FROM experiments e
                        LEFT JOIN conversations c ON e.experiment_id = c.experiment_id
                        GROUP BY e.experiment_id
                        ORDER BY e.created_at DESC
                        LIMIT 1
                    """
                    cursor = conn.execute(query)
                
                row = cursor.fetchone()
                if row:
                    result = dict(row)
                    # Parse config JSON
                    if 'config' in result and result['config']:
                        result['config'] = json.loads(result['config'])
                    return result
        except Exception:
            pass
        return None
    
    def _get_active_conversations(self) -> List[Dict[str, Any]]:
        """Get active conversations with latest metrics."""
        try:
            with self.connect_db() as conn:
                # Get active conversations with their latest metrics
                query = """
                    SELECT c.conversation_id, c.agent_a_model, c.agent_b_model,
                           json_extract(c.config, '$.max_turns') as max_turns, c.status,
                           MAX(tm.turn_number) as turn_number,
                           tm.convergence_score, tm.vocabulary_overlap,
                           AVG(mm2.message_length) as avg_message_length,
                           AVG(mm2.type_token_ratio) as avg_ttr,
                           mm.message as last_message
                    FROM conversations c
                    LEFT JOIN turn_metrics tm ON c.conversation_id = tm.conversation_id
                    LEFT JOIN message_metrics mm2 ON c.conversation_id = mm2.conversation_id
                        AND tm.turn_number = mm2.turn_number
                    LEFT JOIN message_metrics mm ON c.conversation_id = mm.conversation_id
                        AND mm.message_index = (
                            SELECT MAX(message_index) 
                            FROM message_metrics 
                            WHERE conversation_id = c.conversation_id
                        )
                    WHERE c.status IN ('running', 'created')
                    GROUP BY c.conversation_id
                    ORDER BY c.started_at DESC
                """
                
                if self.experiment_name:
                    query = query.replace("WHERE c.status", 
                                        "WHERE c.experiment_id IN (SELECT experiment_id FROM experiments WHERE name = ?) AND c.status")
                    cursor = conn.execute(query, (self.experiment_name,))
                else:
                    cursor = conn.execute(query)
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []
    
    def _get_experiment_statistics(self) -> Dict[str, Any]:
        """Calculate experiment-wide statistics."""
        try:
            with self.connect_db() as conn:
                stats = {}
                
                # Vocabulary overlap distribution at turn 50
                query = """
                    SELECT 
                        CASE 
                            WHEN vocabulary_overlap < 0.2 THEN '0-20'
                            WHEN vocabulary_overlap < 0.4 THEN '20-40'
                            WHEN vocabulary_overlap < 0.6 THEN '40-60'
                            WHEN vocabulary_overlap < 0.8 THEN '60-80'
                            ELSE '80-100'
                        END as range_key,
                        COUNT(*) as count
                    FROM turn_metrics
                    WHERE turn_number = 50
                    GROUP BY range_key
                """
                cursor = conn.execute(query)
                stats['overlap_distribution'] = {row['range_key']: row['count'] for row in cursor.fetchall()}
                
                # Message length distribution
                query = """
                    SELECT 
                        CASE 
                            WHEN message_length < 50 THEN '<50'
                            WHEN message_length < 100 THEN '50-100'
                            WHEN message_length < 150 THEN '100-150'
                            ELSE '>150'
                        END as range_key,
                        COUNT(*) as count
                    FROM message_metrics
                    WHERE turn_number >= 40
                    GROUP BY range_key
                """
                cursor = conn.execute(query)
                stats['length_distribution'] = {row['range_key']: row['count'] for row in cursor.fetchall()}
                
                # Word frequency changes
                early_query = """
                    SELECT word, SUM(frequency) as total_freq
                    FROM word_frequencies
                    WHERE turn_number <= 10
                    GROUP BY word
                    ORDER BY total_freq DESC
                    LIMIT 20
                """
                late_query = """
                    SELECT word, SUM(frequency) as total_freq
                    FROM word_frequencies
                    WHERE turn_number >= 40
                    GROUP BY word
                    ORDER BY total_freq DESC
                    LIMIT 20
                """
                
                cursor = conn.execute(early_query)
                early_words = {row['word']: row['total_freq'] for row in cursor.fetchall()}
                
                cursor = conn.execute(late_query)
                late_words = {row['word']: row['total_freq'] for row in cursor.fetchall()}
                
                # Find biggest changes
                all_words = set(early_words.keys()) | set(late_words.keys())
                changes = []
                for word in all_words:
                    early = early_words.get(word, 0)
                    late = late_words.get(word, 0)
                    if early > 0 or late > 0:
                        changes.append((word, (early, late)))
                
                # Sort by biggest increase
                changes.sort(key=lambda x: x[1][1] - x[1][0], reverse=True)
                
                stats['word_changes'] = {
                    'early': list(early_words.keys())[:10],
                    'late': list(late_words.keys())[:10],
                    'changes': changes[:10]
                }
                
                return stats
        except Exception:
            return {}
    
    def handle_detach(self):
        """Handle detach command (like GNU screen)."""
        self.should_exit = True
        self.detached = True
    
    def handle_stop(self):
        """Handle stop command with confirmation."""
        # Simple confirmation - in real implementation would show dialog
        self.console.print("\n[yellow]Stop experiment? This will end all conversations. (y/N): [/yellow]", end="")
        response = input().strip().lower()
        
        if response == 'y':
            # Stop the experiment
            try:
                from ..experiments.storage import ExperimentStore
                store = ExperimentStore()
                
                # Get experiment ID
                exp_data = self._get_experiment_data()
                if exp_data:
                    exp_id = exp_data.get('experiment_id')
                    if exp_id:
                        store.update_experiment_status(exp_id, 'stopped')
                        self.console.print("[red]Experiment stopped![/red]")
                        self.should_exit = True
            except Exception as e:
                self.console.print(f"[red]Error stopping experiment: {e}[/red]")
    
    async def run(self):
        """Run the dashboard until detached or stopped."""
        from .keyboard_handler import KeyboardHandler
        
        # Set up keyboard handler
        keyboard = KeyboardHandler()
        keyboard.register_handler('d', self.handle_detach)
        keyboard.register_handler('D', self.handle_detach)
        keyboard.register_handler('s', self.handle_stop)
        keyboard.register_handler('S', self.handle_stop)
        
        # Create layout
        layout = self.create_layout()
        
        # Initial loading panel
        loading_panel = Panel(
            Align.center(
                f"◆ Loading experiment data...\n\n[dim]Connecting to database...[/dim]",
                vertical="middle"
            ),
            title="◆ Pidgin Dashboard",
            border_style=NORD_COLORS["nord8"],
            height=10
        )
        
        with keyboard:
            with Live(layout, console=self.console, refresh_per_second=0.5, screen=True) as live:
                # Show loading panel first
                live.update(loading_panel)
                await asyncio.sleep(0.5)
                
                # Start keyboard handler
                keyboard_task = asyncio.create_task(keyboard.handle_input())
                
                try:
                    while not self.should_exit:
                        # Get latest data
                        exp_data = self._get_experiment_data()
                        if not exp_data:
                            live.update(Panel("[red]No experiment found![/red]", style="red"))
                            await asyncio.sleep(self.refresh_interval)
                            continue
                        
                        active_convs = self._get_active_conversations()
                        
                        # Update panels
                        layout["header"].update(self.create_header(exp_data))
                        layout["conversations"].update(self.create_conversations_panel(active_convs))
                        
                        # Update metrics panel if present (wide layout)
                        if self.console.width >= 120:
                            layout["body"]["metrics"].update(self.create_metrics_panel(active_convs))
                        
                        layout["statistics"].update(self.create_statistics_panel(exp_data))
                        layout["footer"].update(self.create_footer())
                        
                        # Update display
                        live.update(layout)
                        
                        # Wait for next update
                        await asyncio.sleep(self.refresh_interval)
                        
                except KeyboardInterrupt:
                    # Ctrl+C = stop
                    self.handle_stop()
                finally:
                    # Cancel keyboard task
                    keyboard_task.cancel()
                    try:
                        await keyboard_task
                    except asyncio.CancelledError:
                        pass
                    
                    if self.detached:
                        self.console.print(f"\n[{NORD_COLORS['nord8']}]◆ Dashboard detached - experiment continues running[/{NORD_COLORS['nord8']}]")
                    else:
                        self.console.print(f"\n[{NORD_COLORS['nord8']}]◆ Dashboard stopped[/{NORD_COLORS['nord8']}]")


def main():
    """Run the dashboard from command line."""
    import sys
    
    db_path = Path("./pidgin_output/experiments/experiments.db")
    experiment_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not db_path.exists():
        print("Database not found!")
        sys.exit(1)
    
    dashboard = ExperimentDashboard(db_path, experiment_name)
    asyncio.run(dashboard.run())


if __name__ == "__main__":
    main()
