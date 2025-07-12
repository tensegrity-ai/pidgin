"""Tail display for showing formatted event stream in console."""

from datetime import datetime
from typing import Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from ..core.event_bus import EventBus
from ..core.events import (
    Event,
    ConversationStartEvent,
    ConversationEndEvent,
    TurnStartEvent,
    TurnCompleteEvent,
    MessageRequestEvent,
    MessageCompleteEvent,
    MessageChunkEvent,
    SystemPromptEvent,
    APIErrorEvent,
    ContextTruncationEvent,
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
        
        # Subscribe to ALL events
        bus.subscribe(Event, self.log_event)
        
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
        else:
            # Generic event display
            self._display_generic_event(event, header)
    
    def _display_conversation_start(self, event: ConversationStartEvent, header: Text, color: str) -> None:
        """Display conversation start event."""
        table = Table.grid(padding=1)
        table.add_column(style=self.NORD_GRAY)
        table.add_column()
        
        table.add_row("conversation_id:", event.conversation_id)
        table.add_row("agent_a:", f"{event.agent_a_model} (temp: {event.temperature_a or 'default'})")
        table.add_row("agent_b:", f"{event.agent_b_model} (temp: {event.temperature_b or 'default'})")
        table.add_row("max_turns:", str(event.max_turns))
        
        panel = Panel(
            table,
            title=header,
            title_align="left",
            border_style=color,
            expand=False
        )
        self.console.print(panel)
        
        # Show initial prompt as a regular event if present
        if event.initial_prompt:
            # Create a fake event-style display for initial prompt
            prompt_header = Text()
            prompt_header.append(f"[{event.timestamp.strftime('%H:%M:%S.%f')[:-3]}] ", style=self.NORD_GRAY)
            prompt_header.append("◆ ", style=self.NORD_CYAN)
            prompt_header.append("InitialPrompt", style=self.NORD_CYAN)
            
            self.console.print(prompt_header, event.initial_prompt)
        self.console.print()
    
    def _display_conversation_end(self, event: ConversationEndEvent, header: Text, color: str) -> None:
        """Display conversation end event."""
        # Format reason nicely
        reason_map = {
            "max_turns_reached": "Max turns reached",
            "high_convergence": "High convergence detected",
            "interrupted": "User interrupted",
            "error": "Error occurred"
        }
        reason_display = reason_map.get(event.reason, event.reason)
        
        content = f"Reason: {reason_display}\n"
        content += f"Total turns: {event.total_turns}\n"
        
        # Format duration
        if hasattr(event, 'duration_ms') and event.duration_ms:
            duration_s = event.duration_ms / 1000
            if duration_s < 60:
                content += f"Duration: {duration_s:.1f}s"
            else:
                minutes = int(duration_s // 60)
                seconds = int(duration_s % 60)
                content += f"Duration: {minutes}m {seconds}s"
        
        # Add convergence if available
        if hasattr(event, 'final_convergence') and event.final_convergence is not None:
            content += f"\nFinal convergence: {event.final_convergence:.3f}"
        
        panel = Panel(
            content,
            title=header,
            title_align="left",
            border_style=color,
            expand=False
        )
        self.console.print(panel)
        self.console.print()
    
    def _display_turn_start(self, event: TurnStartEvent, header: Text) -> None:
        """Display turn start event."""
        self.console.print(header, f"Turn {event.turn_number}")
    
    def _display_turn_complete(self, event: TurnCompleteEvent, header: Text) -> None:
        """Display turn complete event."""
        content = f"turn: {event.turn_number}"
        if event.convergence_score is not None:
            content += f" | convergence: {event.convergence_score:.3f}"
        self.console.print(header, content)
        self.console.print()
    
    def _display_message_request(self, event: MessageRequestEvent, header: Text) -> None:
        """Display message request event."""
        self.console.print(header, f"{event.agent_id} thinking...")
    
    def _display_message_complete(self, event: MessageCompleteEvent, header: Text, color: str) -> None:
        """Display message complete event."""
        # Get agent color
        agent_color = self.NORD_GREEN if event.agent_id == "agent_a" else self.NORD_BLUE
        
        # Format message content
        content = Text()
        content.append(f"{event.agent_id}: ", style=agent_color + " bold")
        content.append(event.message.content if hasattr(event.message, 'content') else str(event.message))
        
        # Add metadata
        metadata = []
        if hasattr(event, 'duration_ms') and event.duration_ms is not None:
            metadata.append(f"duration: {event.duration_ms/1000:.1f}s")
        if hasattr(event, 'tokens_used') and event.tokens_used:
            metadata.append(f"tokens: {event.tokens_used}")
        
        if metadata:
            content.append(f"\n{' | '.join(metadata)}", style=self.NORD_GRAY)
        
        self.console.print(header)
        self.console.print(content)
        self.console.print()
    
    def _handle_message_chunk(self, event: MessageChunkEvent) -> None:
        """Handle message chunks."""
        # Show chunks inline with a subtle indicator
        chunk_text = Text()
        chunk_text.append("·", style=self.NORD_PURPLE)
        chunk_text.append(event.content, style=self.NORD_GRAY)
        self.console.print(chunk_text, end="")
    
    def _display_api_error(self, event: APIErrorEvent, header: Text, color: str) -> None:
        """Display API error event."""
        error_panel = Panel(
            f"Provider: {event.provider}\nError: {event.error_type}\n{event.error_message}",
            title=header,
            title_align="left",
            border_style=color,
            expand=False
        )
        self.console.print(error_panel)
        self.console.print()
    
    def _display_context_truncation(self, event: ContextTruncationEvent, header: Text, color: str) -> None:
        """Display context truncation event."""
        content = f"Agent: {event.agent_id}\n"
        content += f"Messages removed: {event.messages_removed}\n"
        content += f"Tokens before: {event.tokens_before} → after: {event.tokens_after}"
        
        panel = Panel(
            content,
            title=header,
            title_align="left",
            border_style=color,
            expand=False
        )
        self.console.print(panel)
        self.console.print()
    
    def _display_system_prompt(self, event: SystemPromptEvent, header: Text) -> None:
        """Display system prompt event."""
        # Show the actual system prompt content
        if hasattr(event, 'prompt') and event.prompt:
            self.console.print(header, f"{event.agent_id}: {event.prompt}")
        else:
            self.console.print(header, f"{event.agent_id} system prompt configured")
    
    def _display_generic_event(self, event: Event, header: Text) -> None:
        """Display generic event."""
        # Convert event to dict and format key fields
        event_dict = event.dict()
        event_dict.pop('timestamp', None)  # Already in header
        
        # Format as simple key-value pairs
        content = []
        for key, value in event_dict.items():
            if value is not None and value != "":
                content.append(f"{key}: {value}")
        
        if content:
            self.console.print(header)
            for line in content:
                self.console.print(f"  {line}", style=self.NORD_GRAY)
            self.console.print()
        else:
            self.console.print(header)
    
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
            if hasattr(msg, 'content'):
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
            event_dict.pop('timestamp', None)
            
            lines = []
            for key, value in event_dict.items():
                if value is not None:
                    lines.append(f"  {key}: {value}")
            
            return "\n".join(lines) if lines else "  (no data)"