"""Deserializers for conversation lifecycle events."""

from datetime import datetime
from typing import Any, Dict

from ...core.events import (
    ConversationBranchedEvent,
    ConversationEndEvent,
    ConversationPausedEvent,
    ConversationResumedEvent,
    ConversationStartEvent,
    ExperimentCompleteEvent,
    PostProcessingCompleteEvent,
    PostProcessingStartEvent,
    Turn,
    TurnCompleteEvent,
    TurnStartEvent,
)
from .base import BaseDeserializer


class ConversationDeserializer(BaseDeserializer):
    """Deserialize conversation lifecycle events."""

    @classmethod
    def build_conversation_start(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationStartEvent:
        """Build ConversationStartEvent from data."""
        event = ConversationStartEvent(
            conversation_id=data["conversation_id"],
            agent_a=data["agent_a"],
            agent_b=data["agent_b"],
            experiment_id=data.get("experiment_id"),
            config=data.get("config", {}),
            agent_a_display_name=data.get("agent_a_display_name"),
            agent_b_display_name=data.get("agent_b_display_name"),
            agent_a_model=data.get("agent_a_model"),
            agent_b_model=data.get("agent_b_model"),
            max_turns=data.get("max_turns"),
            initial_prompt=data.get("initial_prompt"),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_conversation_end(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationEndEvent:
        """Build ConversationEndEvent from data."""
        event = ConversationEndEvent(
            conversation_id=data["conversation_id"],
            total_turns=data.get("total_turns", 0),
            status=data.get("status", "completed"),
            experiment_id=data.get("experiment_id"),
            reason=data.get("reason"),
            error=data.get("error"),
            duration_ms=data.get("duration_ms", 0),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_turn_start(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> TurnStartEvent:
        """Build TurnStartEvent from data."""
        event = TurnStartEvent(
            conversation_id=data["conversation_id"],
            turn_number=data["turn_number"],
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_turn_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> TurnCompleteEvent:
        """Build TurnCompleteEvent from data."""
        from ...core.types import Message

        # Build Message objects for the Turn
        agent_a_msg = Message(
            role="assistant",
            content=data.get("agent_a_message", ""),
            agent_id="agent_a",
        )

        agent_b_msg = Message(
            role="assistant",
            content=data.get("agent_b_message", ""),
            agent_id="agent_b",
        )

        # Create the Turn object with both messages
        turn = Turn(
            agent_a_message=agent_a_msg,
            agent_b_message=agent_b_msg,
        )

        # Create the event
        event = TurnCompleteEvent(
            conversation_id=data["conversation_id"],
            turn_number=data["turn_number"],
            turn=turn,
            convergence_score=data.get("convergence_score"),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_conversation_paused(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationPausedEvent:
        """Build ConversationPausedEvent from data."""
        event = ConversationPausedEvent(
            conversation_id=data["conversation_id"],
            turn_number=data.get("turn_number", 0),
            paused_during=data.get("paused_during", "between_turns"),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_conversation_resumed(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationResumedEvent:
        """Build ConversationResumedEvent from data."""
        event = ConversationResumedEvent(
            conversation_id=data["conversation_id"],
            turn_number=data.get("turn_number", 0),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_conversation_branched(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationBranchedEvent:
        """Build ConversationBranchedEvent from data."""
        event = ConversationBranchedEvent(
            conversation_id=data.get(
                "new_conversation_id", data.get("conversation_id")
            ),
            source_conversation_id=data.get(
                "original_conversation_id", data.get("source_conversation_id")
            ),
            branch_point=data.get("branch_point_turn", data.get("branch_point", 0)),
            parameter_changes=data.get("parameter_changes", {}),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_experiment_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ExperimentCompleteEvent:
        """Build ExperimentCompleteEvent from data."""
        event = ExperimentCompleteEvent(
            experiment_id=data["experiment_id"],
            total_conversations=data["total_conversations"],
            completed_conversations=data.get(
                "successful_conversations", data.get("completed_conversations", 0)
            ),
            failed_conversations=data.get("failed_conversations", 0),
            status=data.get("status", "completed"),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_post_processing_start(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> PostProcessingStartEvent:
        """Build PostProcessingStartEvent from data."""
        event = PostProcessingStartEvent(
            experiment_id=data["experiment_id"],
            tasks=data.get("tasks", []),
        )
        event.timestamp = timestamp
        return event

    @classmethod
    def build_post_processing_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> PostProcessingCompleteEvent:
        """Build PostProcessingCompleteEvent from data."""
        event = PostProcessingCompleteEvent(
            experiment_id=data["experiment_id"],
            tasks_completed=data.get("tasks_completed", []),
            tasks_failed=data.get("tasks_failed", []),
            duration_ms=int(data.get("duration_seconds", 0) * 1000),
        )
        event.timestamp = timestamp
        return event
