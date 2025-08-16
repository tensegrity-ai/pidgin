"""Display handlers for message events."""

from rich.text import Text

from ...core.events import MessageCompleteEvent
from .base import BaseDisplayHandler


class MessageDisplayHandler(BaseDisplayHandler):
    """Handle message display events."""

    def show_message(self, event: MessageCompleteEvent):
        """Show complete messages with agent info."""
        # Skip system messages in normal display (they're shown separately)
        if hasattr(event.message, "role") and event.message.role == "system":
            return

        # Get agent's display name and model display name if available
        agent_name = None
        model_display_name = None
        if event.agent_id in self.agents:
            agent = self.agents[event.agent_id]
            agent_name = agent.display_name or event.agent_id
            model_display_name = agent.model_display_name

        # Determine styling based on agent
        if event.agent_id == "agent_a":
            # Build name with optional model display name
            if (
                model_display_name
                and agent_name != model_display_name
                and not agent_name.startswith(model_display_name)
            ):
                # Show both name and model display name (e.g., "Kai (Haiku)")
                display_name = f"{agent_name} ({model_display_name})"
            else:
                # Just show the name (e.g., "Haiku-1" or "Agent A")
                display_name = agent_name or "Agent A"
            glyph = "◆"
            color = self.COLORS["nord14"]  # Green
        elif event.agent_id == "agent_b":
            # Build name with optional model display name
            if (
                model_display_name
                and agent_name != model_display_name
                and not agent_name.startswith(model_display_name)
            ):
                # Show both name and model display name (e.g., "Zara (Sonnet)")
                display_name = f"{agent_name} ({model_display_name})"
            else:
                # Just show the name (e.g., "Sonnet-2" or "Agent B")
                display_name = agent_name or "Agent B"
            glyph = "●"
            color = self.COLORS["nord15"]  # Blue
        elif "human" in event.agent_id.lower():
            display_name = "Human Intervention"
            glyph = "◊"
            color = self.COLORS["nord8"]  # Light blue
        else:
            display_name = event.agent_id.title()
            glyph = "○"
            color = self.COLORS["nord3"]  # Gray

        # Extract message content
        if hasattr(event.message, "content"):
            content = event.message.content
        else:
            content = str(event.message)

        # Show the message without a panel
        self.console.print(f"\n[{color}]{glyph} {display_name}:[/{color}]")

        # Wrap the message content at consistent width
        text_width = min(self.console.width - 4, 80)
        wrapped_text = Text(content)
        self.console.print(wrapped_text, width=text_width, style="default")

        if self.show_timing:
            tokens_used = getattr(event, "tokens_used", "unknown")
            self.console.print(
                f"[{self.COLORS['nord3']}]⟐ Duration: {event.duration_ms}ms | "
                f"Tokens: {tokens_used}[/{self.COLORS['nord3']}]"
            )

        self.console.print()  # Add spacing after message
