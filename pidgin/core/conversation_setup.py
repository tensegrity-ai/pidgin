"""Conversation setup and initialization."""

from pathlib import Path
from typing import Dict, Optional

from ..providers.event_wrapper import EventAwareProvider
from ..ui.display_filter import DisplayFilter
from ..ui.tail import TailDisplay
from .event_bus import EventBus
from .types import Agent


class ConversationSetup:
    """Handles conversation initialization and event system setup."""

    def __init__(self, console=None, token_tracker=None):
        """Initialize setup handler.

        Args:
            console: Optional console for output
            token_tracker: Optional token tracker for rate limiting
        """
        self.console = console
        self.token_tracker = token_tracker
        self.base_providers = {}

    def set_providers(self, base_providers):
        self.base_providers = base_providers

    async def initialize_event_system(
        self,
        conv_dir: Path,
        display_mode: str,
        show_timing: bool,
        agents: Dict[str, Agent],
        existing_bus=None,
        db_store=None,
        prompt_tag: Optional[str] = None,
    ):
        """Initialize EventBus and display components.

        Returns:
            Tuple of (bus, display_filter, chat_display, tail_display, wrapped_providers)
        """
        if existing_bus is None:
            bus = EventBus(db_store=None, event_log_dir=conv_dir)
            await bus.start()
            owns_bus = True
        else:
            bus = existing_bus
            owns_bus = False

        display_filter = None
        chat_display = None
        tail_display = None

        if display_mode == "tail":
            tail_display = TailDisplay(bus, self.console)
        elif display_mode == "chat":
            from ..ui.chat_display import ChatDisplay

            chat_display = ChatDisplay(bus, self.console, agents)
        else:
            if self.console is not None and display_mode != "none":
                display_filter = DisplayFilter(
                    console=self.console,
                    mode="quiet" if display_mode == "quiet" else "normal",
                    show_timing=show_timing,
                    prompt_tag=prompt_tag,
                )
                # Subscribe to bus after creation
                if hasattr(display_filter, "subscribe"):
                    display_filter.subscribe(bus)

        wrapped_providers = {}
        for agent_id, provider in self.base_providers.items():
            wrapped_providers[agent_id] = EventAwareProvider(
                provider=provider,
                agent_id=agent_id,
                bus=bus,
                token_tracker=self.token_tracker,
            )

        return (
            bus,
            display_filter,
            chat_display,
            tail_display,
            wrapped_providers,
            owns_bus,
        )
