"""Error panel building for the monitor."""

from datetime import datetime, timezone
from typing import List

from rich.panel import Panel
from rich.table import Table

from ..cli.constants import (
    NORD_BLUE,
    NORD_DARK,
    NORD_GREEN,
    NORD_ORANGE,
    NORD_RED,
    NORD_YELLOW,
)
from ..io.logger import get_logger

logger = get_logger("error_panel_builder")


class ErrorPanelBuilder:
    """Builds error display panel for the monitor."""

    def __init__(self, panel_width_getter):
        """Initialize error panel builder.

        Args:
            panel_width_getter: Function to get panel width
        """
        self.get_panel_width = panel_width_getter

    def build_errors_panel(self, errors: List[dict], error_tracker) -> Panel:
        """Build panel showing recent errors with detailed information."""
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
            # Format time
            time_str = self._format_time_ago(error.get("timestamp"))

            # Get provider
            provider = self._extract_provider(error)

            # Get error type
            error_type = self._extract_error_type(error)

            # Build context
            context_str = self._build_error_context(error)

            # Check status
            status_str, status_color = self._get_error_status(
                error, errors, error_tracker
            )

            # Determine row color based on error type
            type_color, glyph = self._get_error_display_style(error_type)

            # Add row to table
            table.add_row(
                time_str,
                f"[{type_color}]{provider}[/{type_color}]",
                f"[{type_color}]{glyph} {error_type}[/{type_color}]",
                context_str,
                f"[{status_color}]{status_str}[/{status_color}]",
            )

        # Add summary footer if there are more errors
        if len(errors) > 10:
            table.add_row("", "", "", f"[dim]... and {len(errors) - 10} more[/dim]", "")

        title = f"Recent Errors ({len(errors)}) - Last 10m"
        return Panel(table, title=title, width=self.get_panel_width())

    def _format_time_ago(self, timestamp_str):
        """Format timestamp as relative time."""
        if not timestamp_str:
            return "unknown"

        try:
            if isinstance(timestamp_str, datetime):
                event_time = timestamp_str
            else:
                event_time = datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                )

            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            delta = now - event_time

            if delta.total_seconds() < 60:
                return f"{int(delta.total_seconds())}s ago"
            elif delta.total_seconds() < 3600:
                return f"{int(delta.total_seconds() / 60)}m ago"
            else:
                return f"{int(delta.total_seconds() / 3600)}h ago"
        except (ValueError, AttributeError, TypeError):
            return "unknown"

    def _extract_provider(self, error):
        """Extract provider name from error."""
        provider = error.get("provider", "")
        if not provider:
            agent_id = error.get("agent_id", "")
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

        provider_display = provider.replace("Provider", "").title()
        if provider_display == "Unknown":
            provider_display = "?"

        return provider_display

    def _extract_error_type(self, error):
        """Extract and format error type."""
        error_type = error.get("error_type", "unknown")
        error_message = error.get("error_message", "")

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

        type_display = error_type.replace("_", " ").title()
        if type_display == "Api Error":
            type_display = "API Error"

        return type_display

    def _build_error_context(self, error):
        """Build context string for error display."""
        context_parts = []

        # Add experiment name if available
        experiment_id = error.get("experiment_id", "")
        if experiment_id:
            exp_parts = experiment_id.split("_")
            if len(exp_parts) >= 3:
                exp_name = exp_parts[2]
                context_parts.append(self._truncate_text(exp_name, 20))

        # Add conversation ID (shortened)
        conversation_id = error.get("conversation_id", "")
        if conversation_id:
            conv_short = conversation_id.split("_")[-1][:8]
            context_parts.append(f"conv_{conv_short}")

        # Add agent info if available
        agent_id = error.get("agent_id", "")
        if agent_id:
            agent_display = agent_id
            if "gpt" in agent_id or "claude" in agent_id or "gemini" in agent_id:
                agent_display = agent_id.split("/")[-1]
            context_parts.append(f"Agent: {self._truncate_text(agent_display, 15)}")

        # Add error message snippet if no other context
        if len(context_parts) < 2:
            error_message = error.get("error_message", "")
            if error_message:
                msg_snippet = self._truncate_text(error_message, 30)
                context_parts.append(f'"{msg_snippet}"')

        # Add context string if available
        context = error.get("context", "")
        if context and len(context_parts) < 3:
            context_parts.append(self._truncate_text(context, 35))

        return "\n".join(context_parts[:3]) if context_parts else "No context"

    def _get_error_status(self, error, all_errors, error_tracker):
        """Get status string and color for an error."""
        retry_count = error.get("retry_count", 0)
        retryable = error.get("retryable", False)

        # Check if error might be resolved
        is_resolved = error_tracker.check_error_resolved(error, all_errors)

        if is_resolved:
            return "Resolved", NORD_GREEN
        elif retry_count > 0:
            return f"Retried {retry_count}x", NORD_ORANGE
        elif retryable:
            return "Retryable", NORD_BLUE
        else:
            return "Failed", NORD_RED

    def _get_error_display_style(self, error_type):
        """Get color and glyph for error type display."""
        if error_type in ["Rate Limit", "Overloaded"]:
            return NORD_ORANGE, "▲"
        elif error_type in ["Auth Error", "Unauthorized"]:
            return NORD_RED, "✗"
        elif "Timeout" in error_type:
            return NORD_YELLOW, "⏱"
        else:
            return NORD_YELLOW, "!"

    def _truncate_text(self, text: str, max_length: int, suffix: str = "...") -> str:
        """Truncate text to max length with suffix."""
        if len(text) <= max_length:
            return text
        return text[: max_length - len(suffix)] + suffix
