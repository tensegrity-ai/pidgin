"""Unified display utilities for consistent error, warning, and info messages.

This module provides standardized functions for displaying messages throughout
Pidgin, ensuring consistent styling and user experience.
"""

from typing import Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Nord color palette
NORD_COLORS = {
    "nord0": "#2e3440",  # Background
    "nord3": "#4c566a",  # Muted gray (dim text)
    "nord4": "#d8dee9",  # Light gray
    "nord7": "#8fbcbb",  # Teal - Info/Setup
    "nord8": "#88c0d0",  # Light blue
    "nord11": "#bf616a",  # Red - Errors
    "nord12": "#d08770",  # Orange - Warnings (alternate)
    "nord13": "#ebcb8b",  # Yellow - Warnings/Caution
    "nord14": "#a3be8c",  # Green - Success
    "nord15": "#5e81ac",  # Blue
}


class DisplayUtils:
    """Utilities for consistent message display."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize display utilities.

        Args:
            console: Rich console instance. If None, creates a new one.
        """
        self.console = console or Console()

    def _calculate_panel_width(
        self,
        content: Union[str, Text],
        title: str = "",
        min_width: int = 40,
        max_width: int = 80,
    ) -> int:
        """Calculate appropriate panel width based on content.

        Args:
            content: The panel content (string or Text object)
            title: The panel title
            min_width: Minimum panel width
            max_width: Maximum panel width

        Returns:
            Calculated panel width
        """
        # Handle both string and Text objects
        if isinstance(content, Text):
            lines = content.plain.split("\n")
        else:
            lines = content.split("\n")

        max_line_length = 0
        for line in lines:
            # For plain strings, we can just use the length
            max_line_length = max(max_line_length, len(line))

        # Consider title length (plain string)
        title_length = len(title) + 4  # Add padding

        # Determine width based on content
        content_width = max(max_line_length, title_length)

        # Apply constraints (+6 for panel borders and padding)
        panel_width = max(min_width, min(content_width + 6, max_width))

        return panel_width

    def error(
        self,
        message: str,
        title: Optional[str] = None,
        context: Optional[str] = None,
        use_panel: bool = True,
    ) -> None:
        """Display an error message.

        Args:
            message: The error message
            title: Optional title for the panel
            context: Optional context information
            use_panel: Whether to use a panel (True) or plain text (False)
        """
        if use_panel:
            content = message
            if context:
                content += f"\n\nContext: {context}"

            title = title or "! Error"
            width = self._calculate_panel_width(content, title)

            self.console.print()  # Add blank line before panel
            self.console.print(
                Panel(
                    content,
                    title=f" {title}",
                    title_align="left",
                    border_style=NORD_COLORS["nord11"],
                    padding=(1, 2),
                    width=width,
                    expand=False,
                )
            )
            self.console.print()  # Add spacing
        else:
            # Plain text mode
            self.console.print(
                f"[{NORD_COLORS['nord11']}][FAIL] {message}[/{NORD_COLORS['nord11']}]"
            )
            if context:
                self.console.print(
                    f"[{NORD_COLORS['nord3']}]       {context}[/{NORD_COLORS['nord3']}]"
                )

    def warning(
        self,
        message: str,
        title: Optional[str] = None,
        context: Optional[str] = None,
        use_panel: bool = True,
    ) -> None:
        """Display a warning message.

        Args:
            message: The warning message
            title: Optional title for the panel
            context: Optional context information
            use_panel: Whether to use a panel (True) or plain text (False)
        """
        if use_panel:
            content = message
            if context:
                content += f"\n\n{context}"

            title = title or "⚠ Warning"
            width = self._calculate_panel_width(content, title, max_width=70)

            self.console.print()  # Add blank line before panel
            self.console.print(
                Panel(
                    content,
                    title=f" {title}",
                    title_align="left",
                    border_style=NORD_COLORS["nord13"],
                    padding=(1, 2),
                    width=width,
                    expand=False,
                )
            )
            self.console.print()  # Add spacing
        else:
            # Plain text mode
            self.console.print(
                f"[{NORD_COLORS['nord13']}]⚠ {message}[/{NORD_COLORS['nord13']}]"
            )
            if context:
                self.console.print(
                    f"[{NORD_COLORS['nord3']}]  {context}[/{NORD_COLORS['nord3']}]"
                )

    def info(
        self, message: str, title: Optional[str] = None, use_panel: bool = True
    ) -> None:
        """Display an info message.

        Args:
            message: The info message
            title: Optional title for the panel
            use_panel: Whether to use a panel (True) or plain text (False)
        """
        if use_panel:
            content = message
            title = title or "◆ Info"
            width = self._calculate_panel_width(content, title, max_width=70)

            self.console.print()  # Add blank line before panel
            self.console.print(
                Panel(
                    content,
                    title=f" {title}",
                    title_align="left",
                    border_style=NORD_COLORS["nord7"],
                    padding=(1, 2),
                    width=width,
                    expand=False,
                )
            )
            self.console.print()  # Add spacing
        else:
            # Plain text mode
            self.console.print(
                f"[{NORD_COLORS['nord7']}]◆ {message}[/{NORD_COLORS['nord7']}]"
            )

    def success(self, message: str, use_panel: bool = False) -> None:
        """Display a success message.

        Args:
            message: The success message
            use_panel: Whether to use a panel (rare for success)
        """
        if use_panel:
            content = (
                f"[bold {NORD_COLORS['nord14']}]{message}"
                f"[/bold {NORD_COLORS['nord14']}]"
            )
            width = self._calculate_panel_width(content, "✓ Success", max_width=60)

            self.console.print()  # Add blank line before panel
            self.console.print(
                Panel(
                    content,
                    title=" ✓ Success",
                    title_align="left",
                    border_style=NORD_COLORS["nord14"],
                    padding=(1, 2),
                    width=width,
                    expand=False,
                )
            )
            self.console.print()
        else:
            # Plain text mode (default for success)
            self.console.print(
                f"[{NORD_COLORS['nord14']}][OK] {message}[/{NORD_COLORS['nord14']}]"
            )

    def api_error(
        self,
        agent_name: str,
        provider: str,
        error_message: str,
        retryable: bool = False,
        billing_url: Optional[str] = None,
    ) -> None:
        """Display an API error with special handling for billing issues.

        Args:
            agent_name: Name of the agent that encountered the error
            provider: API provider name
            error_message: The error message
            retryable: Whether the error is retryable
            billing_url: Optional billing URL for billing-related errors
        """
        # Check if it's a billing error
        error_lower = error_message.lower()
        is_billing = any(
            phrase in error_lower
            for phrase in ["credit", "billing", "payment", "quota", "insufficient"]
        )

        if is_billing and billing_url:
            # Special billing error display
            content = (
                f"[bold {NORD_COLORS['nord13']}]{agent_name} cannot respond"
                f"[/bold {NORD_COLORS['nord13']}]\n\n"
            )
            content += f"◇ {error_message}\n"
            content += (
                f"\n[{NORD_COLORS['nord4']}]To fix: Visit {billing_url}"
                f"[/{NORD_COLORS['nord4']}]"
            )

            title = "Billing Issue"
            border_style = NORD_COLORS["nord13"]  # Yellow for billing
        else:
            # Regular API error
            content = (
                f"[bold {NORD_COLORS['nord11']}]Connection Issue"
                f"[/bold {NORD_COLORS['nord11']}]\n\n"
            )
            content += f"◈ Agent: {agent_name}\n"
            content += f"◈ Provider: {provider}\n"
            content += f"◈ Error: {error_message}\n"

            if retryable:
                content += (
                    f"\n[{NORD_COLORS['nord8']}]◇ Retrying automatically..."
                    f"[/{NORD_COLORS['nord8']}]"
                )
            else:
                content += (
                    f"\n[{NORD_COLORS['nord3']}]◇ Cannot retry automatically"
                    f"[/{NORD_COLORS['nord3']}]"
                )

            title = "◆ API Error"
            border_style = NORD_COLORS["nord11"]

        width = self._calculate_panel_width(content, title)

        self.console.print()  # Add blank line before panel
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

    def dim(self, message: str) -> None:
        """Display a dimmed/muted message.

        Args:
            message: The message to display dimly
        """
        self.console.print(
            f"[{NORD_COLORS['nord3']}]{message}[/{NORD_COLORS['nord3']}]"
        )

    def status(self, message: str, style: str = "nord8") -> None:
        """Display a status message.

        Args:
            message: The status message
            style: Color style to use (defaults to nord8/light blue)
        """
        color = NORD_COLORS.get(style, NORD_COLORS["nord8"])
        self.console.print(f"[{color}]→ {message}[/{color}]")

    def note(self, message: str) -> None:
        """Display a note/secondary message (alias for dim).

        Args:
            message: The note to display
        """
        self.dim(message)

    def experiment_complete(
        self,
        name: str,
        experiment_id: str,
        completed: int,
        failed: int,
        total: int,
        duration_seconds: float,
        status: str,
        experiment_dir: Optional[str] = None,
    ) -> None:
        """Display experiment completion summary in a panel.

        Args:
            name: Experiment name
            experiment_id: Experiment ID
            completed: Number of completed conversations
            failed: Number of failed conversations
            total: Total number of conversations
            duration_seconds: Total duration in seconds
            status: Final status (completed, completed_with_failures, interrupted)
            experiment_dir: Experiment directory path
        """
        # Format duration
        if duration_seconds < 60:
            duration_str = f"{duration_seconds:.1f}s"
        elif duration_seconds < 3600:
            minutes = int(duration_seconds / 60)
            seconds = int(duration_seconds % 60)
            duration_str = f"{minutes}m {seconds}s"
        else:
            hours = int(duration_seconds / 3600)
            minutes = int((duration_seconds % 3600) / 60)
            duration_str = f"{hours}h {minutes}m"

        # Build content lines
        lines = []
        lines.append("[bold]◇ Experiment Complete[/bold]")
        lines.append("")
        lines.append(f"Name: {name}")
        lines.append(f"ID: {experiment_id}")
        lines.append("")

        # Conversation summary
        if failed == 0:
            lines.append(f"Conversations: {completed}/{total} completed")
        else:
            lines.append(
                f"Conversations: {completed}/{total} completed, {failed} failed"
            )

        lines.append(f"Duration: {duration_str}")

        if experiment_dir:
            lines.append("")
            lines.append(f"[dim]Data: {experiment_dir}[/dim]")

        # Choose color based on status
        if status == "interrupted":
            border_color = NORD_COLORS["nord13"]  # Yellow for interrupted
            title = "⚠ Experiment Interrupted"
        elif failed > 0:
            border_color = NORD_COLORS["nord13"]  # Yellow for partial success
            title = "◇ Experiment Complete (with failures)"
        else:
            border_color = NORD_COLORS["nord14"]  # Green for full success
            title = "◇ Experiment Complete"

        # Create panel
        content = "\n".join(lines)
        self.console.print()  # Add blank line before panel
        self.console.print(
            Panel(
                content,
                title=f" {title} ",
                title_align="left",
                border_style=border_color,
                padding=(1, 2),
                width=self._calculate_panel_width(content, title, max_width=80),
                expand=False,
            )
        )

    def api_key_error(self, message: str, provider: Optional[str] = None) -> None:
        """Display an API key configuration error.

        Args:
            message: The error message (can contain multiple lines)
            provider: Optional provider name for context
        """
        # Format the message with styling
        # Create styled text for the content
        text = Text()
        text.append("Configuration Required\n\n", style=f"bold {NORD_COLORS['nord11']}")

        # Parse and style the message lines
        lines = message.strip().split("\n")
        for line in lines:
            if line.strip():
                if line.strip().startswith("•"):
                    # Bullet points in red
                    text.append(line + "\n", style=NORD_COLORS["nord11"])
                elif line.strip().startswith("export"):
                    # Commands in cyan
                    text.append("  " + line.strip() + "\n", style=NORD_COLORS["nord8"])
                elif "https://" in line:
                    # URLs in light gray
                    text.append("\n" + line + "\n", style=NORD_COLORS["nord4"])
                else:
                    # Regular text
                    text.append(line + "\n")

        # Create and display the panel
        title = "◆ API Key Missing"
        self.console.print()  # Add blank line before panel
        self.console.print(
            Panel(
                text,
                title=f" {title}",
                title_align="left",
                border_style=NORD_COLORS["nord11"],
                padding=(1, 2),
                expand=False,
            )
        )
        self.console.print()  # Add spacing


# Create a default instance for convenience
default_display = DisplayUtils()

# Export convenience functions
error = default_display.error
warning = default_display.warning
info = default_display.info
success = default_display.success
api_error = default_display.api_error
api_key_error = default_display.api_key_error
dim = default_display.dim
status = default_display.status
note = default_display.note
