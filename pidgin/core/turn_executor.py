"""Turn execution logic for conversations."""

from typing import Optional

from .constants import EndReason
from .events import (
    SystemPromptEvent,
    Turn,
    TurnCompleteEvent,
    TurnStartEvent,
)
from .types import Agent, Conversation, Message


class TurnExecutor:
    """Executes conversation turns and handles turn-level events."""

    def __init__(
        self, bus, message_handler, convergence_calculator, config, start_time
    ):
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

        # Track stop reason if conversation ends early
        self.stop_reason = None
        self.context_limit_reached = False

        # Custom awareness for turn-based prompt injection
        self.custom_awareness = {"agent_a": None, "agent_b": None}

        # Subscribe to context limit events
        if bus:
            from .events import ContextLimitEvent

            bus.subscribe(ContextLimitEvent, self.handle_context_limit)

    def set_convergence_overrides(self, threshold=None, action=None):
        """Set convergence threshold and action overrides.

        Args:
            threshold: Override convergence threshold
            action: Override convergence action ('stop' or 'warn')
        """
        self._convergence_threshold_override = threshold
        self._convergence_action_override = action

    def set_custom_awareness(self, custom_awareness):
        """Set custom awareness objects for turn-based prompt injection.

        Args:
            custom_awareness: Dict with agent_a and agent_b CustomAwareness objects
        """
        self.custom_awareness = custom_awareness

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

        # Check for custom awareness prompts to inject at this turn
        await self._inject_turn_prompts(conversation, turn_number)

        # Get Agent A message
        agent_a_message = await self.message_handler.get_agent_message(
            conversation.id,
            agent_a,
            turn_number,
            conversation.messages,
            interrupt_handler,
        )
        if agent_a_message is None:
            return None

        # NOTE: Direct append is intentional here. While this bypasses the event system,
        # it's acceptable because:
        # 1. MessageCompleteEvent was already emitted by message_handler
        # 2. This is just maintaining runtime conversation state
        # 3. The JSONL events are the authoritative source of truth
        # 4. The append is needed for the next agent to see the full context
        conversation.messages.append(agent_a_message)

        # Get Agent B message
        agent_b_message = await self.message_handler.get_agent_message(
            conversation.id,
            agent_b,
            turn_number,
            conversation.messages,
            interrupt_handler,
        )
        if agent_b_message is None:
            return None

        # NOTE: Direct append is intentional (see comment above for agent_a_message)
        conversation.messages.append(agent_b_message)

        # Build turn
        turn = Turn(
            agent_a_message=agent_a_message,
            agent_b_message=agent_b_message,
        )

        # Calculate convergence
        # NOTE: Only convergence is calculated live during experiments.
        # Full metrics (~80 fields) are calculated post-hoc during import
        # to avoid slowing down conversations. See ImportService.
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
        threshold = (
            self._convergence_threshold_override
            if self._convergence_threshold_override is not None
            else conv_config.get("convergence_threshold", 0.85)
        )
        action = (
            self._convergence_action_override
            if self._convergence_action_override is not None
            else conv_config.get("convergence_action", "stop")
        )

        if convergence_score >= threshold:
            if action == "stop":
                # Signal to stop due to high convergence
                # Store the reason so conductor can emit the appropriate end event
                self.stop_reason = EndReason.HIGH_CONVERGENCE
                return None  # Signal to stop
            elif action == "warn":
                # Just log a warning (display already shows it)
                pass

        return turn

    async def _inject_turn_prompts(self, conversation: Conversation, turn_number: int):
        """Inject custom system prompts at specific turns.

        Args:
            conversation: The conversation to inject prompts into
            turn_number: Current turn number
        """
        # Check agent A custom awareness
        if self.custom_awareness.get("agent_a"):
            prompts = self.custom_awareness["agent_a"].get_turn_prompts(turn_number)
            if prompts["agent_a"]:
                # Add system message for agent A
                system_msg = Message(
                    role="system", content=prompts["agent_a"], agent_id="system"
                )
                # NOTE: Direct append for system prompts is intentional.
                # SystemPromptEvent is emitted below for tracking.
                # The append ensures the prompt is in context for the next message.
                conversation.messages.append(system_msg)

                # Emit event for tracking
                await self.bus.emit(
                    SystemPromptEvent(
                        conversation_id=conversation.id,
                        agent_id="agent_a",
                        prompt=prompts["agent_a"],
                        agent_display_name=f"Turn {turn_number} injection for Agent A",
                    )
                )

        # Check agent B custom awareness (might be same file or different)
        if self.custom_awareness.get("agent_b"):
            prompts = self.custom_awareness["agent_b"].get_turn_prompts(turn_number)
            if prompts["agent_b"]:
                # Add system message for agent B
                system_msg = Message(
                    role="system", content=prompts["agent_b"], agent_id="system"
                )
                # NOTE: Direct append for system prompts is intentional (see above)
                conversation.messages.append(system_msg)

                # Emit event for tracking
                await self.bus.emit(
                    SystemPromptEvent(
                        conversation_id=conversation.id,
                        agent_id="agent_b",
                        prompt=prompts["agent_b"],
                        agent_display_name=f"Turn {turn_number} injection for Agent B",
                    )
                )

    async def handle_context_limit(self, event):
        """Handle context limit event by setting the flag.

        Args:
            event: ContextLimitEvent
        """
        self.context_limit_reached = True
        self.stop_reason = EndReason.CONTEXT_LIMIT_REACHED
