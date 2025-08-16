"""Display handlers for error events."""

from rich.panel import Panel

from ...core.events import (
    APIErrorEvent,
    ContextLimitEvent,
    ErrorEvent,
    ProviderTimeoutEvent,
)
from .base import BaseDisplayHandler


class ErrorDisplayHandler(BaseDisplayHandler):
    """Handle error display events."""

    def show_api_error(self, event: APIErrorEvent):
        """Show API error with context."""
        # Get agent's display name if available
        agent_name = None
        if event.agent_id in self.agents:
            agent_name = self.agents[event.agent_id].display_name or event.agent_id

        # Check for common billing/credit errors
        error_lower = event.error_message.lower()
        is_billing_error = any(
            phrase in error_lower
            for phrase in ["credit", "billing", "payment", "quota", "insufficient"]
        )

        if is_billing_error:
            # Special handling for billing errors - less scary, more actionable
            title = "Billing Issue"
            border_style = self.COLORS["nord13"]  # Yellow instead of red

            # Determine which service
            service_url = ""
            if "anthropic" in event.provider.lower():
                service_url = "console.anthropic.com → Billing"
            elif "openai" in event.provider.lower():
                service_url = "platform.openai.com → Billing"

            content = (
                f"[bold {self.COLORS['nord13']}]{agent_name or event.agent_id} "
                f"cannot respond[/bold {self.COLORS['nord13']}]\n\n"
            )
            content += f"◇ {event.error_message}\n"
            if service_url:
                content += f"\n[{self.COLORS['nord4']}]To fix: Visit {service_url}[/{self.COLORS['nord4']}]"
        else:
            # Regular API error display
            title = "◆ API Error"
            border_style = self.COLORS["nord11"]

            content = f"[bold {self.COLORS['nord11']}]Connection Issue[/bold {self.COLORS['nord11']}]\n\n"
            content += f"◈ Agent: {agent_name or event.agent_id}\n"
            content += f"◈ Provider: {event.provider}\n"

            # Show error message
            error_msg = event.error_message
            if len(error_msg) > 200:
                error_msg = error_msg[:197] + "..."
            content += f"◈ Error: {error_msg}\n"

            # Show retry info
            if event.retryable:
                content += f"\n[{self.COLORS['nord8']}]◇ Retrying automatically...[/{self.COLORS['nord8']}]"
            else:
                content += f"\n[{self.COLORS['nord3']}]◇ Cannot retry automatically[/{self.COLORS['nord3']}]"

        # Calculate appropriate width for error panels
        width = self.calculate_panel_width(content, title, min_width=40, max_width=80)

        self.console.print(
            Panel(
                content,
                title=title,
                title_align="left",
                border_style=border_style,
                padding=(1, 2),
                width=width,
                expand=False,
            )
        )
        self.console.print()

    def show_error(self, event: ErrorEvent):
        """Show generic error."""
        content = (
            f"[bold {self.COLORS['nord11']}]"
            f"{event.error_type.replace('_', ' ').title()}"
            f"[/bold {self.COLORS['nord11']}]\n\n"
        )
        content += f"{event.error_message}"

        if event.context:
            content += f"\n\n[{self.COLORS['nord3']}]Context: {event.context}[/{self.COLORS['nord3']}]"

        # Calculate appropriate width
        width = self.calculate_panel_width(
            content, "! Error", min_width=40, max_width=80
        )

        self.console.print(
            Panel(
                content,
                title=" ! Error",
                title_align="left",
                border_style=self.COLORS["nord11"],
                padding=(1, 2),
                width=width,
                expand=False,
            )
        )
        self.console.print()

    def show_timeout_error(self, event: ProviderTimeoutEvent):
        """Show timeout error with options."""
        # Get agent's display name if available
        agent_name = None
        if event.agent_id in self.agents:
            agent_name = self.agents[event.agent_id].display_name or event.agent_id

        content = (
            f"[bold {self.COLORS['nord13']}]Timeout[/bold {self.COLORS['nord13']}]\n\n"
        )
        content += f"◈ Agent: {agent_name or event.agent_id}\n"
        content += f"◈ Timeout: {event.timeout_seconds}s\n"
        content += f"◈ {event.error_message}\n"

        if event.context:
            content += f"\n[dim]Context: {event.context}[/dim]"

        # Calculate appropriate width
        width = self.calculate_panel_width(
            content, "⏱ Timeout", min_width=40, max_width=70
        )

        self.console.print(
            Panel(
                content,
                title=" ⏱ Timeout",
                title_align="left",
                border_style=self.COLORS["nord13"],
                padding=(1, 2),
                width=width,
                expand=False,
            )
        )
        self.console.print()

    def show_context_limit(self, event: ContextLimitEvent):
        """Show context limit reached with informative message."""
        # Get agent's display name if available
        agent_name = None
        if event.agent_id in self.agents:
            agent_name = self.agents[event.agent_id].display_name or event.agent_id

        title = "◆ Context Window Limit Reached"
        border_style = self.COLORS["nord13"]  # Yellow

        content = (
            f"[bold {self.COLORS['nord13']}]Natural Conversation End[/bold {self.COLORS['nord13']}]\n\n"
            f"◈ Agent: {agent_name or event.agent_id}\n"
            f"◈ Provider: {event.provider}\n"
            f"◈ Turn: {event.turn_number}\n\n"
            f"[{self.COLORS['nord4']}]The conversation has reached the model's context window limit.\n"
            f"This is a natural endpoint for the conversation.[/{self.COLORS['nord4']}]"
        )

        # Calculate appropriate width
        width = self.calculate_panel_width(content, title)

        self.console.print()
        self.console.print(
            Panel(
                content,
                title=title,
                title_align="left",
                border_style=border_style,
                padding=(1, 2),
                width=width,
                expand=False,
            )
        )
        self.console.print()
