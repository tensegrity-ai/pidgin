"""System monitor that reads from JSONL files and displays errors."""

import asyncio
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from ..cli.constants import (
    NORD_BLUE,
    NORD_CYAN,
    NORD_DARK,
    NORD_GREEN,
    NORD_LIGHT,
    NORD_ORANGE,
    NORD_RED,
    NORD_YELLOW,
)
from ..constants import ConversationStatus
from ..experiments.state_builder import get_state_builder
from ..io.logger import get_logger
from ..io.paths import get_experiments_dir

logger = get_logger("monitor")
console = Console()

# Monitor refresh settings
REFRESH_INTERVAL_SECONDS = 1
LIVE_REFRESH_PER_SECOND = 0.5  # How often Rich Live updates the display
ERROR_RETRY_DELAY_SECONDS = 5  # Wait time after errors before retrying

# Display settings
# PANEL_WIDTH will be dynamically calculated based on terminal width


class Monitor:
    """Monitor system state from JSONL files with error tracking."""

    def __init__(self, console_instance=None):
        self.exp_base = get_experiments_dir()
        self.running = True
        self.state_builder = get_state_builder()
        self.refresh_count = 0
        self.no_output_dir = False
        self.console = console_instance or console  # Use provided console or default

        # Check if experiments directory exists
        if not self.exp_base.exists():
            self.no_output_dir = True

    def get_panel_width(self) -> int:
        """Calculate panel width based on current terminal size.

        This method is called every time a panel is created, allowing
        the monitor to automatically adapt to terminal resizing.

        Returns:
            Panel width constrained between 60 and 150 characters
        """
        terminal_width = self.console.size.width
        # Leave some margin for borders and scrollbars
        # Minimum width of 60, maximum of 150 for readability
        return max(60, min(terminal_width - 4, 150))

    async def run(self):
        """Run the monitor loop."""
        # Clear screen initially
        console.clear()

        with Live(
            self.build_display(), refresh_per_second=LIVE_REFRESH_PER_SECOND
        ) as live:
            while self.running:
                try:
                    # Check if directory has been created
                    if self.no_output_dir and self.exp_base.exists():
                        self.no_output_dir = False
                        logger.info(f"Experiments directory created: {self.exp_base}")

                    # Check for quit
                    # Note: In a real implementation, we'd handle keyboard input
                    # For now, just update display
                    self.refresh_count += 1
                    live.update(self.build_display())
                    await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

                except KeyboardInterrupt:
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"Monitor error: {e}")
                    await asyncio.sleep(
                        ERROR_RETRY_DELAY_SECONDS
                    )  # Wait longer on error

    def build_display(self) -> Group:
        """Build the display as a group of panels."""
        # Always build header first
        header = self.build_header()

        # If no output directory, show a helpful message
        if self.no_output_dir or not self.exp_base.exists():
            logger.debug(
                f"Showing no experiments message. no_output_dir={self.no_output_dir}, exists={self.exp_base.exists()}"
            )
            message_panel = Panel(
                f"[{NORD_YELLOW}]No experiments directory found at:[/{NORD_YELLOW}]\n\n"
                f"[{NORD_LIGHT}]{self.exp_base}[/{NORD_LIGHT}]\n\n"
                f"[{NORD_DARK}]Run 'pidgin run' to create your first experiment.[/{NORD_DARK}]",
                title="No Experiments Found",
                border_style=NORD_YELLOW,
                width=self.get_panel_width(),
            )
            return Group(header, message_panel)

        # Get current states
        experiments = self.get_experiment_states()

        # Build sections
        errors_panel = self.build_errors_panel()
        experiments_panel = self.build_experiments_panel(experiments)
        conversations_panel = self.build_conversations_panel(experiments)

        # Return a group of panels that will auto-size to their content
        return Group(header, errors_panel, experiments_panel, conversations_panel)

    def _is_recent(self, timestamp: datetime, minutes: int = 5) -> bool:
        """Check if a timestamp is recent."""
        try:
            now = datetime.now(timezone.utc)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return (now - timestamp).total_seconds() < (minutes * 60)
        except (AttributeError, TypeError):
            return False

    def get_experiment_states(self) -> List[Any]:
        """Get all experiment states efficiently."""
        # Return empty list if no output directory
        if self.no_output_dir or not self.exp_base.exists():
            return []

        # Clear cache periodically for fresh data
        self.state_builder.clear_cache()

        # Get all experiments (not just running)
        return self.state_builder.list_experiments(self.exp_base, status_filter=None)

    def build_header(self) -> Panel:
        """Build header panel."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Add a rotating refresh indicator
        refresh_indicators = ["◐", "◓", "◑", "◒"]
        indicator = refresh_indicators[self.refresh_count % len(refresh_indicators)]

        return Panel(
            f"[bold {NORD_BLUE}]◆ PIDGIN MONITOR[/bold {NORD_BLUE}] | [{NORD_DARK}]{timestamp}[/{NORD_DARK}] | [{NORD_GREEN}]{indicator}[/{NORD_GREEN}] | [{NORD_DARK}]Press Ctrl+C to exit[/{NORD_DARK}]",
            style=NORD_CYAN,
            width=self.get_panel_width(),
        )

    def build_experiments_panel(self, experiments: List[Any]) -> Panel:
        """Build experiments overview panel."""
        # Filter to only show running or recently started experiments
        active_experiments = [
            exp for exp in experiments if exp.status in ["running", "created"]
        ]

        if not active_experiments:
            return Panel(
                f"[{NORD_DARK}]No active experiments[/{NORD_DARK}]",
                title="Active Experiments",
                width=self.get_panel_width(),
            )

        table = Table(
            show_header=True, header_style=f"bold {NORD_BLUE}", box=box.ROUNDED
        )
        table.add_column("ID", style=NORD_CYAN, width=24)  # Increased width
        table.add_column("Name", style=NORD_GREEN, width=20)
        table.add_column("Status", width=10)
        table.add_column("Progress", width=15)
        table.add_column("Current", width=15)
        table.add_column("Tokens", width=10)
        table.add_column("Cost", width=8)

        for exp in active_experiments:
            # Calculate progress
            completed, total = exp.progress
            progress_pct = (completed / total * 100) if total > 0 else 0
            progress_str = f"{completed}/{total} ({progress_pct:.0f}%)"

            # Current conversation status (no turn details - those are in conversations panel)
            active_convs = [
                c
                for c in exp.conversations.values()
                if c.status == ConversationStatus.RUNNING
            ]
            pending_convs = [
                c
                for c in exp.conversations.values()
                if c.status == ConversationStatus.CREATED
            ]

            if active_convs:
                current_str = f"{len(active_convs)} active"
            elif pending_convs:
                current_str = f"{len(pending_convs)} pending"
            else:
                current_str = "starting..."

            # Calculate tokens and cost
            # For now, we'll need to read from JSONL files or database to get actual values
            # This is a placeholder - in real implementation we'd aggregate from events
            total_tokens = self._estimate_tokens_for_experiment(exp)
            cost_estimate = self._estimate_cost_for_experiment(exp, total_tokens)

            if total_tokens > 1_000_000:
                tokens_str = f"{total_tokens / 1_000_000:.1f}M"
            elif total_tokens > 1000:
                tokens_str = f"{total_tokens / 1000:.0f}K"
            else:
                tokens_str = str(total_tokens)

            # Determine status color
            status_str = exp.status
            if exp.status == "running":
                status_color = NORD_GREEN
            elif exp.status == "created":
                status_color = NORD_YELLOW
            else:
                status_color = NORD_BLUE

            table.add_row(
                exp.experiment_id[:24],  # Show more of the ID
                exp.name[:20],
                f"[{status_color}]{status_str}[/{status_color}]",
                progress_str,
                current_str,
                tokens_str,
                f"${cost_estimate:.2f}",
            )

        return Panel(
            table,
            title=f"Active Experiments ({len(active_experiments)})",
            width=self.get_panel_width(),
        )

    def build_conversations_panel(self, experiments: List[Any]) -> Panel:
        """Build detailed conversations panel."""
        # Get all conversations from active experiments
        all_convs = []
        for exp in experiments:
            # If experiment is active, show ALL its conversations (running or completed)
            if exp.status in ["running", "created"]:
                for conv in exp.conversations.values():
                    all_convs.append((exp, conv))
            else:
                # For completed experiments, only show recent completions
                for conv in exp.conversations.values():
                    if conv.status == ConversationStatus.RUNNING:
                        all_convs.append((exp, conv))
                    elif conv.completed_at:
                        # Check if completed in last 5 minutes
                        try:
                            now = datetime.now(timezone.utc)
                            completed = conv.completed_at
                            if completed.tzinfo is None:
                                completed = completed.replace(tzinfo=timezone.utc)
                            if (now - completed).total_seconds() < 300:
                                all_convs.append((exp, conv))
                        except (AttributeError, TypeError):
                            pass

        if not all_convs:
            # If no active/recent, show last few completed from any experiment
            for exp in experiments:
                for conv in exp.conversations.values():
                    if conv.status == ConversationStatus.COMPLETED:
                        all_convs.append((exp, conv))

            # Sort by completion time if available
            all_convs.sort(
                key=lambda x: x[1].completed_at
                or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            all_convs = all_convs[:5]  # Show last 5

            if not all_convs:
                return Panel(
                    f"[{NORD_DARK}]No conversations found[/{NORD_DARK}]",
                    title="Conversation Details",
                    width=self.get_panel_width(),
                )

        table = Table(
            show_header=True, header_style=f"bold {NORD_BLUE}", box=box.ROUNDED
        )
        table.add_column("Experiment", style=NORD_CYAN, width=15)
        table.add_column("Conv ID", style=NORD_GREEN, width=12)
        table.add_column("Status", width=10)
        table.add_column("Turn", width=10)
        table.add_column("Models", width=20)
        table.add_column("Convergence", width=12)
        table.add_column("Truncation", width=10)
        table.add_column("Duration", width=10)

        # Sort by status (running first) then by start time
        all_convs.sort(
            key=lambda x: (
                0 if x[1].status == ConversationStatus.RUNNING else 1,
                x[1].started_at or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )

        for exp, conv in all_convs[:10]:  # Show max 10 conversations
            # Status color
            if conv.status == ConversationStatus.RUNNING:
                status_color = NORD_GREEN
                status_str = "running"
            elif conv.status == ConversationStatus.COMPLETED:
                status_color = NORD_BLUE
                status_str = "completed"
            elif conv.status == ConversationStatus.FAILED:
                status_color = NORD_RED
                status_str = "failed"
            else:
                status_color = NORD_YELLOW
                status_str = conv.status

            # Turn progress
            turn_str = f"{conv.current_turn}/{conv.max_turns}"
            turn_pct = (
                (conv.current_turn / conv.max_turns * 100) if conv.max_turns > 0 else 0
            )
            if turn_pct >= 80:
                turn_color = NORD_ORANGE
            elif turn_pct >= 50:
                turn_color = NORD_YELLOW
            else:
                turn_color = NORD_GREEN

            # Models
            models_str = f"{conv.agent_a_model[:8]} ↔ {conv.agent_b_model[:8]}"

            # Convergence
            if conv.last_convergence is not None:
                conv_val = conv.last_convergence
                if conv_val >= 0.8:
                    conv_color = NORD_RED
                    conv_glyph = "▲"
                elif conv_val >= 0.6:
                    conv_color = NORD_ORANGE
                    conv_glyph = "◆"
                else:
                    conv_color = NORD_GREEN
                    conv_glyph = "●"
                conv_str = f"[{conv_color}]{conv_glyph} {conv_val:.2f}[/{conv_color}]"
            else:
                conv_str = "-"

            # Truncation info
            if hasattr(conv, "truncation_count") and conv.truncation_count > 0:
                if conv.truncation_count > 5:
                    trunc_color = NORD_RED
                    trunc_glyph = "⚠"
                elif conv.truncation_count > 2:
                    trunc_color = NORD_ORANGE
                    trunc_glyph = "⚠"
                else:
                    trunc_color = NORD_YELLOW
                    trunc_glyph = "⚠"
                trunc_str = f"[{trunc_color}]{trunc_glyph} {conv.truncation_count}[/{trunc_color}]"
            else:
                trunc_str = "-"

            # Duration
            if conv.started_at:
                # Ensure started_at is timezone-aware
                started = conv.started_at
                if started.tzinfo is None:
                    # Assume UTC for naive timestamps
                    started = started.replace(tzinfo=timezone.utc)

                if conv.completed_at:
                    completed = conv.completed_at
                    if completed.tzinfo is None:
                        completed = completed.replace(tzinfo=timezone.utc)
                    duration = completed - started
                else:
                    # Still running
                    now = datetime.now(timezone.utc)
                    duration = now - started

                # Sanity check - if duration is negative or unreasonably large (>24h),
                # it's likely a timezone issue. Show a placeholder instead.
                total_seconds = int(duration.total_seconds())
                if total_seconds < 0 or total_seconds > 86400:
                    duration_str = "-"
                elif total_seconds < 60:
                    duration_str = f"{total_seconds}s"
                elif total_seconds < 3600:
                    duration_str = f"{total_seconds // 60}m {total_seconds % 60}s"
                else:
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    duration_str = f"{hours}h {minutes}m"
            else:
                duration_str = "-"

            table.add_row(
                exp.name[:15],
                conv.conversation_id[-12:],
                f"[{status_color}]{status_str}[/{status_color}]",
                f"[{turn_color}]{turn_str}[/{turn_color}]",
                models_str,
                conv_str,
                trunc_str,
                duration_str,
            )

        # Determine title based on what we're showing
        has_running = any(c[1].status == ConversationStatus.RUNNING for c in all_convs)
        has_active_exp = any(
            c[0].status in ["running", "created"] for c in all_convs[:10]
        )

        if has_active_exp:
            title = "Experiment Conversations"
        elif has_running:
            title = "Active Conversations"
        else:
            title = "Recent Conversations"

        return Panel(table, title=title, width=self.get_panel_width())

    def tail_file(self, file_path: Path, lines: int = 200) -> List[str]:
        """Efficiently read last N lines from a file."""
        try:
            with open(file_path, "r") as f:
                # Read file in chunks from the end
                file_size = f.seek(0, 2)  # Go to end
                if file_size == 0:
                    return []

                # Start from end and read backwards to find newlines
                chunk_size = 8192
                chunks = []
                lines_found = 0
                pos = file_size

                while pos > 0 and lines_found < lines:
                    chunk_start = max(0, pos - chunk_size)
                    f.seek(chunk_start)
                    chunk = f.read(pos - chunk_start)
                    chunks.append(chunk)
                    lines_found += chunk.count("\n")
                    pos = chunk_start

                # Join chunks and split into lines
                content = "".join(reversed(chunks))
                all_lines = content.split("\n")
                return all_lines[-lines:] if len(all_lines) > lines else all_lines

        except (OSError, IOError) as e:
            logger.debug(f"Error reading {file_path}: {e}")
            return []

    def get_recent_errors(self, minutes: int = 10) -> List[Dict[str, Any]]:
        """Get recent error events from all experiment JSONL files."""
        # Return empty list if no output directory
        if self.no_output_dir or not self.exp_base.exists():
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        errors = []

        try:
            for exp_dir in self.exp_base.iterdir():
                if not exp_dir.is_dir():
                    continue

                # Find JSONL files in experiment directory
                for jsonl_file in exp_dir.glob("*.jsonl"):
                    try:
                        recent_lines = self.tail_file(jsonl_file, lines=500)

                        for line in recent_lines:
                            if not line.strip():
                                continue

                            try:
                                event = json.loads(line)
                                event_type = event.get("event_type", "")

                                # Filter for error events
                                if event_type in ["APIErrorEvent", "ErrorEvent"]:
                                    # Check if event is recent enough
                                    event_time_str = event.get("timestamp", "")
                                    if event_time_str:
                                        try:
                                            event_time = datetime.fromisoformat(
                                                event_time_str.replace("Z", "+00:00")
                                            )
                                            # Make both timezone-aware for comparison
                                            if event_time.tzinfo is None:
                                                event_time = event_time.replace(
                                                    tzinfo=timezone.utc
                                                )
                                            if event_time > cutoff_time:
                                                event["experiment_id"] = exp_dir.name
                                                errors.append(event)
                                        except ValueError:
                                            # Skip events with unparseable timestamps
                                            continue

                            except json.JSONDecodeError:
                                # Skip malformed JSON lines
                                continue

                    except Exception as e:
                        logger.debug(f"Error processing {jsonl_file}: {e}")
                        continue
        except FileNotFoundError:
            # Directory doesn't exist
            return []

        # Sort by timestamp, most recent first
        errors.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return errors
    
    def _truncate_text(self, text: str, max_length: int, suffix: str = "...") -> str:
        """Truncate text to max length with suffix."""
        if len(text) <= max_length:
            return text
        return text[: max_length - len(suffix)] + suffix
    
    def _check_error_resolved(self, error: Dict[str, Any], all_errors: List[Dict[str, Any]]) -> bool:
        """Check if an error was resolved by looking for successful events after it."""
        # This is a simplified check - in a full implementation we'd look for
        # MessageCompleteEvent or similar success events after the error
        error_time = error.get("timestamp", "")
        error_conv = error.get("conversation_id", "")
        
        if not error_time or not error_conv:
            return False
        
        # Check if there are any later errors for the same conversation
        # If not, it might have been resolved
        for other_error in all_errors:
            if (other_error.get("conversation_id") == error_conv and 
                other_error.get("timestamp", "") > error_time):
                return False
        
        # If retryable and has retries, consider it potentially resolved
        if error.get("retryable") and error.get("retry_count", 0) > 0:
            return True
        
        return False

    def build_errors_panel(self) -> Panel:
        """Build panel showing recent errors with detailed information."""
        errors = self.get_recent_errors(minutes=10)

        if not errors:
            return Panel(
                f"[{NORD_GREEN}]● No recent errors[/{NORD_GREEN}]",
                title="Recent Errors (10m)",
                width=self.get_panel_width(),
            )

        # Create a table for detailed error display
        table = Table(show_header=True, header_style="bold", box=None, expand=False)
        table.add_column("Time", style=NORD_DARK, width=8)
        table.add_column("Provider", width=10)
        table.add_column("Type", width=14)
        table.add_column("Context", width=32)
        table.add_column("Status", width=10)

        # Process errors in reverse chronological order (newest first)
        errors.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        
        # Limit to most recent 10 errors for display
        display_errors = errors[:10]
        
        for error in display_errors:
            # Extract fields with defaults
            timestamp_str = error.get("timestamp", "")
            provider = error.get("provider", "")
            error_type = error.get("error_type", "unknown")
            error_message = error.get("error_message", "")
            context = error.get("context", "")
            agent_id = error.get("agent_id", "")
            conversation_id = error.get("conversation_id", "")
            experiment_id = error.get("experiment_id", "")
            retry_count = error.get("retry_count", 0)
            retryable = error.get("retryable", False)
            
            # For ErrorEvent (not APIErrorEvent), provider might not be set
            if not provider:
                # Try to infer from agent_id or error message
                if agent_id:
                    if "gpt" in agent_id.lower():
                        provider = "openai"
                    elif "claude" in agent_id.lower():
                        provider = "anthropic"
                    elif "gemini" in agent_id.lower():
                        provider = "google"
                    elif "grok" in agent_id.lower():
                        provider = "xai"
                    else:
                        provider = "unknown"
                else:
                    provider = "unknown"
            
            # Format timestamp as relative time
            time_str = "unknown"
            if timestamp_str:
                try:
                    event_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if event_time.tzinfo is None:
                        event_time = event_time.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    delta = now - event_time
                    
                    if delta.total_seconds() < 60:
                        time_str = f"{int(delta.total_seconds())}s ago"
                    elif delta.total_seconds() < 3600:
                        time_str = f"{int(delta.total_seconds() / 60)}m ago"
                    else:
                        time_str = f"{int(delta.total_seconds() / 3600)}h ago"
                except:
                    pass
            
            # Infer error type from message if needed
            if error_type == "unknown" and error_message:
                error_msg_lower = error_message.lower()
                if "rate" in error_msg_lower and "limit" in error_msg_lower:
                    error_type = "rate_limit"
                elif "429" in error_message:
                    error_type = "rate_limit"
                elif "auth" in error_msg_lower or "unauthorized" in error_msg_lower:
                    error_type = "auth_error"
                elif "timeout" in error_msg_lower:
                    error_type = "timeout"
                elif "overloaded" in error_msg_lower:
                    error_type = "overloaded"
            
            # Format provider name
            provider_display = provider.replace("Provider", "").title()
            if provider_display == "Unknown":
                provider_display = "?"
            
            # Format error type
            type_display = error_type.replace("_", " ").title()
            if type_display == "Api Error":
                type_display = "API Error"
            
            # Build context string
            context_parts = []
            
            # Add experiment name if available
            if experiment_id:
                # Extract experiment name from ID (format: experiment_id_name_date)
                exp_parts = experiment_id.split("_")
                if len(exp_parts) >= 3:
                    exp_name = exp_parts[2]
                    context_parts.append(self._truncate_text(exp_name, 20))
            
            # Add conversation ID (shortened)
            if conversation_id:
                conv_short = conversation_id.split("_")[-1][:8]
                context_parts.append(f"conv_{conv_short}")
            
            # Add agent info if available
            if agent_id:
                # Try to extract model name from agent_id if it looks like a model
                agent_display = agent_id
                if "gpt" in agent_id or "claude" in agent_id or "gemini" in agent_id:
                    agent_display = agent_id.split("/")[-1]  # Handle provider/model format
                context_parts.append(f"Agent: {self._truncate_text(agent_display, 15)}")
            
            # Add error message snippet if no other context
            if len(context_parts) < 2 and error_message:
                msg_snippet = self._truncate_text(error_message, 30)
                context_parts.append(f'"{msg_snippet}"')
            
            # If we have a context string and room, add it
            if context and len(context_parts) < 3:
                context_parts.append(self._truncate_text(context, 35))
            
            context_str = "\n".join(context_parts[:3]) if context_parts else "No context"
            
            # Format status
            status_str = ""
            status_color = NORD_YELLOW
            
            # Check if error might be resolved
            is_resolved = self._check_error_resolved(error, errors)
            
            if is_resolved:
                status_str = "Resolved"
                status_color = NORD_GREEN
            elif retry_count > 0:
                status_str = f"Retried {retry_count}x"
                status_color = NORD_ORANGE
            elif retryable:
                status_str = "Retryable"
                status_color = NORD_BLUE
            else:
                status_str = "Failed"
                status_color = NORD_RED
            
            # Determine row color based on error type
            if error_type in ["rate_limit", "overloaded"]:
                type_color = NORD_ORANGE
                glyph = "▲"
            elif error_type in ["auth_error", "unauthorized"]:
                type_color = NORD_RED
                glyph = "✗"
            elif "timeout" in error_type:
                type_color = NORD_YELLOW
                glyph = "⏱"
            else:
                type_color = NORD_YELLOW
                glyph = "!"
            
            # Add row to table
            table.add_row(
                time_str,
                f"[{type_color}]{provider_display}[/{type_color}]",
                f"[{type_color}]{glyph} {type_display}[/{type_color}]",
                context_str,
                f"[{status_color}]{status_str}[/{status_color}]"
            )
        
        # Add summary footer if there are more errors
        if len(errors) > 10:
            table.add_row("", "", "", f"[dim]... and {len(errors) - 10} more[/dim]", "")
        
        # Add helpful footer
        if errors:
            table.add_row("", "", "", "", "")
            table.add_row(
                "", 
                "", 
                "", 
                "[dim]View logs for full details[/dim]", 
                ""
            )
        
        title = f"Recent Errors ({len(errors)}) - Last 10m"
        return Panel(table, title=title, width=self.get_panel_width())

    def get_failed_conversations(self) -> List[Dict[str, Any]]:
        """Get failed conversations from manifest files."""
        # Return empty list if no output directory
        if self.no_output_dir or not self.exp_base.exists():
            return []

        failed_convs = []

        try:
            for exp_dir in self.exp_base.iterdir():
                if not exp_dir.is_dir():
                    continue

                manifest_path = exp_dir / "manifest.json"
                if not manifest_path.exists():
                    continue

                try:
                    with open(manifest_path, "r") as f:
                        manifest = json.load(f)

                    for conv_id, conv_data in manifest.get("conversations", {}).items():
                        if conv_data.get("status") == "failed" and conv_data.get(
                            "error"
                        ):
                            failed_convs.append(
                                {
                                    "experiment_id": exp_dir.name,
                                    "conversation_id": conv_id,
                                    "error": conv_data["error"],
                                    "last_updated": conv_data.get("last_updated", ""),
                                }
                            )

                except (json.JSONDecodeError, OSError) as e:
                    logger.debug(f"Error reading manifest {manifest_path}: {e}")
                    continue
        except FileNotFoundError:
            # Directory doesn't exist
            return []

        return failed_convs

    def _estimate_tokens_for_experiment(self, exp: Any) -> int:
        """Estimate total tokens used in an experiment."""
        # Simple estimation based on turns and average message length
        # In a real implementation, we'd read from token usage events
        total_turns = sum(conv.current_turn for conv in exp.conversations.values())
        # Assume average of 150 tokens per message (prompt + response)
        return total_turns * 2 * 150

    def _estimate_cost_for_experiment(self, exp: Any, total_tokens: int) -> float:
        """Estimate cost for an experiment based on tokens and models."""
        # Get primary model from first conversation
        if not exp.conversations:
            return 0.0

        # Use first conversation's model for estimation
        first_conv = next(iter(exp.conversations.values()))
        model = first_conv.agent_a_model.lower()

        # Simple cost estimation (cents per 1K tokens)
        # These are rough estimates - real costs vary by model
        cost_per_1k = {
            "gpt-4": 3.0,
            "gpt-3.5": 0.15,
            "claude": 1.0,
            "qwen": 0.1,  # Local/cheap models
            "llama": 0.1,
            "mixtral": 0.1,
        }

        # Default to cheap model cost if unknown
        rate = 0.1
        for model_key, cost in cost_per_1k.items():
            if model_key in model:
                rate = cost
                break

        # Calculate cost in dollars
        return (total_tokens / 1000) * rate / 100
