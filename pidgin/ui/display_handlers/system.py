"""Display handlers for system events."""

from rich.panel import Panel

from ...core.events import SystemPromptEvent
from .base import BaseDisplayHandler


class SystemDisplayHandler(BaseDisplayHandler):
    """Handle system prompts and pacing indicators."""

    def show_system_prompt(self, event: SystemPromptEvent):
        """Show system context panel."""
        # Use display name if available, otherwise fallback to agent_id
        display_name = event.agent_display_name
        if not display_name:
            if event.agent_id in self.agents:
                display_name = self.agents[event.agent_id].display_name
            else:
                display_name = event.agent_id.replace("_", " ").title()

        content = (
            f"[{self.COLORS['nord3']}]System instructions:"
            f"[/{self.COLORS['nord3']}]\n\n{event.prompt}"
        )

        # Customize the display based on which agent
        if event.agent_id == "agent_a":
            title = f"⧫ System Context - {display_name}"
            style = self.COLORS["nord14"]  # Green
        elif event.agent_id == "agent_b":
            title = f"⧫ System Context - {display_name}"
            style = self.COLORS["nord15"]  # Blue
        else:
            title = f"⧫ System Context - {display_name}"
            style = self.COLORS["nord13"]  # Yellow

        # Calculate width - system prompts are usually short
        width = self.calculate_panel_width(content, title, min_width=50, max_width=70)

        self.console.print(
            Panel(
                content,
                title=f" {title}",
                title_align="left",
                border_style=style,
                padding=(1, 2),
                width=width,
                expand=False,
            )
        )
        self.console.print()

    def show_pacing_indicator(self, provider: str, wait_time: float):
        """Show rate limit pacing in a nice panel.

        Args:
            provider: Provider name being paced
            wait_time: How long we're waiting in seconds
        """
        if wait_time < 0.5:
            # Very brief pause - don't show anything
            return

        # Format the wait time nicely
        if wait_time < 1.0:
            time_str = f"{wait_time:.1f}s"
        else:
            time_str = f"{wait_time:.1f}s"

        # Create a subtle panel
        content = f"⏸ Waiting {time_str} for {provider} rate limits"

        # Calculate width for pacing panel - should be compact
        width = self.calculate_panel_width(content, "", min_width=35, max_width=50)

        self.console.print()  # Leading newline
        self.console.print(
            Panel(
                content,
                style=self.COLORS["nord13"],  # Yellow
                border_style=self.COLORS["nord3"],  # Dim border
                padding=(0, 1),
                width=width,
                expand=False,
            )
        )
        self.console.print()  # Trailing newline

    def show_token_usage(self, provider: str, used: int, limit: int):
        """Show current token consumption rate.

        Args:
            provider: Provider name
            used: Current tokens per minute
            limit: Token per minute limit
        """
        percentage = (used / limit) * 100 if limit > 0 else 0
        bar_width = 20
        filled = int(bar_width * percentage / 100)

        bar = "█" * filled + "░" * (bar_width - filled)
        color = self.COLORS["nord14"] if percentage < 80 else self.COLORS["nord13"]

        self.console.print(
            f"[{self.COLORS['nord3']}]Tokens/min:[/{self.COLORS['nord3']}] [{color}]{bar}[/{color}] {percentage:.0f}%"
        )
