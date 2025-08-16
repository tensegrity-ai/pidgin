"""Conversation lifecycle management - refactored version."""

from pathlib import Path
from typing import Any, Dict, Optional

from ..providers.token_tracker import GlobalTokenTracker
from .conversation_setup import ConversationSetup
from .conversation_state import ConversationState
from .types import Agent, Conversation, Message


class ConversationLifecycle:
    """Manages conversation lifecycle using focused components."""

    def __init__(
        self, console=None, token_tracker: Optional[GlobalTokenTracker] = None
    ):
        self.console = console
        self.token_tracker = token_tracker

        self.setup = ConversationSetup(console, token_tracker)
        self.state: Optional[ConversationState] = None

        self.bus = None
        self.display_filter = None
        self.chat_display = None
        self.tail_display = None
        self.wrapped_providers: Dict[str, Any] = {}
        self._owns_bus = False
        self.db_store = None

    def set_providers(self, base_providers):
        self.setup.set_providers(base_providers)
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
        result = await self.setup.initialize_event_system(
            conv_dir=conv_dir,
            display_mode=display_mode,
            show_timing=show_timing,
            agents=agents,
            existing_bus=existing_bus,
            db_store=db_store,
            prompt_tag=prompt_tag,
        )

        (
            self.bus,
            self.display_filter,
            self.chat_display,
            self.tail_display,
            self.wrapped_providers,
            self._owns_bus,
        ) = result

        self.state = ConversationState(self.bus, self.display_filter)
        self.db_store = db_store

    def create_conversation(
        self,
        agent_a: Agent,
        agent_b: Agent,
        initial_prompt: str,
        conversation_id: Optional[str] = None,
    ) -> Conversation:
        if not self.state:
            raise RuntimeError(
                "Must initialize event system before creating conversation"
            )
        return self.state.create_conversation(
            agent_a, agent_b, initial_prompt, conversation_id
        )

    async def add_initial_messages(
        self,
        conversation: Conversation,
        initial_messages: list[Message],
        loaded_from_checkpoint: bool = False,
    ):
        if not self.state:
            raise RuntimeError("Must initialize event system before adding messages")
        await self.state.add_initial_messages(
            conversation, initial_messages, loaded_from_checkpoint
        )

    async def emit_start_events(
        self,
        conversation: Conversation,
        system_prompts: Dict[str, str],
        show_system_prompts: bool,
        config: dict,
        experiment_id: Optional[str] = None,
    ):
        if not self.state:
            raise RuntimeError("Must initialize event system before emitting events")
        await self.state.emit_start_events(
            conversation, system_prompts, show_system_prompts, config, experiment_id
        )

    async def emit_end_event_with_reason(
        self,
        conversation: Conversation,
        status: str,
        reason: Optional[str] = None,
        error: Optional[str] = None,
        experiment_id: Optional[str] = None,
    ):
        if not self.state:
            raise RuntimeError("Must initialize event system before emitting events")
        await self.state.emit_end_event(
            conversation, status, reason, error, experiment_id
        )

    async def emit_end_event(
        self,
        conversation: Conversation,
        status: str = "completed",
        experiment_id: Optional[str] = None,
    ):
        await self.emit_end_event_with_reason(
            conversation, status, experiment_id=experiment_id
        )

    async def cleanup(self):
        if self.chat_display:
            if hasattr(self.chat_display, "cleanup"):
                await self.chat_display.cleanup()
            self.chat_display = None

        if self.tail_display:
            if hasattr(self.tail_display, "cleanup"):
                await self.tail_display.cleanup()
            self.tail_display = None

        if self._owns_bus and self.bus:
            await self.bus.stop()
            self.bus = None

        self.display_filter = None
        self.wrapped_providers = {}
        self.state = None
