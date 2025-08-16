"""Replay events to reconstruct conversation state for database import."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.constants import ConversationStatus
from ..core.events import (
    ConversationEndEvent,
    ConversationStartEvent,
    Event,
    MessageCompleteEvent,
    SystemPromptEvent,
    TurnCompleteEvent,
)
from ..io.event_deserializer import EventDeserializer
from ..io.logger import get_logger

logger = get_logger("event_replay")


@dataclass
class ConversationState:
    """Reconstructed state of a conversation from events."""

    conversation_id: str
    experiment_id: str

    # Conversation metadata
    agent_a_model: Optional[str] = None
    agent_b_model: Optional[str] = None
    initial_prompt: Optional[str] = None
    max_turns: Optional[int] = None
    temperature_a: Optional[float] = None
    temperature_b: Optional[float] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Status
    status: str = ConversationStatus.CREATED  # Default to created, not unknown
    end_reason: Optional[str] = None
    total_turns: int = 0
    final_convergence_score: Optional[float] = None

    # Agent names
    agent_names: Dict[str, str] = field(default_factory=dict)

    # Messages grouped by turn
    messages: List[Dict[str, Any]] = field(default_factory=list)

    # Turns for metric calculation
    turns: List[tuple[Any, Any]] = field(default_factory=list)

    # Turn metrics
    turn_metrics: List[Dict[str, Any]] = field(default_factory=list)

    # Token usage tracking
    token_counts: Dict[str, int] = field(default_factory=dict)

    # Raw events for storage
    events: List[tuple[int, Event]] = field(default_factory=list)


class EventReplay:
    """Replay events to reconstruct conversation state."""

    def replay_conversation(
        self, experiment_id: str, conversation_id: str, jsonl_path: Path
    ) -> ConversationState:
        """Replay events from JSONL to reconstruct conversation state.

        Args:
            experiment_id: Experiment ID
            conversation_id: Conversation ID
            jsonl_path: Path to JSONL file

        Returns:
            Reconstructed conversation state
        """
        state = ConversationState(
            conversation_id=conversation_id, experiment_id=experiment_id
        )

        # Read and process events
        deserializer = EventDeserializer()
        for line_num, event in deserializer.read_jsonl_events(jsonl_path):
            # Store raw event with line number
            state.events.append((line_num, event))

            # Process event based on type
            if isinstance(event, ConversationStartEvent):
                self._handle_conversation_start(state, event)
            elif isinstance(event, ConversationEndEvent):
                self._handle_conversation_end(state, event)
            elif isinstance(event, TurnCompleteEvent):
                self._handle_turn_complete(state, event)
            elif isinstance(event, MessageCompleteEvent):
                self._handle_message_complete(state, event)
            elif isinstance(event, SystemPromptEvent):
                self._handle_system_prompt(state, event)

        return state

    def _handle_conversation_start(
        self, state: ConversationState, event: ConversationStartEvent
    ) -> None:
        """Process ConversationStartEvent."""
        state.agent_a_model = event.agent_a_model
        state.agent_b_model = event.agent_b_model
        state.initial_prompt = event.initial_prompt
        state.max_turns = event.max_turns
        state.temperature_a = event.temperature_a
        state.temperature_b = event.temperature_b
        state.started_at = event.timestamp
        state.status = ConversationStatus.RUNNING

        # Store display names if provided
        if event.agent_a_display_name:
            state.agent_names["agent_a"] = event.agent_a_display_name
        if event.agent_b_display_name:
            state.agent_names["agent_b"] = event.agent_b_display_name

    def _handle_conversation_end(
        self, state: ConversationState, event: ConversationEndEvent
    ) -> None:
        """Process ConversationEndEvent."""
        state.completed_at = event.timestamp
        state.end_reason = event.reason
        state.total_turns = event.total_turns

        # Map reason to status
        if event.reason in ["max_turns", "max_turns_reached", "high_convergence"]:
            state.status = ConversationStatus.COMPLETED
        elif event.reason == "error":
            state.status = ConversationStatus.FAILED
        else:
            state.status = ConversationStatus.INTERRUPTED

    def _handle_turn_complete(
        self, state: ConversationState, event: TurnCompleteEvent
    ) -> None:
        """Process TurnCompleteEvent."""
        turn_num = event.turn_number

        # Update total turns
        state.total_turns = max(state.total_turns, turn_num)

        # Update final convergence score
        if event.convergence_score is not None:
            state.final_convergence_score = event.convergence_score

        # Extract messages from turn
        turn = event.turn

        # Agent A message
        if turn.agent_a_message.content:
            state.messages.append(
                {
                    "conversation_id": event.conversation_id,
                    "turn_number": turn_num,
                    "agent_id": "agent_a",
                    "content": turn.agent_a_message.content,
                    "timestamp": turn.agent_a_message.timestamp,
                    "token_count": state.token_counts.get("agent_a", 0),
                }
            )

        # Agent B message
        if turn.agent_b_message.content:
            state.messages.append(
                {
                    "conversation_id": event.conversation_id,
                    "turn_number": turn_num,
                    "agent_id": "agent_b",
                    "content": turn.agent_b_message.content,
                    "timestamp": turn.agent_b_message.timestamp,
                    "token_count": state.token_counts.get("agent_b", 0),
                }
            )

        # Store turn for metric calculation
        state.turns.append((turn.agent_a_message, turn.agent_b_message))

        # Store turn metrics (only convergence from live calculation)
        state.turn_metrics.append(
            {
                "conversation_id": event.conversation_id,
                "turn_number": turn_num,
                "timestamp": event.timestamp,
                "convergence_score": event.convergence_score or 0.0,
            }
        )

        # Clear token counts for next turn
        state.token_counts.clear()

    def _handle_message_complete(
        self, state: ConversationState, event: MessageCompleteEvent
    ) -> None:
        """Process MessageCompleteEvent to track token usage."""
        # Store token count for this agent
        state.token_counts[event.agent_id] = event.total_tokens

    def _handle_system_prompt(
        self, state: ConversationState, event: SystemPromptEvent
    ) -> None:
        """Process SystemPromptEvent to capture agent names."""
        if event.agent_display_name and event.agent_display_name != event.agent_id:
            state.agent_names[event.agent_id] = event.agent_display_name
