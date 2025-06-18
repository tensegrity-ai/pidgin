"""Rate limit monitoring dashboard."""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict, deque

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

# Nord color scheme
NORD_COLORS = {
    "polar_night": {
        "nord0": "#2e3440",  # darkest
        "nord1": "#3b4252",
        "nord2": "#434c5e", 
        "nord3": "#4c566a",  # dim text
    },
    "snow_storm": {
        "nord4": "#d8dee9",  # main content
        "nord5": "#e5e9f0",
        "nord6": "#eceff4",  # brightest
    },
    "frost": {
        "nord7": "#8fbcbb",  # light cyan
        "nord8": "#88c0d0",  # cyan (info)
        "nord9": "#81a1c1",  # light blue
        "nord10": "#5e81ac", # blue (primary)
    },
    "aurora": {
        "nord11": "#bf616a", # red (errors)
        "nord12": "#d08770", # orange
        "nord13": "#ebcb8b", # yellow (warnings)
        "nord14": "#a3be8c", # green (success)
        "nord15": "#b48ead", # purple
    }
}


class RateLimitMonitor:
    """Temporary dashboard for monitoring rate limits and API errors."""
    
    def __init__(self, db_path: Path, refresh_rate: float = 1.0):
        self.db_path = db_path
        self.refresh_rate = refresh_rate
        self.console = Console()
        
        # Track recent errors by provider
        self.recent_errors: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        self.last_messages: Dict[str, str] = {}
        self._cached_errors: List[Dict] = []
        
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def get_active_conversations(self) -> List[Dict]:
        """Get currently running conversations."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT 
                    c.conversation_id,
                    c.agent_a_model,
                    c.agent_b_model,
                    c.status,
                    c.started_at,
                    c.error_message,
                    c.final_convergence_score,
                    e.name as experiment_name,
                    e.experiment_id,
                    (SELECT MAX(turn_number) FROM turns WHERE conversation_id = c.conversation_id) as turns,
                    (SELECT convergence_score FROM turns WHERE conversation_id = c.conversation_id 
                     ORDER BY turn_number DESC LIMIT 1) as current_convergence
                FROM conversations c
                JOIN experiments e ON c.experiment_id = e.experiment_id
                WHERE c.status IN ('running', 'created')
                ORDER BY c.started_at DESC
                LIMIT 20
            """).fetchall()
            return [dict(row) for row in rows]
            
    def get_recent_errors(self) -> List[Dict]:
        """Get recent API errors from both failed conversations and event logs."""
        errors = []
        
        # First get failed conversations from database
        with self.get_connection() as conn:
            # Look for failed conversations in last hour
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            rows = conn.execute("""
                SELECT 
                    c.conversation_id,
                    c.agent_a_model,
                    c.agent_b_model,
                    c.error_message,
                    c.completed_at as timestamp
                FROM conversations c
                WHERE c.status = 'failed' 
                AND c.completed_at > ?
                AND c.error_message IS NOT NULL
                ORDER BY c.completed_at DESC
                LIMIT 20
            """, (one_hour_ago,)).fetchall()
            
            for row in rows:
                errors.append({
                    'conversation_id': row['conversation_id'],
                    'agent_a_model': row['agent_a_model'],
                    'agent_b_model': row['agent_b_model'],
                    'error_message': row['error_message'],
                    'timestamp': row['timestamp'],
                    'source': 'database'
                })
        
        # Also scan recent events.jsonl files for APIErrorEvents
        # This catches rate limit errors that are retried successfully
        import json
        import os
        
        # Look for events in experiment directories
        base_path = self.db_path.parent  # experiments directory
        one_hour_ago_dt = datetime.now() - timedelta(hours=1)
        
        # Scan for recent event files
        for exp_dir in base_path.glob("exp_*/"):
            for conv_dir in exp_dir.glob("*/"):
                events_file = conv_dir / "events.jsonl"
                if events_file.exists():
                    # Check file modification time
                    if datetime.fromtimestamp(os.path.getmtime(events_file)) > one_hour_ago_dt:
                        try:
                            with open(events_file, 'r') as f:
                                for line in f:
                                    try:
                                        event = json.loads(line)
                                        if event.get('event_type') == 'APIErrorEvent':
                                            # Extract conversation ID from path
                                            conv_id = conv_dir.name
                                            errors.append({
                                                'conversation_id': conv_id,
                                                'agent_a_model': event.get('provider', 'unknown'),
                                                'agent_b_model': 'unknown',
                                                'error_message': event.get('error_message', 'Unknown error'),
                                                'timestamp': event.get('timestamp', ''),
                                                'source': 'events'
                                            })
                                    except json.JSONDecodeError:
                                        pass
                        except Exception:
                            pass
        
        # Sort by timestamp and return most recent
        errors.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return errors[:20]
            
    def get_last_messages(self) -> Dict[str, str]:
        """Get last message from each active conversation."""
        with self.get_connection() as conn:
            # Get last turn from each active conversation
            rows = conn.execute("""
                SELECT DISTINCT
                    t.conversation_id,
                    t.message,
                    t.speaker
                FROM turns t
                INNER JOIN (
                    SELECT conversation_id, MAX(turn_number) as max_turn
                    FROM turns
                    GROUP BY conversation_id
                ) latest ON t.conversation_id = latest.conversation_id 
                         AND t.turn_number = latest.max_turn
                WHERE t.conversation_id IN (
                    SELECT conversation_id 
                    FROM conversations 
                    WHERE status = 'running'
                )
            """).fetchall()
            
            messages = {}
            for row in rows:
                # Truncate message to 100 chars
                msg = row['message'][:100] + "..." if len(row['message']) > 100 else row['message']
                messages[row['conversation_id']] = f"[{row['speaker']}] {msg}"
            return messages
            
    def get_experiment_summary(self) -> Dict[str, Dict]:
        """Get summary stats for all active experiments."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT 
                    e.experiment_id,
                    e.name,
                    e.total_conversations,
                    e.completed_conversations,
                    COUNT(CASE WHEN c.status = 'running' THEN 1 END) as running,
                    COUNT(CASE WHEN c.status = 'created' THEN 1 END) as queued
                FROM experiments e
                LEFT JOIN conversations c ON e.experiment_id = c.experiment_id
                WHERE e.status = 'running'
                GROUP BY e.experiment_id
                ORDER BY e.created_at DESC
            """).fetchall()
            
            return {row['experiment_id']: dict(row) for row in rows}
    
    def count_by_provider(self, conversations: List[Dict]) -> Dict[str, int]:
        """Count active conversations by provider."""
        provider_counts = defaultdict(int)
        
        for conv in conversations:
            # Extract provider from model names
            for model in [conv['agent_a_model'], conv['agent_b_model']]:
                if 'claude' in model.lower():
                    provider_counts['anthropic'] += 0.5
                elif 'gpt' in model.lower() or model.lower().startswith('o'):
                    provider_counts['openai'] += 0.5
                elif 'gemini' in model.lower():
                    provider_counts['google'] += 0.5
                elif 'grok' in model.lower():
                    provider_counts['xai'] += 0.5
                    
        return dict(provider_counts)
        
    def create_layout(self) -> Layout:
        """Create dashboard layout."""
        layout = Layout()
        
        # Header, body, footer
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Split body into top and bottom
        layout["body"].split_column(
            Layout(name="top", size=10),
            Layout(name="conversations")
        )
        
        # Split top into rate limits and errors
        layout["top"].split_row(
            Layout(name="rate_limits"),
            Layout(name="errors")
        )
        
        return layout
        
    def render_header(self, experiment_stats: Dict[str, Dict], error_count: int = 0) -> Panel:
        """Render header with title and experiment progress."""
        # Calculate totals
        total_experiments = len(experiment_stats) if experiment_stats else 0
        total_completed = sum(exp['completed_conversations'] for exp in experiment_stats.values()) if experiment_stats else 0
        total_planned = sum(exp['total_conversations'] for exp in experiment_stats.values()) if experiment_stats else 0
        total_running = sum(exp.get('running', 0) for exp in experiment_stats.values()) if experiment_stats else 0
        total_queued = sum(exp.get('queued', 0) for exp in experiment_stats.values()) if experiment_stats else 0
        
        progress = f"{total_completed}/{total_planned}" if total_planned > 0 else "0/0"
        
        # Add error count if any
        error_str = ""
        if error_count > 0:
            error_str = f" | [{NORD_COLORS['aurora']['nord11']}]{error_count} errors[/{NORD_COLORS['aurora']['nord11']}]"
        
        content = Align.center(
            f"[bold {NORD_COLORS['frost']['nord8']}]◆ Rate Limit Monitor[/bold {NORD_COLORS['frost']['nord8']}]\n"
            f"[{NORD_COLORS['snow_storm']['nord4']}]{total_experiments} experiments | "
            f"{progress} completed | "
            f"{total_running} running | "
            f"{total_queued} queued{error_str}[/{NORD_COLORS['snow_storm']['nord4']}]\n"
            f"[{NORD_COLORS['polar_night']['nord3']}]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/{NORD_COLORS['polar_night']['nord3']}]"
        )
        return Panel(content, border_style=NORD_COLORS['frost']['nord8'])
        
    def render_active_conversations(self, conversations: List[Dict]) -> Panel:
        """Render active conversations table."""
        table = Table(title="◇ Active Conversations", expand=True)
        table.add_column("Experiment", style=NORD_COLORS['frost']['nord9'], width=15)
        table.add_column("ID", style=NORD_COLORS['polar_night']['nord3'], width=8)
        table.add_column("Models", style=NORD_COLORS['frost']['nord8'])
        table.add_column("Turns", justify="center", style=NORD_COLORS['aurora']['nord13'])
        table.add_column("Conv", justify="center", style=NORD_COLORS['frost']['nord7'])
        table.add_column("Status", style=NORD_COLORS['aurora']['nord14'])
        table.add_column("Last Message", style=NORD_COLORS['snow_storm']['nord4'])
        
        messages = self.get_last_messages()
        
        if not conversations:
            table.add_row(
                "[dim]No active conversations[/dim]", "", "", "", "", "", ""
            )
        else:
            for conv in conversations[:15]:  # More space now
                exp_name = conv['experiment_name'][:15] if conv['experiment_name'] else "unknown"
                conv_id = conv['conversation_id'].split('_')[-1][:8]
                models = f"{conv['agent_a_model'].split('-')[0]} ↔ {conv['agent_b_model'].split('-')[0]}"
                turns = str(conv['turns'] or 0)
                
                # Format convergence
                conv_score = conv.get('current_convergence', 0) or 0
                conv_str = f"{conv_score:.2f}"
                
                status = conv['status']
                last_msg = messages.get(conv['conversation_id'], "...")
                
                table.add_row(exp_name, conv_id, models, turns, conv_str, status, last_msg)
            
        return Panel(table, border_style=NORD_COLORS['frost']['nord7'])
        
    def render_rate_limits(self, conversations: List[Dict]) -> Panel:
        """Render rate limit status."""
        provider_counts = self.count_by_provider(conversations)
        
        # Rate limits from parallel_runner.py
        limits = {
            "anthropic": 2,
            "openai": 3,
            "google": 2,
            "xai": 2
        }
        
        table = Table(title="◆ Provider Load", expand=True)
        table.add_column("Provider", style=NORD_COLORS['frost']['nord8'])
        table.add_column("Active", justify="center")
        table.add_column("Limit", justify="center")
        table.add_column("Status", justify="center")
        
        for provider, limit in limits.items():
            active = provider_counts.get(provider, 0)
            
            # Color code based on load
            if active >= limit:
                # Bright blue for FULL
                status = f"[bold {NORD_COLORS['frost']['nord9']}]FULL[/bold {NORD_COLORS['frost']['nord9']}]"
                active_str = f"[{NORD_COLORS['frost']['nord9']}]{active:.1f}[/{NORD_COLORS['frost']['nord9']}]"
            elif active >= limit * 0.8:
                status = f"[{NORD_COLORS['aurora']['nord13']}]HIGH[/{NORD_COLORS['aurora']['nord13']}]"
                active_str = f"[{NORD_COLORS['aurora']['nord13']}]{active:.1f}[/{NORD_COLORS['aurora']['nord13']}]"
            else:
                status = f"[{NORD_COLORS['aurora']['nord14']}]OK[/{NORD_COLORS['aurora']['nord14']}]"
                active_str = f"[{NORD_COLORS['aurora']['nord14']}]{active:.1f}[/{NORD_COLORS['aurora']['nord14']}]"
                
            table.add_row(provider.title(), active_str, str(limit), status)
            
        return Panel(table, border_style=NORD_COLORS['frost']['nord10'])
        
    def render_recent_errors(self) -> Panel:
        """Render recent API errors."""
        errors = self._cached_errors
        
        table = Table(title="○ Recent Errors (Last Hour)", expand=True)
        table.add_column("Time", style=NORD_COLORS['polar_night']['nord3'], width=8)
        table.add_column("Models", style=NORD_COLORS['frost']['nord8'])
        table.add_column("Error", style=NORD_COLORS['aurora']['nord11'])
        
        for error in errors[:10]:
            # Parse time
            timestamp = error.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime('%H:%M:%S')
                except:
                    time_str = "unknown"
            else:
                time_str = "unknown"
                
            # Shorten model names or use provider info
            if error['source'] == 'events':
                # For events, we might only have provider
                provider = error['agent_a_model']
                models = f"{provider} API"
            else:
                models = f"{error['agent_a_model'].split('-')[0]} ↔ {error['agent_b_model'].split('-')[0]}"
            
            # Extract error type
            error_msg = error['error_message'] or "Unknown error"
            if "429" in error_msg or "rate" in error_msg.lower():
                error_type = "Rate limit (429)"
            elif "overloaded" in error_msg.lower():
                error_type = "Overloaded"
            elif "token" in error_msg.lower():
                error_type = "Token limit"
            else:
                error_type = error_msg[:30] + "..."
                
            table.add_row(time_str, models, error_type)
            
        if not errors:
            table.add_row("", "No recent errors", "")
            
        return Panel(table, border_style=NORD_COLORS['aurora']['nord11'])
        
    def render_footer(self) -> Panel:
        """Render footer with controls."""
        return Panel(
            f"[bold]Controls:[/bold] [{NORD_COLORS['polar_night']['nord3']}]q[/{NORD_COLORS['polar_night']['nord3']}] quit | [{NORD_COLORS['polar_night']['nord3']}]r[/{NORD_COLORS['polar_night']['nord3']}] refresh",
            border_style=NORD_COLORS['polar_night']['nord3']
        )
        
    async def update_display(self, layout: Layout):
        """Update all panels."""
        try:
            # Get data
            conversations = self.get_active_conversations()
            experiment_stats = self.get_experiment_summary()
            self._cached_errors = self.get_recent_errors()
            
            # Update panels
            layout["header"].update(self.render_header(experiment_stats, len(self._cached_errors)))
            layout["rate_limits"].update(self.render_rate_limits(conversations))
            layout["errors"].update(self.render_recent_errors())
            layout["conversations"].update(self.render_active_conversations(conversations))
            layout["footer"].update(self.render_footer())
        except Exception as e:
            # If there's an error, at least show something
            import traceback
            error_text = f"Error: {str(e)}\n{traceback.format_exc()}"
            # Use the full layout for error display
            layout["header"].update(Panel(error_text[:200], title="Error", border_style="red"))
            layout["rate_limits"].update(Panel("Error - see header", border_style="red"))
            layout["errors"].update(Panel("Error - see header", border_style="red"))
            layout["conversations"].update(Panel(error_text, title="Full Error Trace", border_style="red"))
            layout["footer"].update(Panel("Press Ctrl+C to exit", border_style="red"))
        
    async def run(self):
        """Run the dashboard."""
        layout = self.create_layout()
        
        with Live(layout, console=self.console, refresh_per_second=2) as live:
            while True:
                try:
                    await self.update_display(layout)
                    await asyncio.sleep(self.refresh_rate)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    import traceback
                    self.console.print(f"[red]Error: {e}[/red]")
                    self.console.print(f"[red]{traceback.format_exc()}[/red]")
                    await asyncio.sleep(5)


if __name__ == "__main__":
    import sys
    
    # Default to local experiments database
    db_path = Path("./pidgin_output/experiments/experiments.db")
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
        
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)
        
    monitor = RateLimitMonitor(db_path)
    asyncio.run(monitor.run())