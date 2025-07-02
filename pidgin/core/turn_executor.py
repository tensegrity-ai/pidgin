"""Turn execution logic for conversations."""

import time
from typing import Optional

from .types import Agent, Conversation
from .events import (
    Turn,
    TurnStartEvent,
    TurnCompleteEvent,
    ConversationEndEvent,
)


class TurnExecutor:
    """Executes conversation turns and handles turn-level events."""
    
    def __init__(self, bus, message_handler, convergence_calculator, config, start_time):
        """Initialize turn executor.
        
        Args:
            bus: Event bus for emitting events
            message_handler: For getting agent messages
            convergence_calculator: For calculating convergence scores
            config: Configuration object
            start_time: Conversation start time for duration calculation
        """
        self.bus = bus
        self.message_handler = message_handler
        self.convergence_calculator = convergence_calculator
        self.config = config
        self.start_time = start_time
        
        # Convergence overrides for experiments
        self._convergence_threshold_override = None
        self._convergence_action_override = None
    
    def set_convergence_overrides(self, threshold=None, action=None):
        """Set convergence threshold and action overrides.
        
        Args:
            threshold: Override convergence threshold
            action: Override convergence action ('stop' or 'warn')
        """
        self._convergence_threshold_override = threshold
        self._convergence_action_override = action
    
    async def run_single_turn(
        self,
        conversation: Conversation,
        turn_number: int,
        agent_a: Agent,
        agent_b: Agent,
        interrupt_handler,
    ) -> Optional[Turn]:
        """Run a single conversation turn.
        
        Args:
            conversation: The conversation object
            turn_number: Current turn number
            agent_a: First agent
            agent_b: Second agent
            interrupt_handler: For passing to message handler
            
        Returns:
            The completed turn or None if interrupted/stopped
        """
        # Emit turn start
        await self.bus.emit(
            TurnStartEvent(
                conversation_id=conversation.id,
                turn_number=turn_number,
            )
        )
        
        # Get Agent A message
        agent_a_message = await self.message_handler.get_agent_message(
            conversation.id, agent_a, turn_number, conversation.messages, interrupt_handler
        )
        if agent_a_message is None:
            return None
        
        conversation.messages.append(agent_a_message)
        
        # Get Agent B message
        agent_b_message = await self.message_handler.get_agent_message(
            conversation.id, agent_b, turn_number, conversation.messages, interrupt_handler
        )
        if agent_b_message is None:
            return None
        
        conversation.messages.append(agent_b_message)
        
        # Build turn
        turn = Turn(
            agent_a_message=agent_a_message,
            agent_b_message=agent_b_message,
        )
        
        # Calculate convergence
        convergence_score = self.convergence_calculator.calculate(conversation.messages)
        
        # Emit turn complete with convergence
        await self.bus.emit(
            TurnCompleteEvent(
                conversation_id=conversation.id,
                turn_number=turn_number,
                turn=turn,
                convergence_score=convergence_score,
            )
        )
        
        # Check convergence threshold (with overrides for experiments)
        conv_config = self.config.get_convergence_config()
        threshold = self._convergence_threshold_override if self._convergence_threshold_override is not None else conv_config.get("convergence_threshold", 0.85)
        action = self._convergence_action_override if self._convergence_action_override is not None else conv_config.get("convergence_action", "stop")
        
        if convergence_score >= threshold:
            if action == "stop":
                # Stop the conversation
                await self.bus.emit(
                    ConversationEndEvent(
                        conversation_id=conversation.id,
                        reason="high_convergence",
                        total_turns=turn_number + 1,
                        duration_ms=int((time.time() - self.start_time) * 1000),
                    )
                )
                return None  # Signal to stop
            elif action == "warn":
                # Just log a warning (display already shows it)
                pass
        
        return turn