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
from rich.progress import Progress, BarColumn, TextColumn
from rich.box import ROUNDED

from .keyboard_handler import KeyboardHandler

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


class MetricHistory:
    """Track metric history for sparklines."""
    
    def __init__(self, max_points: int = 20):
        self.max_points = max_points
        self.values: deque = deque(maxlen=max_points)
    
    def add(self, value: float):
        """Add a value to the history."""
        self.values.append(value)
    
    def sparkline(self) -> str:
        """Generate a sparkline from the values."""
        if not self.values:
            return ""
        
        chars = " ▁▂▃▄▅▆▇█"
        min_val = min(self.values)
        max_val = max(self.values)
        
        if max_val == min_val:
            return "▄" * len(self.values)
        
        sparkline = ""
        for v in self.values:
            index = int((v - min_val) / (max_val - min_val) * (len(chars) - 1))
            sparkline += chars[index]
        
        return sparkline


class ExperimentDashboard:
    """Real-time dashboard for monitoring Pidgin experiments."""
    
    def __init__(self, db_path: Path, refresh_rate: float = 0.25):
        self.db_path = db_path
        self.refresh_rate = refresh_rate
        self.console = Console()
        
        # Metric histories for sparklines
        self.metric_histories: Dict[str, MetricHistory] = defaultdict(lambda: MetricHistory())
        
        # Pattern detection
        self.detected_patterns: List[Dict[str, Any]] = []
        self.pattern_buffer: deque = deque(maxlen=100)
        
        # Live feed
        self.event_feed: deque = deque(maxlen=50)
        
        # Statistics
        self.start_time = time.time()
        self.total_events = 0
        self.total_conversations = 0
        
        # Control states
        self.paused = False
        self.should_exit = False
        self.force_refresh = False
        
    def connect_db(self) -> sqlite3.Connection:
        """Connect to the experiments database."""
        conn = sqlite3.connect(self.db_path, timeout=1.0)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_experiment_status(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Get current experiment status."""
        cursor = conn.cursor()
        
        # Get active experiments
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
    
    def get_active_conversations(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """Get currently active conversations."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.conversation_id, c.experiment_id, c.agent_a_model, c.agent_b_model, 
                c.total_turns, c.started_at, c.completed_at,
                e.name as experiment_name
            FROM conversations c
            JOIN experiments e ON c.experiment_id = e.experiment_id
            WHERE c.completed_at IS NULL OR c.completed_at > datetime('now', '-5 minutes')
            ORDER BY c.started_at DESC
            LIMIT 10
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_metrics(self, conn: sqlite3.Connection) -> Dict[str, float]:
        """Calculate real-time metrics."""
        cursor = conn.cursor()
        
        metrics = {}
        
        # Convergence metrics
        cursor.execute("""
            SELECT AVG(convergence_score) as avg_convergence
            FROM turns
            WHERE timestamp > datetime('now', '-1 minute')
        """)
        result = cursor.fetchone()
        metrics["convergence"] = result["avg_convergence"] if result["avg_convergence"] else 0.0
        
        # Response times
        cursor.execute("""
            SELECT 
                AVG(response_time_ms) as avg_response_time,
                MIN(response_time_ms) as min_response_time,
                MAX(response_time_ms) as max_response_time
            FROM turns
            WHERE timestamp > datetime('now', '-1 minute')
        """)
        result = cursor.fetchone()
        if result:
            metrics["avg_response_time"] = result["avg_response_time"] or 0
            metrics["min_response_time"] = result["min_response_time"] or 0
            metrics["max_response_time"] = result["max_response_time"] or 0
        
        # Token counts (using word count as proxy)
        cursor.execute("""
            SELECT 
                AVG(word_count) as avg_tokens,
                SUM(word_count) as total_tokens
            FROM turns
            WHERE timestamp > datetime('now', '-1 minute')
        """)
        result = cursor.fetchone()
        if result:
            metrics["avg_tokens"] = result["avg_tokens"] or 0
            metrics["total_tokens"] = result["total_tokens"] or 0
        
        # Turn rate
        cursor.execute("""
            SELECT COUNT(*) as turns_per_minute
            FROM turns
            WHERE timestamp > datetime('now', '-1 minute')
        """)
        result = cursor.fetchone()
        metrics["turns_per_minute"] = result["turns_per_minute"] if result else 0
        
        return metrics
    
    def detect_patterns(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """Detect interesting patterns in conversations."""
        patterns = []
        cursor = conn.cursor()
        
        # High convergence detection
        cursor.execute("""
            SELECT 
                c.conversation_id, c.agent_a_model, c.agent_b_model, 
                MAX(t.convergence_score) as max_convergence,
                AVG(t.convergence_score) as avg_convergence,
                COUNT(t.turn_number) as turn_count
            FROM conversations c
            JOIN turns t ON c.conversation_id = t.conversation_id
            WHERE t.timestamp > datetime('now', '-5 minutes')
            GROUP BY c.conversation_id
            HAVING max_convergence > 0.8
        """)
        for row in cursor.fetchall():
            patterns.append({
                "type": "high_convergence",
                "severity": "warning" if row["max_convergence"] > 0.9 else "info",
                "message": f"High convergence ({row['max_convergence']:.2f}) between {row['agent_a_model']} and {row['agent_b_model']}",
                "data": dict(row)
            })
        
        # Rapid turn exchanges
        cursor.execute("""
            SELECT 
                conversation_id,
                COUNT(*) as turn_count,
                AVG(response_time_ms) as avg_response
            FROM turns
            WHERE timestamp > datetime('now', '-1 minute')
            GROUP BY conversation_id
            HAVING turn_count > 20
        """)
        for row in cursor.fetchall():
            patterns.append({
                "type": "rapid_exchange",
                "severity": "info",
                "message": f"Rapid turn exchange: {row['turn_count']} turns/min, {row['avg_response']:.0f}ms avg",
                "data": dict(row)
            })
        
        # Token explosion (using word count)
        cursor.execute("""
            SELECT 
                conversation_id,
                MAX(word_count) as max_words,
                AVG(word_count) as avg_words
            FROM turns
            WHERE timestamp > datetime('now', '-1 minute')
            GROUP BY conversation_id
            HAVING max_words > 500
        """)
        for row in cursor.fetchall():
            patterns.append({
                "type": "token_explosion",
                "severity": "warning",
                "message": f"High word count: {row['max_words']} words in single turn",
                "data": dict(row)
            })
        
        # Emoji density pattern
        cursor.execute("""
            SELECT 
                conversation_id,
                AVG(emoji_density) as avg_emoji_density,
                MAX(emoji_density) as max_emoji_density
            FROM turns
            WHERE timestamp > datetime('now', '-5 minutes')
            GROUP BY conversation_id
            HAVING avg_emoji_density > 0.1
        """)
        for row in cursor.fetchall():
            patterns.append({
                "type": "high_emoji_usage",
                "severity": "info",
                "message": f"High emoji density: {row['avg_emoji_density']:.2f} emojis/word average",
                "data": dict(row)
            })
        
        return patterns
    
    def get_recent_events(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """Get recent events from the database."""
        cursor = conn.cursor()
        
        events = []
        
        # Get recent turns as events
        cursor.execute("""
            SELECT 
                t.conversation_id,
                t.turn_number,
                t.speaker,
                t.word_count,
                t.timestamp,
                c.agent_a_model,
                c.agent_b_model
            FROM turns t
            JOIN conversations c ON t.conversation_id = c.conversation_id
            ORDER BY t.timestamp DESC
            LIMIT 20
        """)
        
        for row in cursor.fetchall():
            events.append({
                "type": "turn_complete",
                "data": {
                    "conversation_id": row["conversation_id"],
                    "speaker": row["speaker"],
                    "token_count": row["word_count"],
                    "model_a": row["agent_a_model"],
                    "model_b": row["agent_b_model"]
                },
                "timestamp": row["timestamp"]
            })
        
        # Get recent conversation starts
        cursor.execute("""
            SELECT 
                conversation_id,
                agent_a_model,
                agent_b_model,
                started_at
            FROM conversations
            WHERE started_at > datetime('now', '-10 minutes')
            ORDER BY started_at DESC
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            events.append({
                "type": "conversation_start",
                "data": {
                    "conversation_id": row["conversation_id"],
                    "model_a": row["agent_a_model"],
                    "model_b": row["agent_b_model"]
                },
                "timestamp": row["started_at"]
            })
        
        # Get recent conversation ends
        cursor.execute("""
            SELECT 
                conversation_id,
                total_turns,
                completed_at
            FROM conversations
            WHERE completed_at > datetime('now', '-10 minutes')
                AND completed_at IS NOT NULL
            ORDER BY completed_at DESC
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            events.append({
                "type": "conversation_end",
                "data": {
                    "conversation_id": row["conversation_id"],
                    "turn_count": row["total_turns"]
                },
                "timestamp": row["completed_at"]
            })
        
        # Sort all events by timestamp
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return events[:20]  # Return top 20 most recent
    
    def create_status_panel(self, status: Dict[str, Any]) -> Panel:
        """Create the status panel."""
        stats = status.get("stats", {})
        
        content = Table(show_header=False, box=None, padding=(0, 1))
        content.add_column("Label", style=f"[{NORD_COLORS['nord3']}]")
        content.add_column("Value", style=f"[{NORD_COLORS['nord4']}]")
        
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
        table.add_column("ID", style=f"[{NORD_COLORS['nord3']}]", width=8)
        table.add_column("Models", style=f"[{NORD_COLORS['nord4']}]")
        table.add_column("Turns", style=f"[{NORD_COLORS['nord13']}]", width=6)
        table.add_column("Duration", style=f"[{NORD_COLORS['nord8']}]", width=10)
        
        for conv in conversations[:8]:
            conv_id = conv["conversation_id"][:8] if conv["conversation_id"] else "N/A"
            models = f"{conv['agent_a_model']} ↔ {conv['agent_b_model']}"
            turns = str(conv.get("total_turns", 0))
            
            if conv["started_at"]:
                start = datetime.fromisoformat(conv["started_at"])
                duration = datetime.now() - start
                duration_str = f"{duration.seconds//60}m {duration.seconds%60}s"
            else:
                duration_str = "N/A"
            
            table.add_row(conv_id, models, turns, duration_str)
        
        return Panel(
            table,
            title="[bold]◇ Active Conversations",
            border_style=NORD_COLORS["nord9"],
            box=ROUNDED
        )
    
    def create_metrics_panel(self, metrics: Dict[str, float]) -> Panel:
        """Create the metrics panel with sparklines."""
        grid = Table(show_header=True, box=None)
        grid.add_column("Metric", style=f"[{NORD_COLORS['nord3']}]", width=20)
        grid.add_column("Value", style=f"[{NORD_COLORS['nord4']}]", width=15)
        grid.add_column("Trend", style=f"[{NORD_COLORS['nord8']}]", width=20)
        
        # Update histories
        for key, value in metrics.items():
            self.metric_histories[key].add(value)
        
        # Convergence
        conv = metrics.get("convergence", 0)
        conv_color = NORD_COLORS["nord14"] if conv < 0.7 else NORD_COLORS["nord13"] if conv < 0.85 else NORD_COLORS["nord11"]
        grid.add_row(
            "◆ Convergence",
            f"[{conv_color}]{conv:.3f}[/{conv_color}]",
            self.metric_histories["convergence"].sparkline()
        )
        
        # Response time
        avg_resp = metrics.get("avg_response_time", 0)
        resp_color = NORD_COLORS["nord14"] if avg_resp < 1000 else NORD_COLORS["nord13"] if avg_resp < 2000 else NORD_COLORS["nord11"]
        grid.add_row(
            "⟐ Avg Response",
            f"[{resp_color}]{avg_resp:.0f}ms[/{resp_color}]",
            self.metric_histories["avg_response_time"].sparkline()
        )
        
        # Tokens
        avg_tokens = metrics.get("avg_tokens", 0)
        grid.add_row(
            "◈ Avg Tokens",
            f"{avg_tokens:.0f}",
            self.metric_histories["avg_tokens"].sparkline()
        )
        
        # Turn rate
        turn_rate = metrics.get("turns_per_minute", 0)
        grid.add_row(
            "↔ Turns/min",
            f"{turn_rate}",
            self.metric_histories["turns_per_minute"].sparkline()
        )
        
        return Panel(
            grid,
            title="[bold]○ Real-time Metrics",
            border_style=NORD_COLORS["nord7"],
            box=ROUNDED
        )
    
    def create_insights_panel(self, patterns: List[Dict[str, Any]]) -> Panel:
        """Create the insights panel showing detected patterns."""
        content = Table(show_header=False, box=None)
        content.add_column("Icon", width=2)
        content.add_column("Pattern", style=f"[{NORD_COLORS['nord4']}]")
        
        if not patterns:
            content.add_row("◇", "[dim]No patterns detected[/dim]")
        else:
            for pattern in patterns[-10:]:  # Show last 10
                icon = "▲" if pattern["severity"] == "warning" else "◆"
                color = NORD_COLORS["nord11"] if pattern["severity"] == "warning" else NORD_COLORS["nord8"]
                content.add_row(
                    f"[{color}]{icon}[/{color}]",
                    pattern["message"]
                )
        
        return Panel(
            content,
            title="[bold]● Pattern Insights",
            border_style=NORD_COLORS["nord15"],
            box=ROUNDED
        )
    
    def create_feed_panel(self, events: List[Dict[str, Any]]) -> Panel:
        """Create the live event feed panel."""
        content = Table(show_header=False, box=None)
        content.add_column("Time", style=f"[{NORD_COLORS['nord3']}]", width=8)
        content.add_column("Event", style=f"[{NORD_COLORS['nord4']}]")
        
        for event in events[:15]:  # Show last 15
            timestamp = datetime.fromisoformat(event["timestamp"])
            time_str = timestamp.strftime("%H:%M:%S")
            
            # Format event based on type
            if event["type"] == "turn_complete":
                speaker = event["data"].get("speaker", "Unknown")
                tokens = event["data"].get("token_count", 0)
                event_str = f"→ {speaker}: {tokens} tokens"
            elif event["type"] == "conversation_start":
                models = f"{event['data'].get('model_a', '?')} ↔ {event['data'].get('model_b', '?')}"
                event_str = f"▶ Started: {models}"
            elif event["type"] == "conversation_end":
                event_str = f"■ Ended after {event['data'].get('turn_count', 0)} turns"
            else:
                event_str = f"◇ {event['type']}"
            
            content.add_row(time_str, event_str)
        
        return Panel(
            content,
            title="[bold]▶ Live Feed",
            border_style=NORD_COLORS["nord12"],
            box=ROUNDED
        )
    
    def create_layout(self) -> Layout:
        """Create the dashboard layout."""
        layout = Layout()
        
        # Create the main structure
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Split body into panels
        layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="center", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        # Left column
        layout["left"].split_column(
            Layout(name="status", size=8),
            Layout(name="insights")
        )
        
        # Center column
        layout["center"].split_column(
            Layout(name="conversations", ratio=1),
            Layout(name="metrics", ratio=1)
        )
        
        # Right column stays as feed
        
        return layout
    
    def create_header(self) -> Panel:
        """Create the header panel."""
        title = Text("◆ Pidgin Live Dashboard", style="bold", justify="center")
        subtitle = Text("Real-time AI Conversation Monitoring", style=f"[{NORD_COLORS['nord3']}]", justify="center")
        
        return Panel(
            Align.center(title + "\n" + subtitle),
            border_style=NORD_COLORS["nord10"],
            box=ROUNDED
        )
    
    def create_footer(self) -> Panel:
        """Create the footer panel."""
        shortcuts = "◆ [q]uit  ◇ [e]xport  ○ [r]efresh  ● [p]ause"
        if self.paused:
            shortcuts += f"  [{NORD_COLORS['nord13']}]⏸ PAUSED[/{NORD_COLORS['nord13']}]"
        return Panel(
            Text(shortcuts, justify="center", style=f"[{NORD_COLORS['nord3']}]"),
            border_style=NORD_COLORS["nord2"],
            box=ROUNDED
        )
    
    async def update_dashboard(self, layout: Layout):
        """Update all dashboard components."""
        if self.paused and not self.force_refresh:
            # Just update the footer to show paused state
            layout["footer"].update(self.create_footer())
            return
            
        try:
            with self.connect_db() as conn:
                # Get data
                status = self.get_experiment_status(conn)
                conversations = self.get_active_conversations(conn)
                metrics = self.get_metrics(conn)
                patterns = self.detect_patterns(conn)
                events = self.get_recent_events(conn)
                
                # Update event counter
                self.total_events = len(events)
                
                # Update panels
                layout["header"].update(self.create_header())
                layout["status"].update(self.create_status_panel(status))
                layout["conversations"].update(self.create_conversations_panel(conversations))
                layout["metrics"].update(self.create_metrics_panel(metrics))
                layout["insights"].update(self.create_insights_panel(patterns))
                layout["right"].update(self.create_feed_panel(events))
                layout["footer"].update(self.create_footer())
                
                # Clear force refresh flag
                self.force_refresh = False
                
        except Exception as e:
            # Show error gracefully
            error_panel = Panel(
                f"[{NORD_COLORS['nord11']}]Error: {str(e)}[/{NORD_COLORS['nord11']}]",
                title="◆ Connection Error",
                border_style=NORD_COLORS["nord11"]
            )
            layout["body"].update(error_panel)
    
    def export_data(self):
        """Export dashboard data to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = Path(f"dashboard_export_{timestamp}.json")
        
        try:
            with self.connect_db() as conn:
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "status": self.get_experiment_status(conn),
                    "conversations": self.get_active_conversations(conn),
                    "metrics": self.get_metrics(conn),
                    "patterns": self.detect_patterns(conn),
                    "events": self.get_recent_events(conn)
                }
                
                with open(export_path, "w") as f:
                    json.dump(data, f, indent=2)
                
                self.console.print(f"[{NORD_COLORS['nord14']}]◆ Data exported to {export_path}[/{NORD_COLORS['nord14']}]")
        
        except Exception as e:
            self.console.print(f"[{NORD_COLORS['nord11']}]◆ Export failed: {e}[/{NORD_COLORS['nord11']}]")
    
    def handle_quit(self):
        """Handle quit command."""
        self.should_exit = True
        
    def handle_export(self):
        """Handle export command."""
        self.export_data()
        
    def handle_pause(self):
        """Handle pause/unpause command."""
        self.paused = not self.paused
        
    def handle_refresh(self):
        """Handle force refresh command."""
        self.force_refresh = True
        
    async def run(self):
        """Run the dashboard."""
        layout = self.create_layout()
        
        # Set up keyboard handler
        keyboard = KeyboardHandler()
        keyboard.register_handler('q', self.handle_quit)
        keyboard.register_handler('e', self.handle_export)
        keyboard.register_handler('p', self.handle_pause)
        keyboard.register_handler('r', self.handle_refresh)
        
        with keyboard:
            with Live(layout, console=self.console, refresh_per_second=4, screen=True) as live:
                try:
                    # Start keyboard handler task
                    keyboard_task = asyncio.create_task(keyboard.handle_input())
                    
                    while not self.should_exit:
                        await self.update_dashboard(layout)
                        await asyncio.sleep(self.refresh_rate)
                        
                    # Cancel keyboard task
                    keyboard_task.cancel()
                    try:
                        await keyboard_task
                    except asyncio.CancelledError:
                        pass
                        
                except KeyboardInterrupt:
                    pass
                finally:
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