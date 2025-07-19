"""Tail display for showing formatted event stream in console."""

from typing import Dict, Optional

from rich.console import Console
from rich.text import Text

from ..core.event_bus import EventBus
from ..core.events import (
    APIErrorEvent,
    ContextTruncationEvent,
    ConversationEndEvent,
    ConversationPausedEvent,
    ConversationResumedEvent,
    ConversationStartEvent,
    Event,
    InterruptRequestEvent,
    MessageChunkEvent,
    MessageCompleteEvent,
    MessageRequestEvent,
    ProviderTimeoutEvent,
    RateLimitPaceEvent,
    SystemPromptEvent,
    TokenUsageEvent,
    TurnCompleteEvent,
    TurnStartEvent,
)


class TailDisplay:
    """Display formatted event stream in console."""

    # Nord color palette
    NORD_GREEN = "#a3be8c"
    NORD_RED = "#bf616a"
    NORD_BLUE = "#5e81ac"
    NORD_CYAN = "#88c0d0"
    NORD_YELLOW = "#ebcb8b"
    NORD_ORANGE = "#d08770"
    NORD_PURPLE = "#b48ead"
    NORD_GRAY = "#4c566a"
    NORD_LIGHT = "#d8dee9"

    EVENT_COLORS = {
        ConversationStartEvent: NORD_GREEN,
        ConversationEndEvent: NORD_RED,
        TurnStartEvent: NORD_BLUE,
        TurnCompleteEvent: NORD_BLUE,
        MessageRequestEvent: NORD_YELLOW,
        MessageCompleteEvent: NORD_CYAN,
        SystemPromptEvent: NORD_GRAY,
        APIErrorEvent: NORD_RED,
        ContextTruncationEvent: NORD_ORANGE,
        RateLimitPaceEvent: NORD_PURPLE,
        TokenUsageEvent: NORD_CYAN,
        ProviderTimeoutEvent: NORD_ORANGE,
        InterruptRequestEvent: NORD_RED,
        ConversationPausedEvent: NORD_YELLOW,
        ConversationResumedEvent: NORD_GREEN,
    }

    EVENT_GLYPHS = {
        ConversationStartEvent: "◆",
        ConversationEndEvent: "◇",
        TurnStartEvent: "▶",
        TurnCompleteEvent: "■",
        MessageRequestEvent: "→",
        MessageCompleteEvent: "✓",
        MessageChunkEvent: "·",
        SystemPromptEvent: "⚙",
        APIErrorEvent: "✗",
        ContextTruncationEvent: "⚠",
        RateLimitPaceEvent: "⧖",
        TokenUsageEvent: "◉",
        ProviderTimeoutEvent: "⟡",
        InterruptRequestEvent: "⚡",
        ConversationPausedEvent: "⏸",
        ConversationResumedEvent: "▶",
    }

    def __init__(self, bus: EventBus, console: Console):
        """Initialize tail display and subscribe to ALL events.

        Args:
            bus: The event bus to monitor
            console: Rich console for output
        """
        self.bus = bus
        self.console = console
        self.chunk_buffer = {}  # Buffer for message chunks
        
        # Store agent display names from ConversationStartEvent
        self.agent_display_names: Dict[str, str] = {}

        # Subscribe to ALL events
        bus.subscribe(Event, self.log_event)

    def _format_agent_id(self, agent_id: str) -> str:
        """Format agent ID with consistent color.

        Args:
            agent_id: The agent identifier

        Returns:
            Formatted agent ID with color markup
        """
        agent_color = self.NORD_GREEN if agent_id == "agent_a" else self.NORD_BLUE
        # Use display name if available, otherwise fall back to agent_id
        display_text = self.agent_display_names.get(agent_id, agent_id)
        return f"[{agent_color}]{display_text}[/{agent_color}]"

    def log_event(self, event: Event) -> None:
        """Display an event with beautiful Rich formatting.

        Args:
            event: The event to log
        """
        # Skip if no console provided (file-only logging)
        if self.console is None:
            return

        # Handle message chunks separately
        if isinstance(event, MessageChunkEvent):
            self._handle_message_chunk(event)
            return

        # Get event type and metadata
        event_type = type(event)
        color = self.EVENT_COLORS.get(event_type, self.NORD_LIGHT)
        glyph = self.EVENT_GLYPHS.get(event_type, "●")

        # Format timestamp
        timestamp = event.timestamp.strftime("%H:%M:%S.%f")[:-3]

        # Create title with event type
        event_name = event_type.__name__

        # Build header
        header = Text()
        header.append(f"[{timestamp}] ", style=self.NORD_GRAY)
        header.append(f"{glyph} {event_name}", style=color + " bold")

        # Display based on event type
        if isinstance(event, ConversationStartEvent):
            self._display_conversation_start(event, header, color)
        elif isinstance(event, ConversationEndEvent):
            self._display_conversation_end(event, header, color)
        elif isinstance(event, TurnStartEvent):
            self._display_turn_start(event, header)
        elif isinstance(event, TurnCompleteEvent):
            self._display_turn_complete(event, header)
        elif isinstance(event, MessageRequestEvent):
            self._display_message_request(event, header)
        elif isinstance(event, MessageCompleteEvent):
            self._display_message_complete(event, header, color)
        elif isinstance(event, APIErrorEvent):
            self._display_api_error(event, header, color)
        elif isinstance(event, ContextTruncationEvent):
            self._display_context_truncation(event, header, color)
        elif isinstance(event, SystemPromptEvent):
            self._display_system_prompt(event, header)
        elif isinstance(event, RateLimitPaceEvent):
            self._display_rate_limit(event, header)
        elif isinstance(event, TokenUsageEvent):
            self._display_token_usage(event, header)
        elif isinstance(event, ProviderTimeoutEvent):
            self._display_provider_timeout(event, header, color)
        elif isinstance(event, InterruptRequestEvent):
            self._display_interrupt_request(event, header)
        elif isinstance(event, ConversationPausedEvent):
            self._display_conversation_paused(event, header)
        elif isinstance(event, ConversationResumedEvent):
            self._display_conversation_resumed(event, header)
        else:
            # Generic event display
            self._display_generic_event(event, header)

    def _display_conversation_start(
        self, event: ConversationStartEvent, header: Text, color: str
    ) -> None:
        """Display conversation start event."""
        # Store agent display names for later use
        if event.agent_a_display_name:
            self.agent_display_names["agent_a"] = event.agent_a_display_name
        if event.agent_b_display_name:
            self.agent_display_names["agent_b"] = event.agent_b_display_name
            
        # Format as single line with key info
        content = f"id: {event.conversation_id[:12]}... | "
        content += f"{event.agent_a_model} ↔ {event.agent_b_model} | "
        content += f"max_turns: {event.max_turns}"

        self.console.print(header, content)

        # Show initial prompt on next line if present (with human tag as agents see it)
        if event.initial_prompt:
            # Get human tag from config
            from ..config import Config

            config = Config()
            human_tag = config.get("defaults.human_tag", "[HUMAN]")

            # Format prompt as agents see it
            if human_tag:
                full_prompt = f"{human_tag}: {event.initial_prompt}"
            else:
                full_prompt = event.initial_prompt

            prompt_truncated = full_prompt.strip().replace("\n", " ")
            if len(prompt_truncated) > 100:  # Increased limit to accommodate human tag
                prompt_truncated = prompt_truncated[:97] + "..."

            prompt_header = Text()
            prompt_header.append(
                f"[{event.timestamp.strftime('%H:%M:%S.%f')[:-3]}] ",
                style=self.NORD_GRAY,
            )
            prompt_header.append("◆ InitialPrompt", style=self.NORD_CYAN + " bold")

            self.console.print(prompt_header, prompt_truncated)

    def _display_conversation_end(
        self, event: ConversationEndEvent, header: Text, color: str
    ) -> None:
        """Display conversation end event."""
        # Format reason nicely
        reason_map = {
            "max_turns_reached": "max_turns",
            "high_convergence": "convergence",
            "interrupted": "interrupted",
            "error": "error",
        }
        reason_display = reason_map.get(event.reason, event.reason)

        # Format duration
        duration_str = ""
        if hasattr(event, "duration_ms") and event.duration_ms:
            duration_s = event.duration_ms / 1000
            if duration_s < 60:
                duration_str = f"{duration_s:.1f}s"
            else:
                minutes = int(duration_s // 60)
                seconds = int(duration_s % 60)
                duration_str = f"{minutes}m {seconds}s"

        # Format as single line
        content = f"reason: {reason_display} | turns: {event.total_turns}"
        if duration_str:
            content += f" | duration: {duration_str}"

        self.console.print(header, content)

    def _display_turn_start(self, event: TurnStartEvent, header: Text) -> None:
        """Display turn start event."""
        self.console.print(header, f"Turn {event.turn_number}")

    def _display_turn_complete(self, event: TurnCompleteEvent, header: Text) -> None:
        """Display turn complete event."""
        content = f"turn: {event.turn_number}"
        if event.convergence_score is not None:
            content += f" | convergence: {event.convergence_score:.3f}"
        self.console.print(header, content)

    def _display_message_request(
        self, event: MessageRequestEvent, header: Text
    ) -> None:
        """Display message request event."""
        self.console.print(
            header, f"{self._format_agent_id(event.agent_id)} thinking..."
        )

    def _display_message_complete(
        self, event: MessageCompleteEvent, header: Text, color: str
    ) -> None:
        """Display message complete event."""
        # Get message content
        msg_content = (
            event.message.content
            if hasattr(event.message, "content")
            else str(event.message)
        )

        # Truncate message to first line, max 20 chars
        msg_lines = msg_content.strip().replace("\n", " ").split()
        truncated_msg = " ".join(msg_lines)
        if len(truncated_msg) > 20:
            truncated_msg = truncated_msg[:17] + "..."

        # Build metadata
        metadata = []
        if hasattr(event, "duration_ms") and event.duration_ms is not None:
            metadata.append(f"{event.duration_ms/1000:.1f}s")
        if hasattr(event, "tokens_used") and event.tokens_used:
            metadata.append(f"{event.tokens_used}tok")

        # Format as single line
        content = f"{self._format_agent_id(event.agent_id)}: {truncated_msg}"
        if metadata:
            content += f" [{self.NORD_GRAY}]({' | '.join(metadata)})[/{self.NORD_GRAY}]"

        self.console.print(header, content)

    def _handle_message_chunk(self, event: MessageChunkEvent) -> None:
        """Handle message chunks."""
        # Get chunk content with correct attribute name
        chunk_content = (
            event.chunk if hasattr(event, "chunk") else getattr(event, "content", "")
        )

        # Format as single line with timestamp
        timestamp = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
        header = Text()
        header.append(f"[{timestamp}] ", style=self.NORD_GRAY)
        header.append("· MessageChunk", style=self.NORD_PURPLE + " bold")

        # Truncate chunk to 20 chars
        truncated_chunk = chunk_content.strip().replace("\n", " ")
        if len(truncated_chunk) > 20:
            truncated_chunk = truncated_chunk[:17] + "..."

        content = f"{self._format_agent_id(event.agent_id)}: {truncated_chunk}"
        self.console.print(header, content)

    def _display_api_error(
        self, event: APIErrorEvent, header: Text, color: str
    ) -> None:
        """Display API error event."""
        # Truncate error message for single line
        error_msg = event.error_message.strip().replace("\n", " ")
        if len(error_msg) > 60:
            error_msg = error_msg[:57] + "..."

        content = f"{event.provider} | {event.error_type}: {error_msg}"
        self.console.print(header, content)

    def _display_context_truncation(
        self, event: ContextTruncationEvent, header: Text, color: str
    ) -> None:
        """Display context truncation event."""
        content = (
            f"{self._format_agent_id(event.agent_id)} | removed "
            f"{event.messages_dropped} msgs | "
        )
        content += (
            f"{event.original_message_count} → {event.truncated_message_count} msgs"
        )
        self.console.print(header, content)

    def _display_system_prompt(self, event: SystemPromptEvent, header: Text) -> None:
        """Display system prompt event."""
        # Truncate system prompt for single line display
        if hasattr(event, "prompt") and event.prompt:
            prompt_truncated = event.prompt.strip().replace("\n", " ")
            if len(prompt_truncated) > 60:
                prompt_truncated = prompt_truncated[:57] + "..."
            self.console.print(
                header, f"{self._format_agent_id(event.agent_id)}: {prompt_truncated}"
            )
        else:
            self.console.print(
                header,
                f"{self._format_agent_id(event.agent_id)} system prompt configured",
            )

    def _display_generic_event(self, event: Event, header: Text) -> None:
        """Display generic event."""
        # Convert event to dict and format key fields
        event_dict = event.dict()
        event_dict.pop("timestamp", None)  # Already in header
        event_dict.pop("event_id", None)  # Not useful for display

        # Format as single line with key values
        content_parts = []
        for key, value in event_dict.items():
            if value is not None and value != "":
                if isinstance(value, str) and len(value) > 30:
                    value = value[:27] + "..."
                content_parts.append(f"{key}: {value}")

        if content_parts:
            content = " | ".join(content_parts[:3])  # Limit to 3 most important fields
            self.console.print(header, content)
        else:
            self.console.print(header, "(no data)")

    def _display_rate_limit(self, event: RateLimitPaceEvent, header: Text) -> None:
        """Display rate limit event."""
        # Make reason more human-readable
        if event.reason == "mixed":
            reason_str = "(request + token limits)"
        elif event.reason == "request_rate":
            reason_str = "(request limit)"
        elif event.reason == "token_rate":
            reason_str = "(token limit)"
        else:
            reason_str = f"({event.reason})"

        content = f"Waiting {event.wait_time:.1f}s for {event.provider} {reason_str}"
        self.console.print(header, content)

    def _display_token_usage(self, event: TokenUsageEvent, header: Text) -> None:
        """Display token usage event."""
        usage_rate_pct = (
            (event.current_usage_rate / event.tokens_per_minute_limit * 100)
            if event.tokens_per_minute_limit > 0
            else 0
        )
        content = (
            f"{event.provider}: {event.tokens_used} tokens | "
            f"{usage_rate_pct:.0f}% of limit ({event.tokens_per_minute_limit}/min)"
        )
        self.console.print(header, content)

    def _display_provider_timeout(
        self, event: ProviderTimeoutEvent, header: Text, color: str
    ) -> None:
        """Display provider timeout event."""
        content = (
            f"{self._format_agent_id(event.agent_id)} | {event.error_type}: "
            f"{event.error_message} (timeout: {event.timeout_seconds}s)"
        )
        self.console.print(header, content)

    def _display_interrupt_request(
        self, event: InterruptRequestEvent, header: Text
    ) -> None:
        """Display interrupt request event."""
        content = f"Interrupt from {event.interrupt_source} at turn {event.turn_number}"
        self.console.print(header, content)

    def _display_conversation_paused(
        self, event: ConversationPausedEvent, header: Text
    ) -> None:
        """Display conversation paused event."""
        content = f"Paused at turn {event.turn_number} ({event.paused_during})"
        self.console.print(header, content)

    def _display_conversation_resumed(
        self, event: ConversationResumedEvent, header: Text
    ) -> None:
        """Display conversation resumed event."""
        content = f"Resumed at turn {event.turn_number}"
        self.console.print(header, content)

    def _format_event_content(self, event: Event) -> str:
        """Legacy format method for backward compatibility.

        Args:
            event: The event to format

        Returns:
            Formatted content string
        """
        if isinstance(event, ConversationStartEvent):
            content = (
                f"  conversation_id: {event.conversation_id}\n"
                f"  agent_a: {event.agent_a_model}"
            )
            if event.temperature_a is not None:
                content += f" (temp: {event.temperature_a})"
            content += f"\n  agent_b: {event.agent_b_model}"
            if event.temperature_b is not None:
                content += f" (temp: {event.temperature_b})"
            content += (
                f"\n  initial_prompt: {event.initial_prompt[:50]}..."
                f"\n  max_turns: {event.max_turns}"
            )
            return content

        elif isinstance(event, ConversationEndEvent):
            return (
                f"  conversation_id: {event.conversation_id}\n"
                f"  reason: {event.reason}\n"
                f"  final_convergence: {event.final_convergence}\n"
                f"  total_turns: {event.total_turns}\n"
                f"  duration: {event.duration_ms}ms"
            )

        elif isinstance(event, TurnStartEvent):
            return f"  turn {event.turn_number} of {event.max_turns}"

        elif isinstance(event, TurnCompleteEvent):
            content = f"  turn {event.turn_number} complete\n"
            if event.convergence_score is not None:
                content += f"  convergence: {event.convergence_score:.3f}\n"
            content += f"  messages: {event.turn_messages}"
            return content

        elif isinstance(event, MessageRequestEvent):
            return f"  {event.agent_id} generating response..."

        elif isinstance(event, MessageCompleteEvent):
            msg = event.message
            content = f"  agent: {event.agent_id}\n"
            # Handle both string messages and Message objects
            if hasattr(msg, "content"):
                content += f"  content: {msg.content[:100]}..."
            else:
                content += f"  content: {str(msg)[:100]}..."

            if event.duration is not None:
                content += f"\n  duration: {event.duration:.2f}s"
            return content

        elif isinstance(event, MessageChunkEvent):
            # For chunks, return just the content - these are displayed inline
            return event.content

        else:
            # Generic fallback - show all fields
            event_dict = event.dict()
            # Remove timestamp as it's in the header
            event_dict.pop("timestamp", None)

            lines = []
            for key, value in event_dict.items():
                if value is not None:
                    lines.append(f"  {key}: {value}")

            return "\n".join(lines) if lines else "  (no data)"
