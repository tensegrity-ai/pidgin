"""Base display handler with shared utilities."""

from typing import Optional

from rich.console import Console
from rich.text import Text


class BaseDisplayHandler:
    """Base handler with shared display utilities."""

    # Nord color palette
    COLORS = {
        "nord0": "#2e3440",  # Background
        "nord3": "#4c566a",  # Muted gray (dim text)
        "nord4": "#d8dee9",  # Light gray
        "nord7": "#8fbcbb",  # Teal - Setup
        "nord8": "#88c0d0",  # Light blue - Human
        "nord11": "#bf616a",  # Red - Errors
        "nord12": "#d08770",  # Orange - Warnings
        "nord13": "#ebcb8b",  # Yellow - Caution/Timeout
        "nord14": "#a3be8c",  # Green - Success/Agent A
        "nord15": "#5e81ac",  # Blue - Agent B
    }

    def __init__(
        self,
        console: Console,
        mode: str = "normal",
        show_timing: bool = False,
        agents: Optional[dict] = None,
        prompt_tag: Optional[str] = None,
    ):
        """Initialize base handler.

        Args:
            console: Rich console for output
            mode: Display mode ('normal', 'quiet', 'verbose')
            show_timing: Whether to show timing information
            agents: Dict mapping agent_id to Agent objects
            prompt_tag: Optional tag to prefix prompts with
        """
        self.console = console
        self.mode = mode
        self.show_timing = show_timing
        self.agents = agents or {}
        self.prompt_tag = prompt_tag

    def calculate_panel_width(
        self, content: str, title: str = "", min_width: int = 40, max_width: int = 80
    ) -> int:
        """Calculate appropriate panel width based on content.

        Args:
            content: The panel content
            title: The panel title
            min_width: Minimum panel width
            max_width: Maximum panel width

        Returns:
            Calculated panel width
        """
        # Split content into lines and strip ANSI codes for accurate length
        lines = content.split("\n")

        # Find longest line (stripping any rich markup)
        max_line_length = 0
        for line in lines:
            # Use Rich's Text to get actual display length
            text = Text.from_markup(line)
            max_line_length = max(max_line_length, len(text.plain))

        # Consider title length
        title_text = Text.from_markup(title)
        title_length = len(title_text.plain) + 4  # Add padding for title formatting

        # Determine width based on content
        content_width = max(max_line_length, title_length)

        # Apply constraints (+6 for panel borders and padding)
        panel_width = max(min_width, min(content_width + 6, max_width))

        return panel_width
