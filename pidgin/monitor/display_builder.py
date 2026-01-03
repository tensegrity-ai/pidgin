"""Display building components for the monitor."""

from datetime import datetime
from typing import Any, List

from rich import box
from rich.panel import Panel
from rich.table import Table

from ..cli.constants import (
    NORD_BLUE,
    NORD_CYAN,
    NORD_DARK,
    NORD_GREEN,
    NORD_LIGHT,
    NORD_YELLOW,
)
from ..core.constants import ConversationStatus
from ..io.logger import get_logger
from .conversation_panel_builder import ConversationPanelBuilder
from .error_panel_builder import ErrorPanelBuilder

logger = get_logger("display_builder")


class DisplayBuilder:
    """Builds display panels for the monitor."""

    def __init__(self, console, exp_base):
        """Initialize display builder.

        Args:
            console: Rich console instance
            exp_base: Base experiments directory
        """
        self.console = console
        self.exp_base = exp_base
        self.refresh_count = 0

        # Initialize sub-builders
        self.error_panel_builder = ErrorPanelBuilder(self.get_panel_width)
        self.conversation_panel_builder = ConversationPanelBuilder(self.get_panel_width)

    def get_panel_width(self) -> int:
        """Calculate panel width based on current terminal size."""
        terminal_width = self.console.size.width
        # Leave some margin for borders and scrollbars
        # Minimum width of 60, maximum of 150 for readability
        return max(60, min(terminal_width - 4, 150))

    def build_header(self) -> Panel:
        """Build header panel."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Add a rotating refresh indicator
        refresh_indicators = ["◐", "◓", "◑", "◒"]
        indicator = refresh_indicators[self.refresh_count % len(refresh_indicators)]

        return Panel(
            f"[bold {NORD_BLUE}]◆ PIDGIN MONITOR[/bold {NORD_BLUE}] | "
            f"[{NORD_DARK}]{timestamp}[/{NORD_DARK}] | "
            f"[{NORD_GREEN}]{indicator}[/{NORD_GREEN}] | "
            f"[{NORD_DARK}]Press Ctrl+C to exit[/{NORD_DARK}]",
            style=NORD_CYAN,
            width=self.get_panel_width(),
        )

    def build_no_experiments_message(self) -> Panel:
        """Build panel for when no experiments exist."""
        return Panel(
            f"[{NORD_YELLOW}]No experiments directory found at:[/{NORD_YELLOW}]\n\n"
            f"[{NORD_LIGHT}]{self.exp_base}[/{NORD_LIGHT}]\n\n"
            f"[{NORD_DARK}]Run 'pidgin run' to create your first experiment.[/{NORD_DARK}]",
            title="No Experiments Found",
            border_style=NORD_YELLOW,
            width=self.get_panel_width(),
        )

    def build_experiments_panel(
        self, experiments: List[Any], metrics_calculator
    ) -> Panel:
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
        table.add_column("ID", style=NORD_CYAN, width=24)
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

            # Current conversation status
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

            # Get tokens and cost from metrics calculator
            total_tokens = metrics_calculator.estimate_tokens_for_experiment(exp)
            cost_estimate = metrics_calculator.estimate_cost_for_experiment(
                exp, total_tokens
            )

            if total_tokens > 1_000_000:
                tokens_str = f"{total_tokens / 1_000_000:.1f}M"
            elif total_tokens > 1000:
                tokens_str = f"{total_tokens / 1000:.0f}K"
            else:
                tokens_str = str(total_tokens) if total_tokens > 0 else "-"

            # Determine status color
            if exp.status == "running":
                status_color = NORD_GREEN
            elif exp.status == "created":
                status_color = NORD_YELLOW
            else:
                status_color = NORD_BLUE

            table.add_row(
                exp.experiment_id[:24],
                exp.name[:20],
                f"[{status_color}]{exp.status}[/{status_color}]",
                progress_str,
                current_str,
                tokens_str,
                f"${cost_estimate:.2f}" if cost_estimate > 0 else "-",
            )

        return Panel(
            table,
            title=f"Active Experiments ({len(active_experiments)})",
            width=self.get_panel_width(),
        )

    def build_conversations_panel(self, experiments: List[Any]) -> Panel:
        """Build detailed conversations panel."""
        return self.conversation_panel_builder.build_conversations_panel(experiments)

    def build_errors_panel(self, errors: List[dict], error_tracker) -> Panel:
        """Build panel showing recent errors."""
        return self.error_panel_builder.build_errors_panel(errors, error_tracker)

    def build_summary_panel(self, experiments: List[Any], metrics_calculator) -> Panel:
        """Build summary panel with aggregate statistics across all experiments."""
        total_conversations = 0
        completed_conversations = 0
        total_tokens = 0
        total_cost = 0.0

        for exp in experiments:
            # Count conversations
            total_conversations += len(exp.conversations)
            completed_conversations += sum(
                1 for c in exp.conversations.values() if str(c.status) == "completed"
            )

            # Aggregate tokens and cost
            exp_tokens = metrics_calculator.estimate_tokens_for_experiment(exp)
            total_tokens += exp_tokens
            total_cost += metrics_calculator.estimate_cost_for_experiment(
                exp, exp_tokens
            )

        # Format tokens
        if total_tokens > 1_000_000:
            tokens_str = f"{total_tokens / 1_000_000:.1f}M"
        elif total_tokens > 1000:
            tokens_str = f"{total_tokens / 1000:.0f}K"
        else:
            tokens_str = str(total_tokens) if total_tokens > 0 else "0"

        # Build summary text
        if total_conversations > 0:
            pct = completed_conversations / total_conversations * 100
            summary = (
                f"[{NORD_LIGHT}]Conversations:[/{NORD_LIGHT}] "
                f"[{NORD_GREEN}]{completed_conversations}[/{NORD_GREEN}]"
                f"[{NORD_DARK}]/{total_conversations}[/{NORD_DARK}] "
                f"[{NORD_DARK}]({pct:.0f}%)[/{NORD_DARK}]"
                f"  [{NORD_DARK}]│[/{NORD_DARK}]  "
                f"[{NORD_LIGHT}]Tokens:[/{NORD_LIGHT}] [{NORD_CYAN}]{tokens_str}[/{NORD_CYAN}]"
                f"  [{NORD_DARK}]│[/{NORD_DARK}]  "
                f"[{NORD_LIGHT}]Cost:[/{NORD_LIGHT}] [{NORD_YELLOW}]${total_cost:.2f}[/{NORD_YELLOW}]"
            )
        else:
            summary = f"[{NORD_DARK}]No experiments yet[/{NORD_DARK}]"

        return Panel(
            summary,
            title="Summary",
            border_style=NORD_DARK,
            width=self.get_panel_width(),
        )
