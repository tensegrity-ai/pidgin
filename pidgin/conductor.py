"""Event-driven conversation orchestrator."""

import asyncio
import time
from typing import Dict, List, Optional

from rich.console import Console

from .event_bus import EventBus
from .events import (
    Event,
    Turn,
    ConversationStartEvent,
    ConversationEndEvent,
    TurnStartEvent,
    TurnCompleteEvent,
    MessageRequestEvent,
    MessageCompleteEvent,
)
from .types import Agent, Conversation, Message


class Conductor:
    """Event-driven conversation orchestrator (replacing DialogueEngine's orchestration)."""
    
    def __init__(self, event_bus: EventBus, providers: Dict[str, any]):
        """Initialize conductor with event bus.
        
        Args:
            event_bus: Central event distribution
            providers: Dict mapping agent_id to wrapped providers
        """
        self.bus = event_bus
        self.providers = providers
        self.console = Console()
        
        # Track message completion
        self.pending_messages: Dict[str, asyncio.Future] = {}
        
        # Subscribe to message completions
        self.bus.subscribe(MessageCompleteEvent, self._handle_message_complete)
        
    async def run_conversation(
        self,
        agent_a: Agent,
        agent_b: Agent,
        initial_prompt: str,
        max_turns: int = 10,
    ) -> Conversation:
        """Run a complete conversation using events.
        
        Args:
            agent_a: First agent
            agent_b: Second agent
            initial_prompt: Starting prompt
            max_turns: Maximum number of turns
            
        Returns:
            The completed conversation
        """
        # Create conversation
        conversation = Conversation(
            agents=[agent_a, agent_b],
            initial_prompt=initial_prompt,
        )
        
        # Add initial prompt as system message
        conversation.messages.append(
            Message(
                role="system",
                content=initial_prompt,
                agent_id="human"
            )
        )
        
        # Track timing
        start_time = time.time()
        
        # Emit start event
        await self.bus.emit(ConversationStartEvent(
            conversation_id=conversation.id,
            agent_a_model=agent_a.model,
            agent_b_model=agent_b.model,
            initial_prompt=initial_prompt,
            max_turns=max_turns,
        ))
        
        # Run turns
        for turn_num in range(max_turns):
            turn = await self.run_single_turn(
                conversation=conversation,
                turn_number=turn_num,
                agent_a=agent_a,
                agent_b=agent_b,
            )
            
            if turn is None:
                break
        
        # Emit end event
        duration_ms = int((time.time() - start_time) * 1000)
        await self.bus.emit(ConversationEndEvent(
            conversation_id=conversation.id,
            reason="max_turns" if turn_num == max_turns - 1 else "completed",
            total_turns=turn_num + 1,
            duration_ms=duration_ms,
        ))
        
        return conversation
    
    async def run_single_turn(
        self,
        conversation: Conversation,
        turn_number: int,
        agent_a: Agent,
        agent_b: Agent,
    ) -> Optional[Turn]:
        """Run a single conversation turn.
        
        Args:
            conversation: The conversation object
            turn_number: Current turn number
            agent_a: First agent
            agent_b: Second agent
            
        Returns:
            The completed turn or None if interrupted
        """
        # Emit turn start
        await self.bus.emit(TurnStartEvent(
            conversation_id=conversation.id,
            turn_number=turn_number,
        ))
        
        # Request Agent A message
        agent_a_future = asyncio.Future()
        self.pending_messages[agent_a.id] = agent_a_future
        
        await self.bus.emit(MessageRequestEvent(
            conversation_id=conversation.id,
            agent_id=agent_a.id,
            turn_number=turn_number,
            conversation_history=conversation.messages.copy(),
        ))
        
        # Wait for Agent A response
        try:
            agent_a_message = await asyncio.wait_for(agent_a_future, timeout=60.0)
        except asyncio.TimeoutError:
            self.console.print("[red]Timeout waiting for Agent A response[/red]")
            return None
        
        # Add to conversation
        conversation.messages.append(agent_a_message)
        
        # Request Agent B message
        agent_b_future = asyncio.Future()
        self.pending_messages[agent_b.id] = agent_b_future
        
        await self.bus.emit(MessageRequestEvent(
            conversation_id=conversation.id,
            agent_id=agent_b.id,
            turn_number=turn_number,
            conversation_history=conversation.messages.copy(),
        ))
        
        # Wait for Agent B response
        try:
            agent_b_message = await asyncio.wait_for(agent_b_future, timeout=60.0)
        except asyncio.TimeoutError:
            self.console.print("[red]Timeout waiting for Agent B response[/red]")
            return None
        
        # Add to conversation
        conversation.messages.append(agent_b_message)
        
        # Build turn
        turn = Turn(
            agent_a_message=agent_a_message,
            agent_b_message=agent_b_message,
            intervention=None,  # Not handling interventions yet
        )
        
        # Emit turn complete
        await self.bus.emit(TurnCompleteEvent(
            conversation_id=conversation.id,
            turn_number=turn_number,
            turn=turn,
        ))
        
        return turn
    
    def _handle_message_complete(self, event: MessageCompleteEvent) -> None:
        """Handle message completion events.
        
        Args:
            event: The message complete event
        """
        # Check if we're waiting for this message
        if event.agent_id in self.pending_messages:
            future = self.pending_messages.pop(event.agent_id)
            if not future.done():
                future.set_result(event.message)