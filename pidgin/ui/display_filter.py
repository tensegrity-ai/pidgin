"""Display filter for human-readable conversation output."""

from typing import Optional
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from rich.rule import Rule

from ..core.events import (
    Event,
    ConversationStartEvent,
    ConversationEndEvent,
    TurnStartEvent,
    TurnCompleteEvent,
    MessageRequestEvent,
    MessageCompleteEvent,
    SystemPromptEvent,
    APIErrorEvent,
    ErrorEvent,
    ProviderTimeoutEvent,
    InterruptRequestEvent,
    ConversationPausedEvent,
    ConversationResumedEvent,
)


class DisplayFilter:
    """Filters events for human-readable display."""

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
    
    def _calculate_panel_width(self, content: str, title: str = "", min_width: int = 40, max_width: int = 80) -> int:
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
        from rich.text import Text
        lines = content.split('\n')
        
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
            elif isinstance(event, ConversationResumedEvent):
                self._show_resumed(event)

    def _show_conversation_start(self, event: ConversationStartEvent):
        """Show conversation setup panel."""
        self.console.print()  # Add newline before panel
        self.max_turns = event.max_turns

        # Use display names if available
        agent_a_display = event.agent_a_display_name or "Agent A"
        agent_b_display = event.agent_b_display_name or "Agent B"

        content = f"[bold]Starting Conversation[/bold]\n\n"
        content += f"◈ {agent_a_display}: {event.agent_a_model}"
        if event.temperature_a is not None:
            content += f" (temp: {event.temperature_a})"
        content += "\n"
        content += f"◈ {agent_b_display}: {event.agent_b_model}"
        if event.temperature_b is not None:
            content += f" (temp: {event.temperature_b})"
        content += "\n"
        content += f"◈ Max turns: {event.max_turns}\n"
        content += f"◈ [{self.COLORS['nord3']}]Press Ctrl+C to pause[/{self.COLORS['nord3']}]\n\n"

        # Show initial prompt
        content += f"[bold]Initial Prompt:[/bold]\n{event.initial_prompt}"

        # Calculate appropriate width
        width = self._calculate_panel_width(content, "⬡ Conversation Setup")

        self.console.print(
            Panel(
                content,
                title=" ⬡ Conversation Setup",
                title_align="left",
                border_style=self.COLORS["nord7"],
                padding=(1, 2),
                width=width,
                expand=False
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

        content = f"[{self.COLORS['nord3']}]System instructions:[/{self.COLORS['nord3']}]\n\n{event.prompt}"

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
        width = self._calculate_panel_width(content, title, min_width=50, max_width=70)

        self.console.print(
            Panel(
                content,
                title=f" {title}",
                title_align="left",
                border_style=style,
                padding=(1, 2),
                width=width,
                expand=False
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
            # Build name with optional model shortname
            if (
                model_shortname
                and agent_name != model_shortname
                and not agent_name.startswith(model_shortname)
            ):
                # Show both name and model shortname (e.g., "Kai (Haiku)")
                display_name = f"{agent_name} ({model_shortname})"
            else:
                # Just show the name (e.g., "Haiku-1" or "Agent A")
                display_name = agent_name or 'Agent A'
            glyph = "◆"
            color = self.COLORS["nord14"]  # Green
        elif event.agent_id == "agent_b":
            # Build name with optional model shortname
            if (
                model_shortname
                and agent_name != model_shortname
                and not agent_name.startswith(model_shortname)
            ):
                # Show both name and model shortname (e.g., "Zara (Sonnet)")
                display_name = f"{agent_name} ({model_shortname})"
            else:
                # Just show the name (e.g., "Sonnet-2" or "Agent B")
                display_name = agent_name or 'Agent B'
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
        from rich.text import Text
        text_width = min(self.console.width - 4, 80)
        wrapped_text = Text(content)
        self.console.print(wrapped_text, width=text_width, style="default")
        
        if self.show_timing:
            self.console.print(f"[{self.COLORS['nord3']}]⟐ Duration: {event.duration_ms}ms | Tokens: {event.tokens_used}[/{self.COLORS['nord3']}]")
        
        self.console.print()  # Add spacing after message

    def _show_turn_complete(self, event: TurnCompleteEvent):
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
                plain_turn_info = f"Turn {self.current_turn}/{self.max_turns} | {conv_text}"
                turn_info += f" | [{self.COLORS['nord13']}]{conv_text}[/{self.COLORS['nord13']}]"
            else:
                plain_turn_info = f"Turn {self.current_turn}/{self.max_turns} | {conv_text}"
                turn_info += f" | {conv_text}"
        else:
            plain_turn_info = f"Turn {self.current_turn}/{self.max_turns}"
        
        # Calculate padding for centering
        padding = max(0, (separator_width - len(plain_turn_info)) // 2)
        centered_info = " " * padding + turn_info
        
        # Print centered separators and info
        self.console.print(f"\n[{self.COLORS['nord3']}]{'─' * separator_width}[/{self.COLORS['nord3']}]")
        self.console.print(f"[{self.COLORS['nord3']}]{centered_info}[/{self.COLORS['nord3']}]")
        self.console.print(f"[{self.COLORS['nord3']}]{'─' * separator_width}[/{self.COLORS['nord3']}]\n")

    def _show_conversation_end(self, event: ConversationEndEvent):
        """Show conversation end panel."""
        duration = event.duration_ms / 1000  # Convert to seconds

        content = f"[bold]Conversation Complete[/bold]\n\n"
        content += f"◇ Total turns: {event.total_turns}\n"
        content += f"◇ Duration: {duration:.1f}s\n"
        
        # Enhanced reason display for convergence
        if event.reason == "high_convergence":
            content += f"◇ Reason: Convergence threshold reached\n"
            content += f"[dim]  (Stopped to prevent token waste)[/dim]"
        else:
            content += f"◇ Reason: {event.reason}"

        # Summary panels should be compact
        width = self._calculate_panel_width(content, "⬟ Summary", min_width=40, max_width=60)

        self.console.print(
            Panel(
                content,
                title=" ⬟ Summary",
                title_align="left",
                border_style=self.COLORS["nord7"],
                padding=(1, 2),
                width=width,
                expand=False
            )
        )

    # Quiet mode methods
    def _show_quiet_start(self, event: ConversationStartEvent):
        """Minimal start display."""
        self.max_turns = event.max_turns
        self.console.print(
            f"[{self.COLORS['nord3']}]Starting conversation ({event.max_turns} turns)...[/{self.COLORS['nord3']}]"
        )

    def _show_quiet_turn(self, event: TurnCompleteEvent):
        """Minimal turn display."""
        self.current_turn = event.turn_number + 1
        self.console.print(
            f"[{self.COLORS['nord3']}]Turn {self.current_turn}/{self.max_turns} complete[/{self.COLORS['nord3']}]"
        )

    def _show_quiet_end(self, event: ConversationEndEvent):
        """Minimal end display."""
        self.console.print(
            f"[{self.COLORS['nord3']}]Done. {event.total_turns} turns in {event.duration_ms/1000:.1f}s[/{self.COLORS['nord3']}]"
        )

    def _show_api_error(self, event: APIErrorEvent):
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

            content = f"[bold {self.COLORS['nord13']}]{agent_name or event.agent_id} cannot respond[/bold {self.COLORS['nord13']}]\n\n"
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
        width = self._calculate_panel_width(content, title, min_width=40, max_width=80)
        
        self.console.print(
            Panel(
                content,
                title=title,
                title_align="left",
                border_style=border_style,
                padding=(1, 2),
                width=width,
                expand=False
            )
        )
        self.console.print()

    def _show_error(self, event: ErrorEvent):
        """Show generic error."""
        content = f"[bold {self.COLORS['nord11']}]{event.error_type.replace('_', ' ').title()}[/bold {self.COLORS['nord11']}]\n\n"
        content += f"{event.error_message}"

        if event.context:
            content += f"\n\n[{self.COLORS['nord3']}]Context: {event.context}[/{self.COLORS['nord3']}]"

        # Calculate appropriate width
        width = self._calculate_panel_width(content, "! Error", min_width=40, max_width=80)

        self.console.print(
            Panel(
                content,
                title=" ! Error",
                title_align="left",
                border_style=self.COLORS["nord11"],
                padding=(1, 2),
                width=width,
                expand=False
            )
        )
        self.console.print()

    def _show_timeout_error(self, event: ProviderTimeoutEvent):
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
        width = self._calculate_panel_width(content, "⏱ Timeout", min_width=40, max_width=70)

        self.console.print(
            Panel(
                content,
                title=" ⏱ Timeout",
                title_align="left",
                border_style=self.COLORS["nord13"],
                padding=(1, 2),
                width=width,
                expand=False
            )
        )
        self.console.print()

    def _show_resumed(self, event: ConversationResumedEvent):
        """Show conversation resumed notification."""
        self.console.print(
            f"\n[{self.COLORS['nord14']}]▶ Conversation resumed[/{self.COLORS['nord14']}]\n"
        )

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
        width = self._calculate_panel_width(content, "", min_width=35, max_width=50)
        
        self.console.print()  # Leading newline
        self.console.print(
            Panel(
                content,
                style=self.COLORS['nord13'],  # Yellow
                border_style=self.COLORS['nord3'],  # Dim border
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
