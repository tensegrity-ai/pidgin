"""Conversation panel building for the monitor."""

import json
from datetime import datetime, timezone
from typing import Any, List

from rich import box
from rich.panel import Panel
from rich.table import Table

from ..cli.constants import (
    NORD_BLUE,
    NORD_CYAN,
    NORD_DARK,
    NORD_GREEN,
    NORD_ORANGE,
    NORD_RED,
    NORD_YELLOW,
)
from ..core.constants import ConversationStatus
from ..io.logger import get_logger

logger = get_logger("conversation_panel_builder")


class ConversationPanelBuilder:
    """Builds conversation display panel for the monitor."""

    def __init__(self, panel_width_getter):
        """Initialize conversation panel builder.

        Args:
            panel_width_getter: Function to get panel width
        """
        self.get_panel_width = panel_width_getter

    def build_conversations_panel(self, experiments: List[Any]) -> Panel:
        """Build detailed conversations panel."""
        # Get all conversations from active experiments
        all_convs = self._collect_conversations(experiments)

        if not all_convs:
            # Try to show last few completed conversations
            all_convs = self._get_recent_completed(experiments)

            if not all_convs:
                return Panel(
                    f"[{NORD_DARK}]No conversations found[/{NORD_DARK}]",
                    title="Conversation Details",
                    width=self.get_panel_width(),
                )

        table = self._build_conversation_table(all_convs)

        # Determine title based on what we're showing
        has_active_exp = any(
            c[0].status in ["running", "created"] for c in all_convs[:10]
        )

        if has_active_exp:
            title = "Experiment Conversations"
        else:
            title = "Recent Conversations"

        return Panel(table, title=title, width=self.get_panel_width())

    def _collect_conversations(self, experiments):
        """Collect conversations from experiments."""
        all_convs = []
        for exp in experiments:
            # If experiment is active, show ALL its conversations
            if exp.status in ["running", "created"]:
                for conv in exp.conversations.values():
                    all_convs.append((exp, conv))
            else:
                # For completed experiments, only show recent completions
                for conv in exp.conversations.values():
                    if conv.status == ConversationStatus.RUNNING:
                        all_convs.append((exp, conv))
                    elif conv.completed_at and self._is_recent(conv.completed_at, 5):
                        all_convs.append((exp, conv))
        return all_convs

    def _get_recent_completed(self, experiments):
        """Get recently completed conversations."""
        all_convs = []
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
        return all_convs[:5]  # Show last 5

    def _build_conversation_table(self, all_convs):
        """Build the conversation table."""
        table = Table(
            show_header=True, header_style=f"bold {NORD_BLUE}", box=box.ROUNDED
        )
        table.add_column("Experiment", style=NORD_CYAN, width=15)
        table.add_column("Conv ID", style=NORD_GREEN, width=12)
        table.add_column("Status", width=10)
        table.add_column("Turn", width=10)
        table.add_column("Models", width=20)
        table.add_column("Tokens", width=8)
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
            self._add_conversation_row(table, exp, conv)

        return table

    def _add_conversation_row(self, table, exp, conv):
        """Add a single conversation row to the table."""
        # Status
        status_str, status_color = self._get_status_display(conv.status)

        # Turn progress
        turn_str, turn_color = self._get_turn_display(conv)

        # Models
        models_str = f"{conv.agent_a_model[:8]} ↔ {conv.agent_b_model[:8]}"

        # Convergence
        conv_str = self._get_convergence_display(conv.last_convergence)

        # Truncation
        trunc_str = self._get_truncation_display(conv)

        # Duration
        duration_str = self._format_duration(conv.started_at, conv.completed_at)

        # Tokens
        tokens_str = self._get_conversation_tokens(exp, conv)

        table.add_row(
            exp.name[:15],
            conv.conversation_id[-12:],
            f"[{status_color}]{status_str}[/{status_color}]",
            f"[{turn_color}]{turn_str}[/{turn_color}]",
            models_str,
            tokens_str,
            conv_str,
            trunc_str,
            duration_str,
        )

    def _get_status_display(self, status):
        """Get status string and color."""
        if status == ConversationStatus.RUNNING:
            return "running", NORD_GREEN
        elif status == ConversationStatus.COMPLETED:
            return "completed", NORD_BLUE
        elif status == ConversationStatus.FAILED:
            return "failed", NORD_RED
        else:
            return status, NORD_YELLOW

    def _get_turn_display(self, conv):
        """Get turn progress string and color."""
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
        return turn_str, turn_color

    def _get_convergence_display(self, last_convergence):
        """Get convergence display string."""
        if last_convergence is not None:
            conv_val = last_convergence
            if conv_val >= 0.8:
                conv_color = NORD_RED
                conv_glyph = "▲"
            elif conv_val >= 0.6:
                conv_color = NORD_ORANGE
                conv_glyph = "◆"
            else:
                conv_color = NORD_GREEN
                conv_glyph = "●"
            return f"[{conv_color}]{conv_glyph} {conv_val:.2f}[/{conv_color}]"
        return "-"

    def _get_truncation_display(self, conv):
        """Get truncation display string."""
        if hasattr(conv, "truncation_count") and conv.truncation_count > 0:
            if conv.truncation_count > 5:
                trunc_color = NORD_RED
            elif conv.truncation_count > 2:
                trunc_color = NORD_ORANGE
            else:
                trunc_color = NORD_YELLOW
            return f"[{trunc_color}]⚠ {conv.truncation_count}[/{trunc_color}]"
        return "-"

    def _format_duration(self, started_at, completed_at):
        """Format duration between two timestamps."""
        if not started_at:
            return "-"

        # Ensure started_at is timezone-aware
        started = started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)

        if completed_at:
            completed = completed_at
            if completed.tzinfo is None:
                completed = completed.replace(tzinfo=timezone.utc)
            duration = completed - started
        else:
            # Still running
            now = datetime.now(timezone.utc)
            duration = now - started

        # Sanity check
        total_seconds = int(duration.total_seconds())
        if total_seconds < 0 or total_seconds > 86400:
            return "-"
        elif total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            return f"{total_seconds // 60}m {total_seconds % 60}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def _get_conversation_tokens(self, exp, conv):
        """Get token count for a conversation from manifest."""
        tokens_str = "-"
        manifest_path = exp.directory / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                    conv_data = manifest.get("conversations", {}).get(
                        conv.conversation_id, {}
                    )
                    if "token_usage" in conv_data:
                        total_tokens = conv_data["token_usage"].get("total", 0)
                        if total_tokens > 0:
                            if total_tokens > 1000:
                                tokens_str = f"{total_tokens / 1000:.1f}K"
                            else:
                                tokens_str = str(total_tokens)
            except Exception as e:
                logger.debug(f"Error reading tokens for {conv.conversation_id}: {e}")
        return tokens_str

    def _is_recent(self, timestamp, minutes=5):
        """Check if timestamp is recent."""
        try:
            now = datetime.now(timezone.utc)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return (now - timestamp).total_seconds() < (minutes * 60)
        except (AttributeError, TypeError):
            return False
