"""Display filter for human-readable conversation output."""

from typing import Optional

from rich.console import Console

from ..core.events import (
    APIErrorEvent,
    ContextLimitEvent,
    ConversationEndEvent,
    ConversationResumedEvent,
    ConversationStartEvent,
    ErrorEvent,
    Event,
    MessageCompleteEvent,
    ProviderTimeoutEvent,
    SystemPromptEvent,
    TurnCompleteEvent,
)
from .display_handlers import (
    ConversationDisplayHandler,
    ErrorDisplayHandler,
    MessageDisplayHandler,
    SystemDisplayHandler,
)


class DisplayFilter:
    """Filters events for human-readable display."""

    def __init__(
        self,
        console: Console,
        mode: str = "normal",
        show_timing: bool = False,
        agents: Optional[dict] = None,
        prompt_tag: Optional[str] = None,
    ):
        """Initialize display filter.

        Args:
            console: Rich console for output
            mode: Display mode ('normal', 'quiet', 'verbose')
            show_timing: Whether to show timing information
            agents: Dict mapping agent_id to Agent objects
            prompt_tag: Optional tag to prefix prompts with
        """
        self.console = console
        self.mode = mode
        self.show_timing = show_timing
        self.agents = agents or {}
        self.prompt_tag = prompt_tag

        self.conversation_handler = ConversationDisplayHandler(
            console=console,
            mode=mode,
            show_timing=show_timing,
            agents=agents,
            prompt_tag=prompt_tag,
        )
        self.message_handler = MessageDisplayHandler(
            console=console,
            mode=mode,
            show_timing=show_timing,
            agents=agents,
            prompt_tag=prompt_tag,
        )
        self.error_handler = ErrorDisplayHandler(
            console=console,
            mode=mode,
            show_timing=show_timing,
            agents=agents,
            prompt_tag=prompt_tag,
        )
        self.system_handler = SystemDisplayHandler(
            console=console,
            mode=mode,
            show_timing=show_timing,
            agents=agents,
            prompt_tag=prompt_tag,
        )

        # Track conversation state
        self.current_turn = 0
        self.max_turns = 0

    def handle_event(self, event: Event) -> None:
        """Display events based on mode."""

        if self.mode == "verbose":
            # Show everything (keep existing EventLogger behavior)
            return  # Let EventLogger handle it

        elif self.mode == "quiet":
            # Only critical events
            if isinstance(event, ConversationStartEvent):
                self.conversation_handler.show_quiet_start(event)
                self.max_turns = event.max_turns
            elif isinstance(event, TurnCompleteEvent):
                self.conversation_handler.show_quiet_turn(event)
                self.current_turn = event.turn_number + 1
            elif isinstance(event, ConversationEndEvent):
                self.conversation_handler.show_quiet_end(event)

        else:  # normal mode
            if isinstance(event, ConversationStartEvent):
                self.conversation_handler.show_conversation_start(event)
                self.max_turns = event.max_turns
            elif isinstance(event, SystemPromptEvent):
                self.system_handler.show_system_prompt(event)
            elif isinstance(event, MessageCompleteEvent):
                self.message_handler.show_message(event)
            elif isinstance(event, TurnCompleteEvent):
                self.conversation_handler.show_turn_complete(event)
                self.current_turn = event.turn_number + 1
            elif isinstance(event, APIErrorEvent):
                self.error_handler.show_api_error(event)
            elif isinstance(event, ProviderTimeoutEvent):
                self.error_handler.show_timeout_error(event)
            elif isinstance(event, ErrorEvent):
                self.error_handler.show_error(event)
            elif isinstance(event, ContextLimitEvent):
                self.error_handler.show_context_limit(event)
            elif isinstance(event, ConversationEndEvent):
                self.conversation_handler.show_conversation_end(event)
            elif isinstance(event, ConversationResumedEvent):
                self.conversation_handler.show_resumed(event)

        # Sync state with conversation handler
        if hasattr(self.conversation_handler, "current_turn"):
            self.current_turn = self.conversation_handler.current_turn
        if hasattr(self.conversation_handler, "max_turns"):
            self.max_turns = self.conversation_handler.max_turns

    # Delegation methods for external callers
    def show_pacing_indicator(self, provider: str, wait_time: float):
        """Show rate limit pacing indicator.

        Args:
            provider: Provider name being paced
            wait_time: How long we're waiting in seconds
        """
        self.system_handler.show_pacing_indicator(provider, wait_time)

    def show_token_usage(self, provider: str, used: int, limit: int):
        """Show current token consumption rate.

        Args:
            provider: Provider name
            used: Current tokens per minute
            limit: Token per minute limit
        """
        self.system_handler.show_token_usage(provider, used, limit)
