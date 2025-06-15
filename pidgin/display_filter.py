"""Display filter for human-readable conversation output."""

from typing import Optional
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from rich.rule import Rule

from .events import (
    Event,
    ConversationStartEvent,
    ConversationEndEvent,
    TurnStartEvent,
    TurnCompleteEvent,
    MessageRequestEvent,
    MessageChunkEvent,
    MessageCompleteEvent,
    SystemPromptEvent,
    APIErrorEvent,
    ErrorEvent,
    ProviderTimeoutEvent,
)


class DisplayFilter:
    """Filters events for human-readable display."""

    # Nord color palette
    COLORS = {
        "nord0": "#2e3440",  # Background
        "nord3": "#4c566a",  # Muted gray
        "nord4": "#d8dee9",  # Light gray
        "nord7": "#8fbcbb",  # Teal - Setup
        "nord8": "#88c0d0",  # Light blue - Human
        "nord13": "#ebcb8b",  # Yellow - System
        "nord14": "#a3be8c",  # Green - Agent A
        "nord15": "#5e81ac",  # Blue - Agent B
    }

    def __init__(
        self,
        console: Console,
        mode: str = "normal",
        show_timing: bool = False,
        agents: Optional[dict] = None,
    ):
        """Initialize display filter.

        Args:
            console: Rich console for output
            mode: Display mode ('normal', 'quiet', 'verbose')
            show_timing: Whether to show timing information
            agents: Dict mapping agent_id to Agent objects
        """
        self.console = console
        self.mode = mode
        self.show_timing = show_timing
        self.current_turn = 0
        self.max_turns = 0
        self.agents = agents or {}

    def handle_event(self, event: Event) -> None:
        """Display events based on mode."""

        if self.mode == "verbose":
            # Show everything (keep existing EventLogger behavior)
            return  # Let EventLogger handle it

        elif self.mode == "quiet":
            # Only critical events
            if isinstance(event, ConversationStartEvent):
                self._show_quiet_start(event)
            elif isinstance(event, TurnCompleteEvent):
                self._show_quiet_turn(event)
            elif isinstance(event, ConversationEndEvent):
                self._show_quiet_end(event)

        else:  # normal mode
            if isinstance(event, ConversationStartEvent):
                self._show_conversation_start(event)
            elif isinstance(event, SystemPromptEvent):
                self._show_system_prompt(event)
            elif isinstance(event, MessageCompleteEvent):
                self._show_message(event)
            elif isinstance(event, TurnCompleteEvent):
                self._show_turn_complete(event)
            elif isinstance(event, APIErrorEvent):
                self._show_api_error(event)
            elif isinstance(event, ProviderTimeoutEvent):
                self._show_timeout_error(event)
            elif isinstance(event, ErrorEvent):
                self._show_error(event)
            elif isinstance(event, ConversationEndEvent):
                self._show_conversation_end(event)

    def _show_conversation_start(self, event: ConversationStartEvent):
        """Show conversation setup panel."""
        self.max_turns = event.max_turns

        # Use display names if available
        agent_a_display = event.agent_a_display_name or "Agent A"
        agent_b_display = event.agent_b_display_name or "Agent B"

        content = f"[bold]Starting Conversation[/bold]\n\n"
        content += f"◈ {agent_a_display}: {event.agent_a_model}\n"
        content += f"◈ {agent_b_display}: {event.agent_b_model}\n"
        content += f"◈ Max turns: {event.max_turns}\n\n"

        # Show initial prompt
        prompt_preview = event.initial_prompt
        if len(prompt_preview) > 100:
            prompt_preview = prompt_preview[:97] + "..."
        content += f"[bold]Initial Prompt:[/bold]\n{prompt_preview}"

        self.console.print(
            Panel(
                content,
                title="⬡ Conversation Setup",
                border_style=self.COLORS["nord7"],
                padding=(1, 2),
            )
        )
        self.console.print()

    def _show_system_prompt(self, event: SystemPromptEvent):
        """Show system context panel."""
        # Use display name if available, otherwise fallback to agent_id
        display_name = event.agent_display_name
        if not display_name:
            if event.agent_id in self.agents:
                display_name = self.agents[event.agent_id].display_name
            else:
                display_name = event.agent_id.replace("_", " ").title()
        
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

        self.console.print(
            Panel(
                f"[dim]System instructions:[/dim]\n\n{event.prompt}",
                title=title,
                border_style=style,
                padding=(1, 2),
            )
        )
        self.console.print()

    def _show_message(self, event: MessageCompleteEvent):
        """Show complete messages with agent info."""
        # Skip system messages in normal display (they're shown separately)
        if hasattr(event.message, "role") and event.message.role == "system":
            return

        # Get agent's display name and model shortname if available
        agent_name = None
        model_shortname = None
        if event.agent_id in self.agents:
            agent = self.agents[event.agent_id]
            agent_name = agent.display_name or event.agent_id
            model_shortname = agent.model_shortname

        # Determine styling based on agent
        if event.agent_id == "agent_a":
            # Build title with name and optional model shortname
            if model_shortname and agent_name != model_shortname and not agent_name.startswith(model_shortname):
                # Show both name and model shortname (e.g., "⬢ Kai (Haiku)")
                title = f"⬢ {agent_name} ({model_shortname})"
            else:
                # Just show the name (e.g., "⬢ Haiku-1" or "⬢ Agent A")
                title = f"⬢ {agent_name or 'Agent A'}"
            style = self.COLORS["nord14"]  # Green
        elif event.agent_id == "agent_b":
            # Build title with name and optional model shortname
            if model_shortname and agent_name != model_shortname and not agent_name.startswith(model_shortname):
                # Show both name and model shortname (e.g., "⬡ Zara (Sonnet)")
                title = f"⬡ {agent_name} ({model_shortname})"
            else:
                # Just show the name (e.g., "⬡ Sonnet-2" or "⬡ Agent B")
                title = f"⬡ {agent_name or 'Agent B'}"
            style = self.COLORS["nord15"]  # Blue
        elif "human" in event.agent_id.lower():
            title = f"◊ Human Intervention"
            style = self.COLORS["nord8"]  # Light blue
        else:
            title = f"⬨ {event.agent_id.title()}"
            style = self.COLORS["nord3"]  # Gray

        # Extract message content
        if hasattr(event.message, "content"):
            content = event.message.content
        else:
            content = str(event.message)

        if self.show_timing:
            timing_info = f"\n\n[dim]⟐ Duration: {event.duration_ms}ms | Tokens: {event.tokens_used}[/dim]"
            content += timing_info

        self.console.print(
            Panel(content, title=title, border_style=style, padding=(1, 2))
        )
        self.console.print()

    def _show_turn_complete(self, event: TurnCompleteEvent):
        """Show turn completion marker."""
        self.current_turn = event.turn_number + 1
        self.console.print(
            Rule(
                f"━━━ Turn {self.current_turn}/{self.max_turns} Complete ━━━",
                style=self.COLORS["nord3"],
            )
        )
        self.console.print()

    def _show_conversation_end(self, event: ConversationEndEvent):
        """Show conversation end panel."""
        duration = event.duration_ms / 1000  # Convert to seconds

        content = f"[bold]Conversation Complete[/bold]\n\n"
        content += f"◇ Total turns: {event.total_turns}\n"
        content += f"◇ Duration: {duration:.1f}s\n"
        content += f"◇ Reason: {event.reason}"

        self.console.print(
            Panel(
                content,
                title="⬟ Summary",
                border_style=self.COLORS["nord7"],
                padding=(1, 2),
            )
        )

    # Quiet mode methods
    def _show_quiet_start(self, event: ConversationStartEvent):
        """Minimal start display."""
        self.max_turns = event.max_turns
        self.console.print(
            f"[dim]Starting conversation ({event.max_turns} turns)...[/dim]"
        )

    def _show_quiet_turn(self, event: TurnCompleteEvent):
        """Minimal turn display."""
        self.current_turn = event.turn_number + 1
        self.console.print(
            f"[dim]Turn {self.current_turn}/{self.max_turns} complete[/dim]"
        )

    def _show_quiet_end(self, event: ConversationEndEvent):
        """Minimal end display."""
        self.console.print(
            f"[dim]Done. {event.total_turns} turns in {event.duration_ms/1000:.1f}s[/dim]"
        )

    def _show_api_error(self, event: APIErrorEvent):
        """Show API error with context."""
        # Get agent's display name if available
        agent_name = None
        if event.agent_id in self.agents:
            agent_name = self.agents[event.agent_id].display_name or event.agent_id

        # Build error content
        content = f"[bold red]API Error[/bold red]\n\n"
        content += f"◈ Agent: {agent_name or event.agent_id}\n"
        content += f"◈ Provider: {event.provider}\n"

        # Show error message
        error_msg = event.error_message
        if len(error_msg) > 200:
            error_msg = error_msg[:197] + "..."
        content += f"◈ Error: {error_msg}\n"

        # Show retry info
        if event.retryable:
            content += f"\n[yellow]⟳ This error is retryable. The system will attempt to recover.[/yellow]"
        else:
            content += f"\n[red]✗ This error cannot be automatically retried.[/red]"

        self.console.print(
            Panel(content, title="⚠ Error", border_style="red", padding=(1, 2))
        )
        self.console.print()

    def _show_error(self, event: ErrorEvent):
        """Show generic error."""
        content = (
            f"[bold red]{event.error_type.replace('_', ' ').title()}[/bold red]\n\n"
        )
        content += f"{event.error_message}"

        if event.context:
            content += f"\n\n[dim]Context: {event.context}[/dim]"

        self.console.print(
            Panel(content, title="⚠ Error", border_style="red", padding=(1, 2))
        )
        self.console.print()
        
    def _show_timeout_error(self, event: ProviderTimeoutEvent):
        """Show timeout error with options."""
        # Get agent's display name if available
        agent_name = None
        if event.agent_id in self.agents:
            agent_name = self.agents[event.agent_id].display_name or event.agent_id
            
        content = f"[bold yellow]Timeout[/bold yellow]\n\n"
        content += f"◈ Agent: {agent_name or event.agent_id}\n"
        content += f"◈ Timeout: {event.timeout_seconds}s\n"
        content += f"◈ {event.error_message}\n"
        
        if event.context:
            content += f"\n[dim]Context: {event.context}[/dim]"
            
        self.console.print(
            Panel(
                content,
                title="⏱ Timeout",
                border_style="yellow",
                padding=(1, 2)
            )
        )
        self.console.print()
