"""Formatting utilities for tail display."""

from typing import Optional

from rich.text import Text

from ...core.events import Event
from .constants import EVENT_COLORS, EVENT_GLYPHS, NORD_GRAY, NORD_LIGHT


class TailFormatter:
    """Handles text formatting for tail display."""

    @staticmethod
    def format_agent_id(agent_id: str) -> str:
        """Format agent identifier for display.

        Args:
            agent_id: Raw agent identifier

        Returns:
            Formatted agent name
        """
        if agent_id == "agent_a":
            return "Agent A"
        elif agent_id == "agent_b":
            return "Agent B"
        elif agent_id == "human":
            return "Human"
        else:
            # Capitalize first letter of each word
            return " ".join(word.capitalize() for word in agent_id.split("_"))

    @staticmethod
    def create_event_header(event: Event, timestamp: Optional[str] = None) -> Text:
        """Create formatted header for an event.

        Args:
            event: Event to create header for
            timestamp: Optional timestamp string

        Returns:
            Formatted Rich Text header
        """
        event_type = type(event)
        color = EVENT_COLORS.get(event_type, NORD_GRAY)
        glyph = EVENT_GLYPHS.get(event_type, "•")

        # Create header with timestamp and event name
        header = Text()

        if timestamp:
            header.append(f"[{timestamp}] ", style=f"dim {NORD_GRAY}")

        header.append(f"{glyph} ", style=color)
        header.append(event.__class__.__name__.replace("Event", ""), style=color)

        return header

    @staticmethod
    def format_chunk_content(content: str, agent_id: str) -> Text:
        """Format message chunk content.

        Args:
            content: Message content
            agent_id: Agent identifier

        Returns:
            Formatted Rich Text content
        """
        formatted = Text()
        agent_name = TailFormatter.format_agent_id(agent_id)

        # Use different colors for different agents
        if agent_id == "agent_a":
            color = "#88c0d0"  # Nord cyan
        elif agent_id == "agent_b":
            color = "#a3be8c"  # Nord green
        else:
            color = NORD_LIGHT

        formatted.append(f"{agent_name}: ", style=f"bold {color}")
        formatted.append(content, style=color)

        return formatted

    @staticmethod
    def format_error_details(
        error_message: str, error_type: Optional[str] = None
    ) -> Text:
        """Format error details for display.

        Args:
            error_message: Error message
            error_type: Optional error type

        Returns:
            Formatted Rich Text error
        """
        formatted = Text()

        if error_type:
            formatted.append(f"Error Type: {error_type}\n", style="bold red")

        formatted.append(f"Message: {error_message}", style="red")

        return formatted

    @staticmethod
    def format_metrics(metrics: dict) -> Text:
        """Format metrics dictionary for display.

        Args:
            metrics: Dictionary of metrics

        Returns:
            Formatted Rich Text metrics
        """
        formatted = Text()

        for key, value in metrics.items():
            # Convert underscore to space and capitalize
            display_key = " ".join(word.capitalize() for word in key.split("_"))

            # Format value based on type
            if isinstance(value, float):
                display_value = f"{value:.3f}"
            elif isinstance(value, int):
                display_value = f"{value:,}"
            else:
                display_value = str(value)

            formatted.append(f"  {display_key}: ", style="dim")
            formatted.append(f"{display_value}\n", style="bright")

        return formatted
