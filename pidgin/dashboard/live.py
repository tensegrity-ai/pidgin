"""Live experiment dashboard for real-time monitoring of AI conversations."""

import asyncio
import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.box import ROUNDED
from rich.prompt import Confirm

from .keyboard_handler import KeyboardHandler
from ..experiments.storage import ExperimentStore

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
    
    def __init__(self, db_path: Path, refresh_rate: float = 2.0, experiment_name: Optional[str] = None):
        self.db_path = db_path
        self.refresh_rate = refresh_rate
        self.experiment_name = experiment_name
        self.console = Console()
        
        # Metric histories for sparklines (keep last 10 values)
        self.metric_histories: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        
        # Statistics
        self.start_time = time.time()
        self.total_events = 0
        self.total_conversations = 0
        
        # Control states
        self.should_exit = False
        self.detached = False  # For detach functionality
        
        # Loading state
        self.conversations_started = False
        self.loading_check_interval = 2.0  # seconds
        self.last_loading_check = 0
        
        # Initialize storage
        self.storage = ExperimentStore(db_path)
        
    def connect_db(self) -> sqlite3.Connection:
        """Connect to the experiments database."""
        conn = sqlite3.connect(self.db_path, timeout=1.0)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_experiment_status(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Get current experiment status."""
        cursor = conn.cursor()
        
        try:
            # Get active experiments
            if self.experiment_name:
                # Filter by specific experiment name
                cursor.execute("""
                    SELECT experiment_id, name, status, created_at, total_conversations, completed_conversations
                    FROM experiments
                    WHERE name = ? AND status IN ('running', 'created')
                    ORDER BY created_at DESC
                """, (self.experiment_name,))
            else:
                cursor.execute("""
                    SELECT experiment_id, name, status, created_at, total_conversations, completed_conversations
                    FROM experiments
                    WHERE status IN ('running', 'created')
                    ORDER BY created_at DESC
                """)
            experiments = cursor.fetchall()
            
            # Get total counts
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT e.experiment_id) as total_experiments,
                    COUNT(DISTINCT c.conversation_id) as total_conversations,
                    SUM(CASE WHEN e.status = 'running' THEN 1 ELSE 0 END) as active_experiments
                FROM experiments e
                LEFT JOIN conversations c ON e.experiment_id = c.experiment_id
            """)
            stats = cursor.fetchone()
            
            return {
                "experiments": [dict(exp) for exp in experiments],
                "stats": dict(stats) if stats else {}
            }
        except sqlite3.OperationalError:
            # Table might not exist yet
            return {
                "experiments": [],
                "stats": {"total_experiments": 0, "total_conversations": 0, "active_experiments": 0}
            }
    
    def get_active_conversations(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """Get currently active conversations with latest metrics."""
        cursor = conn.cursor()
        
        try:
            if self.experiment_name:
                # Filter by specific experiment
                cursor.execute("""
                    SELECT 
                        c.conversation_id, c.experiment_id, c.agent_a_model, c.agent_b_model, 
                        c.total_turns, c.started_at, c.completed_at, c.status,
                        e.name as experiment_name,
                        tm.vocabulary_overlap,
                        tm.convergence_score as latest_convergence,
                        (mm_a.word_count + mm_b.word_count) / 2.0 as avg_message_length
                    FROM conversations c
                    JOIN experiments e ON c.experiment_id = e.experiment_id
                    LEFT JOIN turn_metrics tm ON c.conversation_id = tm.conversation_id
                        AND tm.turn_number = (
                            SELECT MAX(turn_number) FROM turn_metrics 
                            WHERE conversation_id = c.conversation_id
                        )
                    LEFT JOIN message_metrics mm_a ON c.conversation_id = mm_a.conversation_id 
                        AND mm_a.turn_number = tm.turn_number AND mm_a.speaker = 'agent_a'
                    LEFT JOIN message_metrics mm_b ON c.conversation_id = mm_b.conversation_id 
                        AND mm_b.turn_number = tm.turn_number AND mm_b.speaker = 'agent_b'
                    WHERE e.name = ? AND c.status IN ('running', 'created')
                    ORDER BY c.started_at DESC
                    LIMIT 10
                """, (self.experiment_name,))
            else:
                cursor.execute("""
                    SELECT 
                        c.conversation_id, c.experiment_id, c.agent_a_model, c.agent_b_model, 
                        c.total_turns, c.started_at, c.completed_at, c.status,
                        e.name as experiment_name,
                        tm.vocabulary_overlap,
                        tm.convergence_score as latest_convergence,
                        (mm_a.word_count + mm_b.word_count) / 2.0 as avg_message_length
                    FROM conversations c
                    JOIN experiments e ON c.experiment_id = e.experiment_id
                    LEFT JOIN turn_metrics tm ON c.conversation_id = tm.conversation_id
                        AND tm.turn_number = (
                            SELECT MAX(turn_number) FROM turn_metrics 
                            WHERE conversation_id = c.conversation_id
                        )
                    LEFT JOIN message_metrics mm_a ON c.conversation_id = mm_a.conversation_id 
                        AND mm_a.turn_number = tm.turn_number AND mm_a.speaker = 'agent_a'
                    LEFT JOIN message_metrics mm_b ON c.conversation_id = mm_b.conversation_id 
                        AND mm_b.turn_number = tm.turn_number AND mm_b.speaker = 'agent_b'
                    WHERE c.status IN ('running', 'created')
                    ORDER BY c.started_at DESC
                    LIMIT 10
                """)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            return []
    
    def get_sparkline_metrics(self, conn: sqlite3.Connection, conversation_id: str) -> List[Dict[str, float]]:
        """Get last 10 turns of metrics for sparklines."""
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    tm.turn_number,
                    tm.vocabulary_overlap,
                    tm.convergence_score,
                    tm.mimicry_score,
                    AVG(mm.type_token_ratio) as avg_ttr,
                    AVG(mm.word_count) as avg_message_length
                FROM turn_metrics tm
                LEFT JOIN message_metrics mm ON tm.conversation_id = mm.conversation_id 
                    AND tm.turn_number = mm.turn_number
                WHERE tm.conversation_id = ?
                GROUP BY tm.turn_number
                ORDER BY tm.turn_number DESC
                LIMIT 10
            """, (conversation_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            return []
    
    def get_experiment_statistics(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Get experiment statistics for display."""
        cursor = conn.cursor()
        stats = {}
        
        try:
            experiment_filter = ""
            params = []
            if self.experiment_name:
                experiment_filter = """
                    AND tm.conversation_id IN (
                        SELECT c.conversation_id FROM conversations c
                        JOIN experiments e ON c.experiment_id = e.experiment_id
                        WHERE e.name = ?
                    )
                """
                params.append(self.experiment_name)
            
            # Vocabulary overlap distribution at turn 50
            query = f"""
                SELECT 
                    COUNT(*) as count,
                    CASE 
                        WHEN vocabulary_overlap < 0.2 THEN '0-20'
                        WHEN vocabulary_overlap < 0.4 THEN '20-40'
                        WHEN vocabulary_overlap < 0.6 THEN '40-60'
                        WHEN vocabulary_overlap < 0.8 THEN '60-80'
                        ELSE '80-100'
                    END as range
                FROM turn_metrics tm
                WHERE tm.turn_number = 50 {experiment_filter}
                GROUP BY range
            """
            cursor.execute(query, params)
            overlap_dist = {}
            for row in cursor.fetchall():
                overlap_dist[row['range']] = row['count']
            stats['vocabulary_overlap_distribution'] = overlap_dist
            
            # Message length distribution
            query = f"""
                SELECT 
                    COUNT(*) as count,
                    CASE 
                        WHEN word_count < 50 THEN '<50'
                        WHEN word_count < 100 THEN '50-100'
                        WHEN word_count < 150 THEN '100-150'
                        ELSE '>150'
                    END as range
                FROM message_metrics mm
                WHERE mm.conversation_id IN (
                    SELECT DISTINCT conversation_id FROM turn_metrics tm
                    WHERE 1=1 {experiment_filter}
                )
                GROUP BY range
            """
            cursor.execute(query, params)
            length_dist = {}
            for row in cursor.fetchall():
                length_dist[row['range']] = row['count']
            stats['message_length_distribution'] = length_dist
            
            # Word frequency evolution
            early_params = params + [10] if params else [10]
            late_params = params + [40] if params else [40]
            
            # Early turns word frequency
            query = f"""
                SELECT word, SUM(frequency) as total_freq
                FROM word_frequencies wf
                WHERE wf.turn_number <= ? {experiment_filter.replace('tm.', 'wf.')}
                GROUP BY word
                ORDER BY total_freq DESC
                LIMIT 20
            """
            cursor.execute(query, early_params)
            early_words = [(row['word'], row['total_freq']) for row in cursor.fetchall()]
            
            # Late turns word frequency
            query = f"""
                SELECT word, SUM(frequency) as total_freq
                FROM word_frequencies wf
                WHERE wf.turn_number >= ? {experiment_filter.replace('tm.', 'wf.')}
                GROUP BY word
                ORDER BY total_freq DESC
                LIMIT 20
            """
            cursor.execute(query, late_params)
            late_words = [(row['word'], row['total_freq']) for row in cursor.fetchall()]
            
            stats['word_frequency_evolution'] = {
                'early_words': [w[0] for w in early_words[:10]],
                'late_words': [w[0] for w in late_words[:10]]
            }
            
        except sqlite3.OperationalError:
            # Return empty stats if tables don't exist
            stats = {
                'vocabulary_overlap_distribution': {},
                'message_length_distribution': {},
                'word_frequency_evolution': {'early_words': [], 'late_words': []}
            }
        
        return stats
    
    def get_last_message(self, conn: sqlite3.Connection, conversation_id: str) -> Optional[str]:
        """Get the last message from a conversation."""
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT mm.message
                FROM message_metrics mm
                WHERE mm.conversation_id = ?
                ORDER BY mm.turn_number DESC, mm.message_index DESC
                LIMIT 1
            """, (conversation_id,))
            
            result = cursor.fetchone()
            return result['message'] if result else None
        except sqlite3.OperationalError:
            return None
    
    def create_status_panel(self, status: Dict[str, Any]) -> Panel:
        """Create the status panel."""
        stats = status.get("stats", {})
        
        content = Table(show_header=False, box=None, padding=(0, 1))
        content.add_column("Label", style=NORD_COLORS['nord3'])
        content.add_column("Value", style=NORD_COLORS['nord4'])
        
        runtime = timedelta(seconds=int(time.time() - self.start_time))
        
        content.add_row("◆ Runtime", str(runtime))
        content.add_row("◇ Experiments", str(stats.get("total_experiments", 0)))
        content.add_row("○ Conversations", str(stats.get("total_conversations", 0)))
        content.add_row("● Active", str(stats.get("active_experiments", 0)))
        content.add_row("▶ Events/sec", f"{self.total_events / (time.time() - self.start_time):.1f}")
        
        return Panel(
            content,
            title="[bold]◆ Experiment Status",
            border_style=NORD_COLORS["nord10"],
            box=ROUNDED
        )
    
    def create_conversations_panel(self, conversations: List[Dict[str, Any]]) -> Panel:
        """Create the active conversations panel."""
        table = Table(show_header=True, box=None)
        table.add_column("ID", style=NORD_COLORS['nord3'], width=6)
        table.add_column("Models", style=NORD_COLORS['nord4'], width=14)
        table.add_column("Turn", style=NORD_COLORS['nord13'], width=6)
        table.add_column("VOv%", style=NORD_COLORS['nord8'], width=5)
        table.add_column("Len", style=NORD_COLORS['nord8'], width=4)
        table.add_column("Last Message", style=NORD_COLORS['nord4'], no_wrap=False)
        
        if not conversations:
            # No active conversations yet
            table.add_row(
                "-", "Waiting for conversations to start...", "-", "-", "-", "-"
            )
        else:
            with self.connect_db() as conn:
                for conv in conversations[:8]:
                    # Extract conversation ID suffix
                    conv_id = conv["conversation_id"].split('_')[-1][:6] if conv["conversation_id"] else "N/A"
                    
                    # Format models - abbreviated
                    model_a = conv['agent_a_model'][:6] if len(conv['agent_a_model']) > 6 else conv['agent_a_model']
                    model_b = conv['agent_b_model'][:6] if len(conv['agent_b_model']) > 6 else conv['agent_b_model']
                    models = f"{model_a}↔{model_b}"
                    
                    # Format turns as X/Y
                    current_turns = conv.get("total_turns", 0)
                    max_turns = 50  # Default max turns
                    turns = f"{current_turns}/{max_turns}"
                    
                    # Format vocabulary overlap - just percentage
                    vocab_overlap = conv.get("vocabulary_overlap", 0)
                    vocab_str = f"{int(vocab_overlap * 100)}" if vocab_overlap else "-"
                    
                    # Format average message length - just number
                    avg_len = conv.get("avg_message_length", 0)
                    len_str = f"{int(avg_len)}" if avg_len else "-"
                    
                    # Get last message
                    last_msg = self.get_last_message(conn, conv["conversation_id"])
                    if last_msg:
                        # Truncate to 50 chars
                        last_msg = last_msg[:50] + "..." if len(last_msg) > 50 else last_msg
                    else:
                        last_msg = "[dim]waiting...[/dim]"
                    
                    table.add_row(conv_id, models, turns, vocab_str, len_str, last_msg)
        
        return Panel(
            table,
            title="[bold]◇ Active Conversations",
            border_style=NORD_COLORS["nord9"],
            box=ROUNDED
        )
    
    def create_metrics_panel(self, conversations: List[Dict[str, Any]]) -> Panel:
        """Create the metrics panel with sparklines."""
        if not conversations:
            return Panel("No active conversations", title="[bold]○ Metrics", border_style=NORD_COLORS["nord7"])
            
        # Get sparkline data for first active conversation
        with self.connect_db() as conn:
            # Get aggregated metrics across all conversations
            lines = []
            
            for conv in conversations[:1]:  # Focus on first conversation for sparklines
                sparkline_data = self.get_sparkline_metrics(conn, conv['conversation_id'])
                if not sparkline_data:
                    continue
                    
                # Build sparklines for each metric
                metrics_config = [
                    ('vocabulary_overlap', 'Vocabulary Overlap', '%'),
                    ('convergence_score', 'Convergence Score', ''),
                    ('avg_ttr', 'Type-Token Ratio', ''),
                    ('avg_message_length', 'Avg Message Length', ' chars')
                ]
                
                for metric_key, label, suffix in metrics_config:
                    values = [d.get(metric_key, 0) for d in sparkline_data if d.get(metric_key) is not None]
                    if values:
                        # Store in history
                        self.metric_histories[metric_key].extend(values)
                        # Keep only last 10
                        while len(self.metric_histories[metric_key]) > 10:
                            self.metric_histories[metric_key].popleft()
                        
                        # Create sparkline
                        sparkline = self._create_sparkline(list(self.metric_histories[metric_key]))
                        current_val = values[0]  # Most recent
                        
                        if metric_key == 'vocabulary_overlap':
                            display_val = f"{int(current_val * 100)}{suffix}"
                        elif metric_key == 'convergence_score':
                            display_val = f"{current_val:.2f}"
                        elif metric_key == 'avg_ttr':
                            display_val = f"{current_val:.2f}"
                        else:
                            display_val = f"{int(current_val)}{suffix}"
                            
                        lines.append(f"{label:.<25} {sparkline} {display_val:>10}")
                
                break  # Only show sparklines for one conversation
            
            if not lines:
                lines = ["Waiting for metrics data..."]
                
            content = "\n".join(lines)
            
        return Panel(
            content,
            title="[bold]○ Metrics (Last 10 Turns)",
            border_style=NORD_COLORS["nord7"],
            box=ROUNDED
        )
    
    def _create_sparkline(self, values: List[float]) -> str:
        """Create a sparkline from values."""
        if not values:
            return " " * 10
            
        chars = " ▁▂▃▄▅▆▇█"
        min_val = min(values)
        max_val = max(values)
        
        if max_val == min_val:
            return "▄" * 10
            
        sparkline = ""
        for v in values[-10:]:  # Last 10 values
            index = int((v - min_val) / (max_val - min_val) * (len(chars) - 1))
            sparkline += chars[index]
            
        # Pad if needed
        if len(sparkline) < 10:
            sparkline = " " * (10 - len(sparkline)) + sparkline
            
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
    
    def create_loading_panel(self, message: str = "Initializing dashboard...") -> Panel:
        """Create a loading panel with status message."""
        subtitle = "[dim]Connecting to experiment database...[/dim]"
        if self.experiment_name:
            subtitle = f"[dim]Loading experiment: {self.experiment_name}[/dim]"
            
        content = Align.center(
            f"◆ {message}\n\n{subtitle}",
            vertical="middle"
        )
        return Panel(
            content,
            title="◆ Pidgin Dashboard",
            border_style=NORD_COLORS["nord8"],
            height=10
        )
    
    def create_loading_panel_with_progress(self, step: int, total: int = 4) -> Panel:
        """Loading panel with progress indicator."""
        blocks = "░" * total
        filled = "█" * step
        progress = filled + blocks[step:]
        
        messages = [
            "Connecting to database...",
            "Loading experiment configuration...",
            "Checking active conversations...",
            "Ready! Loading complete."
        ]
        
        message = messages[min(step - 1, len(messages) - 1)] if step > 0 else "Initializing..."
        
        content = Align.center(
            f"◆ Loading Experiment Data\n\n{progress}\n\n[dim]{message}[/dim]\n[dim]Step {step}/{total}[/dim]",
            vertical="middle"
        )
        return Panel(content, border_style=NORD_COLORS["nord8"], height=10)
    
    def _check_database(self) -> bool:
        """Check if database exists and is accessible."""
        try:
            with self.connect_db() as conn:
                # Try a simple query to verify database structure
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM experiments LIMIT 1")
            return True
        except:
            return False
    
    def create_statistics_panel(self, stats: Dict[str, Any]) -> Panel:
        """Create the statistics panel."""
        # Create two columns - distributions and word frequency
        left_column = Table(show_header=False, box=None)
        left_column.add_column("Label", style=NORD_COLORS['nord3'])
        left_column.add_column("Value", style=NORD_COLORS['nord4'])
        
        # Calculate average metrics if we have data
        if stats:
            # Vocabulary overlap distribution
            overlap_dist = stats.get('vocabulary_overlap_distribution', {})
            if overlap_dist:
                left_column.add_row("Vocabulary Overlap (Turn 50):", "")
                for range_key in ['0-20', '20-40', '40-60', '60-80', '80-100']:
                    count = overlap_dist.get(range_key, 0)
                    if overlap_dist.values():
                        max_count = max(overlap_dist.values())
                        bar_len = int((count / max_count) * 10) if max_count > 0 else 0
                    else:
                        bar_len = 0
                    bar = "█" * bar_len + "░" * (10 - bar_len)
                    left_column.add_row(f"  {range_key}%:", f"{bar} {count}")
                left_column.add_row("", "")
            
            # Message length stats
            length_dist = stats.get('message_length_distribution', {})
            if length_dist:
                left_column.add_row("Message Length:", "")
                total_messages = sum(length_dist.values())
                if total_messages > 0:
                    avg_under_50 = length_dist.get('<50', 0) / total_messages * 100
                    avg_50_100 = length_dist.get('50-100', 0) / total_messages * 100
                    avg_100_150 = length_dist.get('100-150', 0) / total_messages * 100
                    avg_over_150 = length_dist.get('>150', 0) / total_messages * 100
                    
                    left_column.add_row("  Short (<50):", f"{avg_under_50:.0f}%")
                    left_column.add_row("  Medium (50-100):", f"{avg_50_100:.0f}%")
                    left_column.add_row("  Long (100-150):", f"{avg_100_150:.0f}%")
                    left_column.add_row("  Very Long (>150):", f"{avg_over_150:.0f}%")
        else:
            left_column.add_row("Collecting statistics...", "")
        
        # Word frequency column
        right_column = Table(show_header=False, box=None)
        right_column.add_column("Early", style=NORD_COLORS['nord3'])
        right_column.add_column("→", style=NORD_COLORS['nord4'], width=3)
        right_column.add_column("Late", style=NORD_COLORS['nord8'])
        
        word_evolution = stats.get('word_frequency_evolution', {}) if stats else {}
        early_words = word_evolution.get('early_words', [])
        late_words = word_evolution.get('late_words', [])
        
        if early_words or late_words:
            right_column.add_row("Word Evolution:", "", "")
            # Show top 5 words from each period
            for i in range(min(5, max(len(early_words), len(late_words)))):
                early = early_words[i] if i < len(early_words) else ""
                late = late_words[i] if i < len(late_words) else ""
                right_column.add_row(early, "→", late)
        else:
            right_column.add_row("No word data yet", "", "")
        
        # Combine columns
        from rich.columns import Columns
        content = Columns([left_column, right_column], padding=(0, 2))
        
        return Panel(
            content,
            title="[bold]◆ Statistics",
            border_style=NORD_COLORS["nord14"],
            box=ROUNDED
        )
    
    
    def create_layout(self) -> Layout:
        """Create the dashboard layout."""
        layout = Layout()
        
        # Determine terminal width
        width = self.console.width
        
        if width >= 140:
            # Wide layout with metrics panel
            layout.split_column(
                Layout(name="header", size=4),
                Layout(name="body"),
                Layout(name="footer", size=1)
            )
            
            # Split body into main and metrics
            layout["body"].split_row(
                Layout(name="main", ratio=3),
                Layout(name="metrics", ratio=1)
            )
            
            # Main has conversations and statistics
            layout["body"]["main"].split_column(
                Layout(name="conversations", ratio=1),
                Layout(name="statistics", ratio=1)
            )
        else:
            # Narrow layout - stack vertically
            layout.split_column(
                Layout(name="header", size=4),
                Layout(name="conversations", size=12),
                Layout(name="statistics", size=15),
                Layout(name="footer", size=1)
            )
        
        return layout
    
    def create_header(self, status: Dict[str, Any]) -> Panel:
        """Create the header panel with progress bar."""
        if not status.get("experiments"):
            return Panel("No experiment found", border_style=NORD_COLORS["nord11"])
            
        exp = status["experiments"][0]
        
        # Calculate progress
        total = exp.get('total_conversations', 0)
        completed = exp.get('completed_conversations', 0)
        failed = exp.get('failed_conversations', 0)
        active = len(self.get_active_conversations(self.connect_db()))
        queued = max(0, total - completed - failed - active)
        
        progress = completed / total if total > 0 else 0
        
        # Calculate timing
        if exp.get('started_at'):
            started = datetime.fromisoformat(exp['started_at'])
            runtime = datetime.now() - started
            runtime_str = self._format_duration(runtime)
            
            if completed > 0:
                avg_time = runtime / completed
                eta = avg_time * (total - completed)
                eta_str = self._format_duration(eta)
            else:
                eta_str = "calculating..."
        else:
            runtime_str = "0m"
            eta_str = "unknown"
        
        # Build progress bar with proper block characters
        bar_width = 20
        filled = int(bar_width * progress)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        # Build header text - single line format
        header = f"Experiment: {exp['name']} | {bar} {completed}/{total} ({progress*100:.1f}%) | Runtime: {runtime_str} | ETA: {eta_str}"
        status_line = f"◉ Active: {active}   ◎ Complete: {completed}   ⊗ Failed: {failed}   ◇ Queue: {queued}"
        
        return Panel(
            f"{header}\n{status_line}",
            border_style=NORD_COLORS["nord10"],
            box=ROUNDED
        )
    
    def create_footer(self) -> Panel:
        """Create the footer panel."""
        shortcuts = "[D]etach the screen            [S]top the experiment"
        return Panel(
            Text(shortcuts, justify="center", style=NORD_COLORS['nord3']),
            border_style=NORD_COLORS["nord2"],
            box=ROUNDED
        )
    
    def check_conversations_started(self, conn: sqlite3.Connection) -> bool:
        """Check if any conversations have started producing turns."""
        if self.experiment_name:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM turn_metrics tm
                JOIN conversations c ON tm.conversation_id = c.conversation_id
                JOIN experiments e ON c.experiment_id = e.experiment_id
                WHERE e.name = ?
            """, (self.experiment_name,))
            count = cursor.fetchone()[0]
            return count > 0
        return False
    
    def create_experiment_loading_panel(self) -> Panel:
        """Create a loading panel while waiting for conversations to start."""
        elapsed = time.time() - self.start_time
        
        # Get experiment info if available
        experiment_info = ""
        try:
            with self.connect_db() as conn:
                status = self.get_experiment_status(conn)
                if status["experiments"]:
                    exp = status["experiments"][0]
                    experiment_info = f"""
◇ Experiment: {exp['name']}
○ Total conversations: {exp['total_conversations']}
● Status: {exp['status']}
"""
        except:
            pass
            
        content = f"""[bold]◆ Waiting for Conversations to Start[/bold]

{experiment_info}
◇ Starting conversations...
○ Elapsed: {elapsed:.1f}s

[dim]Conversations will appear as they start producing data[/dim]
[dim]This typically takes 5-10 seconds[/dim]
"""
        
        return Panel(
            Align.center(content, vertical="middle"),
            title="[bold]◆ Loading",
            border_style=NORD_COLORS["nord13"],
            box=ROUNDED
        )
    
    async def update_dashboard(self, layout: Layout):
        """Update all dashboard components."""
        # Check if conversations have started
        current_time = time.time()
        if not self.conversations_started and current_time - self.last_loading_check > self.loading_check_interval:
            self.last_loading_check = current_time
            try:
                with self.connect_db() as conn:
                    self.conversations_started = self.check_conversations_started(conn)
            except:
                pass
                
        # Show loading screen if conversations haven't started
        if not self.conversations_started and time.time() - self.start_time < 30:
            # For layouts with body section
            if "body" in layout._children:
                layout["body"].update(self.create_experiment_loading_panel())
            layout["header"].update(self.create_header({"experiments": []}))
            layout["footer"].update(self.create_footer())
            return
            
        try:
            with self.connect_db() as conn:
                # Get data
                status = self.get_experiment_status(conn)
                conversations = self.get_active_conversations(conn)
                stats = self.get_experiment_statistics(conn)
                
                # Update panels with individual error handling
                try:
                    layout["header"].update(self.create_header(status))
                except Exception as e:
                    layout["header"].update(Panel(f"Header error: {e}", border_style="red"))
                
                try:
                    layout["conversations"].update(self.create_conversations_panel(conversations))
                except Exception as e:
                    layout["conversations"].update(Panel(f"Conversations error: {e}", border_style="red"))
                
                # Update metrics panel if wide layout
                if "metrics" in layout._children or ("body" in layout._children and "metrics" in layout["body"]._children):
                    try:
                        metrics_panel = self.create_metrics_panel(conversations)
                        if "metrics" in layout._children:
                            layout["metrics"].update(metrics_panel)
                        else:
                            layout["body"]["metrics"].update(metrics_panel)
                    except Exception as e:
                        if "metrics" in layout._children:
                            layout["metrics"].update(Panel(f"Metrics error: {e}", border_style="red"))
                        else:
                            layout["body"]["metrics"].update(Panel(f"Metrics error: {e}", border_style="red"))
                
                try:
                    stats_panel = self.create_statistics_panel(stats)
                    if "statistics" in layout._children:
                        layout["statistics"].update(stats_panel)
                    elif "body" in layout._children and "main" in layout["body"]._children:
                        layout["body"]["main"]["statistics"].update(stats_panel)
                except Exception as e:
                    error_panel = Panel(f"Statistics error: {e}", border_style="red")
                    if "statistics" in layout._children:
                        layout["statistics"].update(error_panel)
                    elif "body" in layout._children and "main" in layout["body"]._children:
                        layout["body"]["main"]["statistics"].update(error_panel)
                
                try:
                    layout["footer"].update(self.create_footer())
                except Exception as e:
                    layout["footer"].update(Panel(f"Footer error: {e}", border_style="red"))
                
        except sqlite3.OperationalError as e:
            # Database/table might not exist yet
            waiting_panel = Panel(
                f"[{NORD_COLORS['nord8']}]◆ Waiting for experiment to initialize...\n\n"
                f"The experiment daemon is starting up.\n"
                f"Data will appear momentarily.[/{NORD_COLORS['nord8']}]",
                title="◆ Initializing",
                border_style=NORD_COLORS["nord13"],
                style=NORD_COLORS['nord4']
            )
            if "body" in layout._children:
                layout["body"].update(Align.center(waiting_panel, vertical="middle"))
            else:
                # For narrow layout, update conversations panel
                layout["conversations"].update(waiting_panel)
        except Exception as e:
            # Show error gracefully
            import traceback
            error_detail = traceback.format_exc() if self.console.is_terminal else str(e)
            error_panel = Panel(
                f"[{NORD_COLORS['nord11']}]Error: {str(e)}[/{NORD_COLORS['nord11']}]\n\n"
                f"[{NORD_COLORS['nord3']}]{error_detail}[/{NORD_COLORS['nord3']}]",
                title="◆ Dashboard Error",
                border_style=NORD_COLORS["nord11"]
            )
            if "body" in layout._children:
                layout["body"].update(error_panel)
            else:
                layout["conversations"].update(error_panel)
    
    
        
    def handle_detach(self):
        """Handle detach command (like screen's Ctrl+A D)."""
        self.should_exit = True
        self.detached = True
    
    async def handle_stop(self):
        """Handle stop command with confirmation."""
        # Show confirmation in the console
        self.console.print("\n[yellow]Stop the experiment? This will terminate all running conversations. (y/N)[/yellow] ", end="")
        
        # Wait for user input
        import sys
        response = sys.stdin.read(1).lower()
        
        if response == 'y':
            # Get experiment ID from name
            if self.experiment_name:
                experiment = self.storage.get_experiment_by_name(self.experiment_name)
                if experiment:
                    # Stop the experiment
                    self.storage.stop_experiment(experiment['experiment_id'])
                    self.should_exit = True
                    self.console.print("[red]Experiment stopped.[/red]")
                else:
                    self.console.print("[red]Could not find experiment to stop.[/red]")
            else:
                self.console.print("[red]No experiment name specified.[/red]")
        else:
            self.console.print("[green]Continuing experiment.[/green]")
            # Force refresh to redraw the dashboard
            await self.update_dashboard(self.layout)
        
    async def run(self):
        """Run the dashboard."""
        # Show loading panel immediately
        with Live(self.create_loading_panel(), console=self.console, refresh_per_second=2) as live:
            # Step 1: Check database connection
            await asyncio.sleep(0.1)  # Let Rich render
            live.update(self.create_loading_panel_with_progress(1, 4))
            
            if not self._check_database():
                live.update(Panel(
                    Align.center(
                        "⊗ Database not found!\n\n[dim]Make sure the experiment is running.[/dim]",
                        vertical="middle"
                    ),
                    border_style=NORD_COLORS["nord11"],
                    height=10
                ))
                await asyncio.sleep(3)
                return
            
            # Step 2: Load experiment configuration
            await asyncio.sleep(0.1)
            live.update(self.create_loading_panel_with_progress(2, 4))
            
            # Step 3: Check for active conversations
            await asyncio.sleep(0.1)
            live.update(self.create_loading_panel_with_progress(3, 4))
            
            # Create the actual layout
            self.layout = self.create_layout()
            
            # Step 4: Ready
            live.update(self.create_loading_panel_with_progress(4, 4))
            await asyncio.sleep(0.5)
            
            # Now switch to the main layout
            live.update(self.layout)
            
            # Set up keyboard handler
            keyboard = KeyboardHandler()
            keyboard.register_handler('d', self.handle_detach)
            keyboard.register_handler('D', self.handle_detach)
            keyboard.register_handler('s', lambda: asyncio.create_task(self.handle_stop()))
            keyboard.register_handler('S', lambda: asyncio.create_task(self.handle_stop()))
            
            with keyboard:
                try:
                    # Initial dashboard update
                    await self.update_dashboard(self.layout)
                    
                    # Start keyboard handler task
                    keyboard_task = asyncio.create_task(keyboard.handle_input())
                    
                    # Main dashboard loop
                    while not self.should_exit:
                        await self.update_dashboard(self.layout)
                        await asyncio.sleep(self.refresh_rate)
                        
                    # Cancel keyboard task
                    keyboard_task.cancel()
                    try:
                        await keyboard_task
                    except asyncio.CancelledError:
                        pass
                        
                except KeyboardInterrupt:
                    # Treat Ctrl+C as detach
                    self.should_exit = True
                    self.detached = True
                finally:
                    # Clear screen and show exit message
                    live.stop()
                    if self.detached:
                        self.console.print(f"\n[{NORD_COLORS['nord8']}]◆ Dashboard detached. Run 'pidgin experiment dashboard' to reattach.[/{NORD_COLORS['nord8']}]")
                    else:
                        self.console.print(f"\n[{NORD_COLORS['nord8']}]◆ Dashboard stopped[/{NORD_COLORS['nord8']}]")


def main():
    """Run the dashboard from command line."""
    import sys
    
    # Default to experiments.db in standard location
    db_path = Path("./pidgin_output/experiments/experiments.db")
    
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)
    
    dashboard = ExperimentDashboard(db_path)
    asyncio.run(dashboard.run())


if __name__ == "__main__":
    main()