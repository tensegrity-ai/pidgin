"""Main tail display module."""

from rich.console import Console
from rich.text import Text

from ...core.event_bus import EventBus
from ...core.events import (
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
from .constants import EVENT_COLORS, EVENT_GLYPHS, NORD_GRAY
from .formatters import TailFormatter
from .handlers import EventHandlers


class TailDisplay:
    """Display formatted event stream in console."""

    def __init__(self, bus: EventBus, console: Console):
        """Initialize with event bus and console.

        Args:
            bus: Event bus to subscribe to
            console: Rich console for output
        """
        self.bus = bus
        self.console = console
        self.formatter = TailFormatter()
        self.handlers = EventHandlers(console)

        # Subscribe to all events
        self.bus.subscribe(Event, self.log_event)

    def _format_agent_id(self, agent_id: str) -> str:
        """Format agent identifier for display.

        Delegates to formatter for consistency.
        """
        return self.formatter.format_agent_id(agent_id)

    def log_event(self, event: Event) -> None:
        """Log an event to the console.

        Args:
            event: Event to log
        """
        # Skip if no console (daemon mode)
        if self.console is None:
            return

        # Get event type for styling
        event_type = type(event)
        color = EVENT_COLORS.get(event_type, NORD_GRAY)
        glyph = EVENT_GLYPHS.get(event_type, "•")

        timestamp = event.timestamp.strftime("%H:%M:%S.%f")[:-3]

        header = Text()
        header.append(f"[{timestamp}] ", style=NORD_GRAY)
        header.append(f"{glyph} ", style=color + " bold")
        header.append(
            event.__class__.__name__.replace("Event", ""), style=color + " bold"
        )

        if isinstance(event, ConversationStartEvent):
            self.handlers.display_conversation_start(event, header, color)
        elif isinstance(event, ConversationEndEvent):
            self.handlers.display_conversation_end(event, header, color)
        elif isinstance(event, TurnStartEvent):
            self.handlers.display_turn_start(event, header)
        elif isinstance(event, TurnCompleteEvent):
            self.handlers.display_turn_complete(event, header)
        elif isinstance(event, MessageRequestEvent):
            self.handlers.display_message_request(event, header)
        elif isinstance(event, MessageCompleteEvent):
            self.handlers.display_message_complete(event, header, color)
        elif isinstance(event, MessageChunkEvent):
            self.handlers.handle_message_chunk(event)
        elif isinstance(event, APIErrorEvent):
            self.handlers.display_api_error(event, header, color)
        elif isinstance(event, ContextTruncationEvent):
            self.handlers.display_context_truncation(event, header, color)
        elif isinstance(event, SystemPromptEvent):
            self.handlers.display_system_prompt(event, header)
        elif isinstance(event, RateLimitPaceEvent):
            self.handlers.display_rate_limit(event, header)
        elif isinstance(event, TokenUsageEvent):
            self.handlers.display_token_usage(event, header)
        elif isinstance(event, ProviderTimeoutEvent):
            self.handlers.display_provider_timeout(event, header)
        elif isinstance(event, InterruptRequestEvent):
            self.handlers.display_interrupt_request(event, header)
        elif isinstance(event, ConversationPausedEvent):
            self.handlers.display_conversation_paused(event, header)
        elif isinstance(event, ConversationResumedEvent):
            self.handlers.display_conversation_resumed(event, header)
        else:
            self._display_generic_event(event, header)

    def _display_generic_event(self, event: Event, header: Text) -> None:
        """Display generic event information.

        Args:
            event: Event to display
            header: Formatted header text
        """
        # Skip if no console (daemon mode)
        if self.console is None:
            return

        # Get event attributes
        event_dict = vars(event)

        # Filter out private and timestamp attributes
        display_attrs = {
            k: v
            for k, v in event_dict.items()
            if not k.startswith("_") and k != "timestamp"
        }

        # Format attributes
        if display_attrs:
            attr_strs = []
            for key, value in display_attrs.items():
                # Truncate long values
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                attr_strs.append(f"{key}: {value_str}")

            content = " | ".join(attr_strs)
        else:
            content = "(no data)"

        self.console.print(header, content)
