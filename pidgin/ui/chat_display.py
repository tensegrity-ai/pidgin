"""Chat display for watching conversations with minimal metadata."""

from typing import Dict, Union

from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from ..core.event_bus import EventBus
from ..core.events import (
    ContextTruncationEvent,
    ConversationEndEvent,
    ConversationStartEvent,
    MessageCompleteEvent,
    SystemPromptEvent,
    ThinkingCompleteEvent,
    TurnCompleteEvent,
)
from ..core.types import Agent


class ChatDisplay:
    """Chat display showing messages and turn markers."""

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
        """Initialize chat display.

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
        self._last_convergence: float = 0.0
        self._shown_prompts: set = (
            set()
        )  # Track (agent_id, prompt_hash) to avoid duplicates

        # Subscribe to relevant events
        bus.subscribe(SystemPromptEvent, self.handle_system_prompt)
        bus.subscribe(ConversationStartEvent, self.handle_start)
        bus.subscribe(ThinkingCompleteEvent, self.handle_thinking)
        bus.subscribe(MessageCompleteEvent, self.handle_message)
        bus.subscribe(TurnCompleteEvent, self.handle_turn_complete)
        bus.subscribe(ConversationEndEvent, self.handle_end)
        bus.subscribe(ContextTruncationEvent, self.handle_truncation)

    def calculate_bubble_width(self) -> int:
        """Calculate responsive bubble width based on terminal size.

        Bubbles are 70% of terminal width so they overlap horizontally.
        Capped at 70 chars to maintain readability on wide terminals.
        """
        terminal_width = self.console.size.width
        if terminal_width >= 100:
            return min(int(terminal_width * 0.70), 70)
        elif terminal_width >= 80:
            return int(terminal_width * 0.75)
        else:
            return max(int(terminal_width * 0.90), 40)

    def calculate_margins(self) -> tuple[int, int]:
        """Calculate left and right margins for bubble positioning.

        Returns:
            Tuple of (left_margin, right_margin) for Agent A and B respectively.
            On wide terminals, includes centering offset to keep content in a
            virtual 100-char stage.
        """
        terminal_width = self.console.size.width
        if terminal_width > 100:
            # Center a virtual 100-char stage
            center_offset = (terminal_width - 100) // 2
            return (center_offset + 3, center_offset + 3)
        elif terminal_width >= 100:
            return (3, 3)
        elif terminal_width >= 80:
            margin = int(terminal_width * 0.02)
            return (margin, margin)
        else:
            return (0, 0)

    def print_bubble(self, panel: Panel, agent_id: str) -> None:
        """Print a bubble with appropriate alignment and margins.

        Agent A: left-aligned within centered stage
        Agent B: right-aligned within centered stage
        """
        left_margin, right_margin = self.calculate_margins()
        if agent_id == "agent_b":
            if right_margin > 0:
                self.console.print(Padding(Align.right(panel), (0, right_margin, 0, 0)))
            else:
                self.console.print(Align.right(panel))
        else:
            if left_margin > 0:
                self.console.print(Padding(panel, (0, 0, 0, left_margin)))
            else:
                self.console.print(panel)

    def handle_system_prompt(self, event: SystemPromptEvent) -> None:
        """Display system prompt for an agent.

        Args:
            event: System prompt event
        """
        # Skip if we've shown this exact prompt for this agent
        key = (event.agent_id, hash(event.prompt))
        if key in self._shown_prompts:
            return
        self._shown_prompts.add(key)

        # Get agent info
        agent_name = event.agent_display_name
        if not agent_name and event.agent_id in self.agents:
            agent_name = self.agents[event.agent_id].display_name
        if not agent_name:
            agent_name = event.agent_id.replace("_", " ").title()

        # Set color and symbol based on agent
        if event.agent_id == "agent_a":
            color = self.COLORS["agent_a"]
            symbol = "◆"
        elif event.agent_id == "agent_b":
            color = self.COLORS["agent_b"]
            symbol = "●"
        else:
            color = self.COLORS["dim"]
            symbol = "○"

        # Build header
        header = Text()
        header.append(f"{symbol} ", style=color)
        header.append(f"System Context - {agent_name}", style=color + " bold")

        # Create panel with responsive width
        panel = Panel(
            event.prompt,
            title=header,
            title_align="left",
            border_style=color,
            padding=(1, 2),
            width=self.calculate_bubble_width(),
            expand=False,
        )

        # Center system prompts (they're setup info, not conversation)
        self.console.print()
        self.console.print(Align.center(panel))

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

        # Build header with agent symbols on both sides
        agent_a_name = event.agent_a_display_name or "Agent A"
        agent_b_name = event.agent_b_display_name or "Agent B"

        header = Text()
        header.append("◆ ", style=self.COLORS["agent_a"])
        header.append(f"{agent_a_name} ", style=self.COLORS["agent_a"] + " bold")
        header.append("↔ ", style=self.COLORS["dim"])
        header.append(f"{agent_b_name} ", style=self.COLORS["agent_b"] + " bold")
        header.append("●", style=self.COLORS["agent_b"])

        self.console.print()
        self.console.print(header, justify="center")

        # Show initial prompt (or [Begin] for cold starts)
        from ..config import Config

        config = Config()
        human_tag = config.get("defaults.human_tag", "")
        initial_text = event.initial_prompt if event.initial_prompt else "[Begin]"

        # Format prompt as agents see it
        if human_tag:
            prompt_content = f"{human_tag}: {initial_text}"
        else:
            prompt_content = initial_text

        prompt_panel = Panel(
            prompt_content,
            title="[bold]Initial Prompt[/bold]",
            title_align="left",
            border_style=self.COLORS["header"],
            padding=(1, 2),
            width=self.calculate_bubble_width(),
            expand=False,
        )

        self.console.print()
        self.console.print(Align.center(prompt_panel))
        self.console.print()

    def handle_thinking(self, event: ThinkingCompleteEvent) -> None:
        """Display thinking/reasoning trace.

        Args:
            event: Thinking complete event
        """
        # Get agent info
        agent_name = "Unknown"
        color = self.COLORS["dim"]

        if event.agent_id in self.agents:
            agent = self.agents[event.agent_id]
            agent_name = agent.display_name or agent.model

            if event.agent_id == "agent_a":
                color = self.COLORS["agent_a"]
            elif event.agent_id == "agent_b":
                color = self.COLORS["agent_b"]

        # Format thinking content - show first/last parts if very long
        content = event.thinking_content
        max_chars = 2000
        if len(content) > max_chars:
            half = max_chars // 2
            content = f"{content[:half]}\n\n[...{len(content) - max_chars} chars omitted...]\n\n{content[-half:]}"

        # Create styled header
        header_text = Text()
        header_text.append(f"{agent_name} ", style=color)
        header_text.append("thinking", style=f"{color} dim italic")
        if event.thinking_tokens:
            header_text.append(f" ({event.thinking_tokens} tokens)", style="dim")

        # Render as dimmed italic panel
        thinking_panel = Panel(
            Text(content, style="dim italic"),
            title=header_text,
            title_align="left",
            border_style=f"{color} dim",
            padding=(1, 2),
            width=self.calculate_bubble_width(),
            expand=False,
        )

        self.console.print()
        self.print_bubble(thinking_panel, event.agent_id)

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
        content_display: Union[Markdown, Text]
        if any(marker in content for marker in ["```", "**", "*", "#", "-", "1."]):
            try:
                content_display = Markdown(content, code_theme="nord")
            except (ValueError, AttributeError, Exception):
                # Markdown parsing failed, fall back to plain text
                content_display = Text(content, style="default")
        else:
            content_display = Text(content, style="default")

        # Create panel with agent name as title and responsive width
        message_panel = Panel(
            content_display,
            title=name_text,
            title_align="left",
            border_style=color,
            padding=(1, 2),
            width=self.calculate_bubble_width(),
            expand=False,
        )

        self.console.print()
        self.print_bubble(message_panel, event.agent_id)

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

            info.append(" | ", style=self.COLORS["dim"])
            info.append(f"{event.convergence_score:.2f}", style=conv_color)

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
            info.append(" ✂", style="yellow")
            self.truncation_occurred = False  # Reset for next turn

        # Use dotted Rule instead of Panel
        self.console.print()
        self.console.print(Rule(info, style=self.COLORS["dim"], characters="·"))
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
            summary.append(f" • {self._last_convergence:.2f}", style=conv_color)

        # Simple centered text instead of panel
        self.console.print()
        self.console.print(summary, justify="center")
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

        # Create truncation panel with responsive width
        truncation_panel = Panel(
            info,
            padding=(0, 1),
            border_style="yellow",
            width=self.calculate_bubble_width(),
            expand=False,
        )

        self.console.print()
        self.console.print(Align.center(truncation_panel))
