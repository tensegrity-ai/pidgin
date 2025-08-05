"""Display handlers for conversation lifecycle events."""

from rich.panel import Panel

from ...core.events import (
    ConversationEndEvent,
    ConversationResumedEvent,
    ConversationStartEvent,
    TurnCompleteEvent,
)
from .base import BaseDisplayHandler


class ConversationDisplayHandler(BaseDisplayHandler):
    """Handle conversation start, end, and turn events."""

    def __init__(self, *args, **kwargs):
        """Initialize conversation handler."""
        super().__init__(*args, **kwargs)
        self.current_turn = 0
        self.max_turns = 0

    def show_conversation_start(self, event: ConversationStartEvent):
        """Show conversation setup panel."""
        self.console.print()  # Add newline before panel
        self.max_turns = event.max_turns

        # Use display names if available
        agent_a_display = event.agent_a_display_name or "Agent A"
        agent_b_display = event.agent_b_display_name or "Agent B"

        content = "[bold]Starting Conversation[/bold]\n\n"
        content += f"◈ {agent_a_display}: {event.agent_a_model}"
        if event.temperature_a is not None:
            content += f" (temp: {event.temperature_a})"
        content += "\n"
        content += f"◈ {agent_b_display}: {event.agent_b_model}"
        if event.temperature_b is not None:
            content += f" (temp: {event.temperature_b})"
        content += "\n"
        content += f"◈ Max turns: {event.max_turns}\n"
        content += (
            f"◈ [{self.COLORS['nord3']}]Press Ctrl+C to pause"
            f"[/{self.COLORS['nord3']}]\n\n"
        )

        # Get human tag - use instance value or default
        human_tag = self.prompt_tag if self.prompt_tag is not None else "[HUMAN]"

        # Show initial prompt as agents will see it
        content += "[bold]Initial Prompt (as agents see it):[/bold]\n"
        if human_tag:
            content += f"{human_tag}: {event.initial_prompt}"
        else:
            content += f"{event.initial_prompt}"

        # Calculate appropriate width - allow wider panels for initial prompt display
        width = self.calculate_panel_width(
            content, "⬡ Conversation Setup", max_width=120
        )

        self.console.print(
            Panel(
                content,
                title=" ⬡ Conversation Setup",
                title_align="left",
                border_style=self.COLORS["nord7"],
                padding=(1, 2),
                width=width,
                expand=False,
            )
        )
        self.console.print()

    def show_turn_complete(self, event: TurnCompleteEvent):
        """Show turn completion marker."""
        self.current_turn = event.turn_number + 1

        # Use consistent width similar to panels
        separator_width = min(self.console.width - 4, 60)

        # Build turn info
        turn_info = f"Turn {self.current_turn}/{self.max_turns}"

        # Add convergence if available
        if event.convergence_score is not None:
            conv_text = f"Convergence: {event.convergence_score:.2f}"
            # Add warning if convergence is high
            if event.convergence_score > 0.75:
                conv_text += " [HIGH]"
                # Use plain text for centering calculation
                plain_turn_info = (
                    f"Turn {self.current_turn}/{self.max_turns} | {conv_text}"
                )
                turn_info += (
                    f" | [{self.COLORS['nord13']}]{conv_text}[/{self.COLORS['nord13']}]"
                )
            else:
                plain_turn_info = (
                    f"Turn {self.current_turn}/{self.max_turns} | {conv_text}"
                )
                turn_info += f" | {conv_text}"
        else:
            plain_turn_info = f"Turn {self.current_turn}/{self.max_turns}"

        # Calculate padding for centering
        padding = max(0, (separator_width - len(plain_turn_info)) // 2)
        centered_info = " " * padding + turn_info

        # Print centered separators and info
        self.console.print(
            f"\n[{self.COLORS['nord3']}]{'─' * separator_width}[/{self.COLORS['nord3']}]"
        )
        self.console.print(
            f"[{self.COLORS['nord3']}]{centered_info}[/{self.COLORS['nord3']}]"
        )
        self.console.print(
            f"[{self.COLORS['nord3']}]{'─' * separator_width}[/{self.COLORS['nord3']}]\n"
        )

    def show_conversation_end(self, event: ConversationEndEvent):
        """Show conversation end panel."""
        duration = event.duration_ms / 1000  # Convert to seconds

        content = "[bold]Conversation Complete[/bold]\n\n"
        content += f"◇ Total turns: {event.total_turns}\n"
        content += f"◇ Duration: {duration:.1f}s\n"

        # Enhanced reason display for convergence
        if event.reason == "high_convergence":
            content += "◇ Reason: Convergence threshold reached\n"
            content += "[dim]  (Stopped to prevent token waste)[/dim]"
        else:
            content += f"◇ Reason: {event.reason}"

        # Summary panels should be compact
        width = self.calculate_panel_width(
            content, "⬟ Summary", min_width=40, max_width=60
        )

        self.console.print(
            Panel(
                content,
                title=" ⬟ Summary",
                title_align="left",
                border_style=self.COLORS["nord7"],
                padding=(1, 2),
                width=width,
                expand=False,
            )
        )

    def show_resumed(self, event: ConversationResumedEvent):
        """Show conversation resumed notification."""
        self.console.print(
            f"\n[{self.COLORS['nord14']}]▶ Conversation resumed[/{self.COLORS['nord14']}]\n"
        )

    # Quiet mode methods
    def show_quiet_start(self, event: ConversationStartEvent):
        """Minimal start display."""
        self.max_turns = event.max_turns
        self.console.print(
            f"[{self.COLORS['nord3']}]Starting conversation ({event.max_turns} turns)...[/{self.COLORS['nord3']}]"
        )

    def show_quiet_turn(self, event: TurnCompleteEvent):
        """Minimal turn display."""
        self.current_turn = event.turn_number + 1
        self.console.print(
            f"[{self.COLORS['nord3']}]Turn {self.current_turn}/{self.max_turns} complete[/{self.COLORS['nord3']}]"
        )

    def show_quiet_end(self, event: ConversationEndEvent):
        """Minimal end display."""
        self.console.print(
            f"[{self.COLORS['nord3']}]Done. {event.total_turns} turns in {event.duration_ms/1000:.1f}s[/{self.COLORS['nord3']}]"
        )