"""Event logger for radical transparency - SEE EVERYTHING."""

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
)


class EventLogger:
    """SEE EVERYTHING - no filtering at first."""
    
    EVENT_COLORS = {
        ConversationStartEvent: "bold green",
        ConversationEndEvent: "bold red",
        TurnStartEvent: "cyan",
        TurnCompleteEvent: "blue",
        MessageRequestEvent: "yellow",
        MessageCompleteEvent: "magenta",
    }
    
    def __init__(self, bus: EventBus, console: Console):
        """Initialize logger and subscribe to ALL events.
        
        Args:
            bus: The event bus to monitor
            console: Rich console for output
        """
        self.bus = bus
        self.console = console
        
        # Subscribe to ALL events
        bus.subscribe(Event, self.log_event)
        
    def log_event(self, event: Event) -> None:
        """Log an event with beautiful Rich formatting.
        
        Args:
            event: The event to log
        """
        # Skip if no console provided (file-only logging)
        if self.console is None:
            return
            
        # Get color for this event type
        color = self.EVENT_COLORS.get(type(event), "white")
        
        # Format timestamp
        timestamp = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
        
        # Create title with event type
        event_type = type(event).__name__
        title = f"[{color}][{timestamp}] {event_type}[/{color}]"
        
        # Build content based on event type
        content = self._format_event_content(event)
        
        # Display based on event importance
        if isinstance(event, (ConversationStartEvent, ConversationEndEvent)):
            # Major events get panels
            self.console.print(Panel(content, title=title, border_style=color))
        elif isinstance(event, MessageChunkEvent):
            # Chunks are inline for less noise (but still visible!)
            self.console.print(f"{title} {content}", highlight=False)
        else:
            # Everything else gets nice formatting
            self.console.print(f"\n{title}")
            self.console.print(content)
    
    def _format_event_content(self, event: Event) -> str:
        """Format event content based on type.
        
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
                f"\n  max_turns: {event.max_turns}\n"
                f"  initial_prompt: {event.initial_prompt[:50]}..."
            )
            return content
            
        elif isinstance(event, ConversationEndEvent):
            return (
                f"  conversation_id: {event.conversation_id}\n"
                f"  reason: {event.reason}\n"
                f"  total_turns: {event.total_turns}\n"
                f"  duration: {event.duration_ms / 1000:.2f}s"
            )
            
        elif isinstance(event, TurnStartEvent):
            return (
                f"  conversation_id: {event.conversation_id}\n"
                f"  turn_number: {event.turn_number}"
            )
            
        elif isinstance(event, TurnCompleteEvent):
            # Show message previews
            a_preview = event.turn.agent_a_message.content[:50]
            b_preview = event.turn.agent_b_message.content[:50]
            return (
                f"  conversation_id: {event.conversation_id}\n"
                f"  turn_number: {event.turn_number}\n"
                f"  agent_a: \"{a_preview}...\"\n"
                f"  agent_b: \"{b_preview}...\""
            )
            
        elif isinstance(event, MessageRequestEvent):
            return (
                f"  conversation_id: {event.conversation_id}\n"
                f"  agent_id: {event.agent_id}\n"
                f"  turn_number: {event.turn_number}\n"
                f"  history_length: {len(event.conversation_history)}"
            )
            
        elif isinstance(event, MessageChunkEvent):
            # Inline format for chunks
            chunk_display = repr(event.chunk)[:30]
            return (
                f"agent_id: {event.agent_id} | "
                f"chunk[{event.chunk_index}]: {chunk_display} | "
                f"elapsed: {event.elapsed_ms}ms"
            )
            
        elif isinstance(event, MessageCompleteEvent):
            preview = event.message.content[:80]
            return (
                f"  conversation_id: {event.conversation_id}\n"
                f"  agent_id: {event.agent_id}\n"
                f"  message_length: {len(event.message.content)}\n"
                f"  tokens_used: {event.tokens_used}\n"
                f"  duration: {event.duration_ms}ms\n"
                f"  preview: \"{preview}...\""
            )
            
        else:
            # Generic formatting for any other events
            attrs = []
            for key, value in event.__dict__.items():
                if key not in ['timestamp', 'event_id']:
                    attrs.append(f"  {key}: {value}")
            return "\n".join(attrs) if attrs else "  (no additional data)"