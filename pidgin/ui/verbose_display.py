"""Verbose display for watching conversations with minimal metadata."""

from typing import Dict

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from ..core.event_bus import EventBus
from ..core.events import (
    ContextTruncationEvent,
    ConversationEndEvent,
    ConversationStartEvent,
    MessageCompleteEvent,
    TurnCompleteEvent,
)
from ..core.types import Agent


class VerboseDisplay:
    """Verbose display showing messages and turn markers."""

    # Nord color palette
    COLORS = {
        "agent_a": "#a3be8c",  # Nord14 green
        "agent_b": "#5e81ac",  # Nord10 blue
        "turn": "#4c566a",  # Nord3 gray
        "convergence_low": "#a3be8c",  # Nord14 green
        "convergence_mid": "#ebcb8b",  # Nord13 yellow
        "convergence_high": "#bf616a",  # Nord11 red
        "header": "#8fbcbb",  # Nord7 teal
        "dim": "#4c566a",  # Nord3 gray
    }

    def __init__(self, bus: EventBus, console: Console, agents: Dict[str, Agent]):
        """Initialize verbose display.

        Args:
            bus: Event bus to subscribe to
            console: Rich console for output
            agents: Dict of agent_id -> Agent
        """
        self.bus = bus
        self.console = console
        self.agents = agents
        self.current_turn = 0
        self.max_turns = 0
        self.truncation_occurred = False
        self.conversation_count = 0

        # Subscribe to relevant events
        bus.subscribe(ConversationStartEvent, self.handle_start)
        bus.subscribe(MessageCompleteEvent, self.handle_message)
        bus.subscribe(TurnCompleteEvent, self.handle_turn_complete)
        bus.subscribe(ConversationEndEvent, self.handle_end)
        bus.subscribe(ContextTruncationEvent, self.handle_truncation)

    def handle_start(self, event: ConversationStartEvent) -> None:
        """Display conversation start header.

        Args:
            event: Conversation start event
        """
        # Reset state for new conversation
        self.current_turn = 0
        self.max_turns = event.max_turns
        self.truncation_occurred = False
        self.conversation_count += 1

        # Add separator if this is not the first conversation
        if self.conversation_count > 1:
            self.console.print()
            self.console.print(Rule(style=self.COLORS["dim"]))
            self.console.print()

        # Update agent display names from event
        if event.agent_a_display_name and "agent_a" in self.agents:
            self.agents["agent_a"].display_name = event.agent_a_display_name
        if event.agent_b_display_name and "agent_b" in self.agents:
            self.agents["agent_b"].display_name = event.agent_b_display_name
            
        # Build header
        agent_a_name = event.agent_a_display_name or "Agent A"
        agent_b_name = event.agent_b_display_name or "Agent B"

        header = Text()
        header.append("◆ ", style=self.COLORS["header"])
        header.append(f"{agent_a_name} ", style=self.COLORS["agent_a"] + " bold")
        header.append("↔ ", style=self.COLORS["dim"])
        header.append(f"{agent_b_name}", style=self.COLORS["agent_b"] + " bold")

        # Show initial prompt as agents see it (with human tag)
        from ..config import Config

        config = Config()
        human_tag = config.get("defaults.human_tag", "[HUMAN]")

        # Format prompt as agents see it
        if human_tag:
            prompt_content = f"{human_tag}: {event.initial_prompt}"
        else:
            prompt_content = event.initial_prompt

        prompt_panel = Panel(
            prompt_content,
            title="[bold]Initial Prompt[/bold]",
            title_align="left",
            border_style=self.COLORS["header"],
            padding=(1, 2),
            width=120,  # Allow wider display for longer prompts
            expand=False,
        )

        self.console.print()
        self.console.print(header, justify="center")
        self.console.print()
        self.console.print(prompt_panel)
        self.console.print()

    def handle_message(self, event: MessageCompleteEvent) -> None:
        """Display a message.

        Args:
            event: Message complete event
        """
        # Skip system messages
        if hasattr(event.message, "role") and event.message.role == "system":
            return

        # Get agent info
        agent_name = "Unknown"
        color = self.COLORS["dim"]
        symbol = "○"

        if event.agent_id in self.agents:
            agent = self.agents[event.agent_id]
            agent_name = agent.display_name or agent.model

            if event.agent_id == "agent_a":
                color = self.COLORS["agent_a"]
                symbol = "◆"
            elif event.agent_id == "agent_b":
                color = self.COLORS["agent_b"]
                symbol = "●"

        # Extract content
        content = (
            event.message.content
            if hasattr(event.message, "content")
            else str(event.message)
        )

        # Create styled name header
        name_text = Text()
        name_text.append(f"{symbol} ", style=color)
        name_text.append(agent_name, style=color + " bold")

        # Render content
        if any(marker in content for marker in ["```", "**", "*", "#", "-", "1."]):
            try:
                content_display = Markdown(content, code_theme="nord")
            except (ValueError, AttributeError, Exception):
                # Markdown parsing failed, fall back to plain text
                content_display = Text(content, style="default")
        else:
            content_display = Text(content, style="default")

        # Create panel with agent name as title
        message_panel = Panel(
            content_display,
            title=name_text,
            title_align="left",
            border_style=color,
            padding=(1, 2),
            width=80,
            expand=False,
        )

        self.console.print()
        self.console.print(message_panel)

    def handle_turn_complete(self, event: TurnCompleteEvent) -> None:
        """Display turn separator.

        Args:
            event: Turn complete event
        """
        self.current_turn = event.turn_number + 1

        # Skip if this is the last turn
        if self.current_turn >= self.max_turns:
            return

        # Build turn info with convergence
        info = Text()
        info.append(
            f"Turn {self.current_turn}/{self.max_turns}", style=self.COLORS["turn"]
        )

        if event.convergence_score is not None:
            # Color based on convergence level
            if event.convergence_score < 0.5:
                conv_color = self.COLORS["convergence_low"]
            elif event.convergence_score < 0.75:
                conv_color = self.COLORS["convergence_mid"]
            else:
                conv_color = self.COLORS["convergence_high"]

            info.append(" • ", style=self.COLORS["dim"])
            info.append(f"Convergence: {event.convergence_score:.2f}", style=conv_color)

            # Add trend indicator if we have history
            if hasattr(self, "_last_convergence"):
                delta = event.convergence_score - self._last_convergence
                if delta > 0.05:
                    info.append(" ↑↑", style=conv_color)
                elif delta > 0:
                    info.append(" ↑", style=conv_color)
                elif delta < -0.05:
                    info.append(" ↓↓", style=conv_color)
                elif delta < 0:
                    info.append(" ↓", style=conv_color)
                else:
                    info.append(" →", style=conv_color)

            self._last_convergence = event.convergence_score

        # Add truncation indicator if truncation occurred
        if self.truncation_occurred:
            info.append(" • ", style=self.COLORS["dim"])
            info.append("✂", style="yellow")
            self.truncation_occurred = False  # Reset for next turn

        # Create a turn panel
        turn_panel = Panel(
            info,
            padding=(0, 1),
            border_style=self.COLORS["dim"],
            width=80,
            expand=False,
        )

        self.console.print()
        self.console.print(turn_panel, justify="center")
        self.console.print()

    def handle_end(self, event: ConversationEndEvent) -> None:
        """Display conversation end summary.

        Args:
            event: Conversation end event
        """
        # Build summary
        duration = event.duration_ms / 1000

        summary = Text()
        summary.append("◇ ", style=self.COLORS["header"])
        summary.append("Conversation Complete", style="bold")
        summary.append(f" • {event.total_turns} turns", style=self.COLORS["dim"])
        summary.append(f" • {duration:.1f}s", style=self.COLORS["dim"])

        # Add final convergence if available
        if hasattr(self, "_last_convergence"):
            if self._last_convergence < 0.5:
                conv_color = self.COLORS["convergence_low"]
            elif self._last_convergence < 0.75:
                conv_color = self.COLORS["convergence_mid"]
            else:
                conv_color = self.COLORS["convergence_high"]
            summary.append(
                f" • Final convergence: {self._last_convergence:.2f}", style=conv_color
            )

        # Create end panel
        end_panel = Panel(
            summary,
            padding=(1, 2),
            border_style=self.COLORS["header"],
            width=80,
            expand=False,
        )

        self.console.print()
        self.console.print(end_panel, justify="center")
        self.console.print()

    def handle_truncation(self, event: ContextTruncationEvent) -> None:
        """Display context truncation event.

        Args:
            event: Context truncation event
        """
        # Get agent name
        agent_name = "Unknown"
        if event.agent_id in self.agents:
            agent = self.agents[event.agent_id]
            agent_name = agent.display_name or agent.model

        # Build truncation info
        info = Text()
        info.append("⚠ Context Truncated", style="bold yellow")
        info.append(f" • {agent_name}", style="yellow")
        info.append(f" • Turn {event.turn_number}", style=self.COLORS["dim"])
        info.append(
            f" • {event.messages_dropped} messages dropped", style=self.COLORS["dim"]
        )
        info.append(
            f" • {event.truncated_message_count} remain", style=self.COLORS["dim"]
        )

        # Create truncation panel
        truncation_panel = Panel(
            info, padding=(0, 1), border_style="yellow", width=80, expand=False
        )

        self.console.print()
        self.console.print(truncation_panel, justify="center")
