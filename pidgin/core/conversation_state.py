"""Conversation state management."""

import time
from typing import Dict, List, Optional

from .events import (
    ConversationEndEvent,
    ConversationStartEvent,
    SystemPromptEvent,
)
from .types import Agent, Conversation, Message


class ConversationState:
    """Manages conversation state and events."""

    def __init__(self, bus, display_filter=None):
        self.bus = bus
        self.display_filter = display_filter
        self._end_event_emitted = False

    def create_conversation(
        self,
        agent_a: Agent,
        agent_b: Agent,
        initial_prompt: str,
        conversation_id: Optional[str] = None,
    ) -> Conversation:
        return Conversation(
            id=conversation_id,
            agents=[agent_a, agent_b],
            messages=[],
            initial_prompt=initial_prompt,
        )

    async def add_initial_messages(
        self,
        conversation: Conversation,
        initial_messages: List[Message],
        loaded_from_checkpoint: bool = False,
    ):
        if initial_messages:
            if loaded_from_checkpoint:
                conversation.messages.extend(initial_messages)
            else:
                conversation.messages.extend(initial_messages)

    async def emit_start_events(
        self,
        conversation: Conversation,
        system_prompts: Dict[str, str],
        show_system_prompts: bool,
        config: dict,
        experiment_id: Optional[str] = None,
    ):
        if show_system_prompts:
            for agent_id, prompt in system_prompts.items():
                if prompt:
                    await self.bus.emit(
                        SystemPromptEvent(
                            conversation_id=conversation.id,
                            agent_id=agent_id,
                            prompt=prompt,
                        )
                    )

        # Extract model info from agents
        agent_a_model = getattr(conversation.agent_a, "model", None)
        agent_b_model = getattr(conversation.agent_b, "model", None)

        # Extract display names and other config values
        agent_a_display_name = getattr(conversation.agent_a, "display_name", None)
        agent_b_display_name = getattr(conversation.agent_b, "display_name", None)
        max_turns = config.get("max_turns")
        initial_prompt = config.get("initial_prompt")

        await self.bus.emit(
            ConversationStartEvent(
                conversation_id=conversation.id,
                agent_a=conversation.agent_a,
                agent_b=conversation.agent_b,
                experiment_id=experiment_id,
                config=config,
                agent_a_model=agent_a_model,
                agent_b_model=agent_b_model,
                agent_a_display_name=agent_a_display_name,
                agent_b_display_name=agent_b_display_name,
                max_turns=max_turns,
                initial_prompt=initial_prompt,
            )
        )

    async def emit_end_event(
        self,
        conversation: Conversation,
        status: str,
        reason: Optional[str] = None,
        error: Optional[str] = None,
        experiment_id: Optional[str] = None,
    ):
        if self._end_event_emitted:
            return

        self._end_event_emitted = True

        if not conversation.messages:
            actual_status = "empty"
        else:
            actual_status = status

        await self.bus.emit(
            ConversationEndEvent(
                conversation_id=conversation.id,
                total_turns=conversation.turn_count,
                status=actual_status,
                experiment_id=experiment_id,
                reason=reason,
                error=error,
                duration_ms=int((time.time() - conversation.start_time) * 1000),
            )
        )
