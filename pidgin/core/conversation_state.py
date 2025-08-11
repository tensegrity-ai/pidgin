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
        """Initialize state manager.
        
        Args:
            bus: Event bus for emitting events
            display_filter: Optional display filter
        """
        self.bus = bus
        self.display_filter = display_filter
        self._end_event_emitted = False
        
    def create_conversation(
        self,
        experiment_id: str,
        agent_a: Agent,
        agent_b: Agent,
        initial_prompt: str,
        conversation_id: Optional[str] = None,
    ) -> Conversation:
        return Conversation(
            experiment_id=experiment_id,
            agent_a=agent_a,
            agent_b=agent_b,
            messages=[],
            initial_prompt=initial_prompt,
            id=conversation_id,
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
                for msg in initial_messages:
                    msg.timestamp = time.time()
                    conversation.messages.append(msg)
                    
    async def emit_start_events(
        self,
        conversation: Conversation,
        system_prompts: Dict[str, str],
        show_system_prompts: bool,
        config: dict,
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
                    
        # Emit conversation start event
        await self.bus.emit(
            ConversationStartEvent(
                conversation_id=conversation.id,
                experiment_id=conversation.experiment_id,
                agent_a=conversation.agent_a,
                agent_b=conversation.agent_b,
                config=config,
            )
        )
        
    async def emit_end_event(
        self,
        conversation: Conversation,
        status: str,
        reason: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Emit conversation end event.
        
        Args:
            conversation: Conversation instance
            status: Final status (completed, failed, interrupted)
            reason: Optional reason for ending
            error: Optional error message
        """
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
                experiment_id=conversation.experiment_id,
                turns_completed=conversation.turn_count,
                status=actual_status,
                reason=reason,
                error=error,
                duration_seconds=time.time() - conversation.start_time,
            )
        )