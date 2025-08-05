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
        return ConversationStartEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            agent_a_model=data["agent_a_model"],
            agent_b_model=data["agent_b_model"],
            agent_a_provider=data.get("agent_a_provider"),
            agent_b_provider=data.get("agent_b_provider"),
            initial_prompt=data["initial_prompt"],
            max_turns=data["max_turns"],
            temperature_a=data.get("temperature_a"),
            temperature_b=data.get("temperature_b"),
            agent_a_display_name=data.get("agent_a_display_name"),
            agent_b_display_name=data.get("agent_b_display_name"),
        )

    @classmethod
    def build_conversation_end(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationEndEvent:
        """Build ConversationEndEvent from data."""
        return ConversationEndEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            total_turns=data["total_turns"],
            reason=data["reason"],
            duration_ms=data.get("duration_ms", 0),
        )

    @classmethod
    def build_turn_start(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> TurnStartEvent:
        """Build TurnStartEvent from data."""
        return TurnStartEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            turn_number=data["turn_number"],
        )

    @classmethod
    def build_turn_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> TurnCompleteEvent:
        """Build TurnCompleteEvent from data."""
        # Build Turn objects for agent messages
        agent_a_turn = None
        agent_b_turn = None

        if "agent_a_message" in data:
            agent_a_turn = Turn(
                agent_id="agent_a",
                message=data["agent_a_message"],
                tokens_used=data.get("agent_a_tokens", 0),
                timestamp=timestamp,
            )

        if "agent_b_message" in data:
            agent_b_turn = Turn(
                agent_id="agent_b",
                message=data["agent_b_message"],
                tokens_used=data.get("agent_b_tokens", 0),
                timestamp=timestamp,
            )

        return TurnCompleteEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            turn_number=data["turn_number"],
            agent_a_turn=agent_a_turn,
            agent_b_turn=agent_b_turn,
            convergence_score=data.get("convergence_score"),
            vocabulary_overlap=data.get("vocabulary_overlap"),
            style_similarity=data.get("style_similarity"),
            topic_consistency=data.get("topic_consistency"),
        )

    @classmethod
    def build_conversation_paused(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationPausedEvent:
        """Build ConversationPausedEvent from data."""
        return ConversationPausedEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            turn_number=data.get("turn_number", 0),
            reason=data.get("reason", "user_interrupt"),
        )

    @classmethod
    def build_conversation_resumed(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationResumedEvent:
        """Build ConversationResumedEvent from data."""
        return ConversationResumedEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            turn_number=data.get("turn_number", 0),
        )

    @classmethod
    def build_conversation_branched(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ConversationBranchedEvent:
        """Build ConversationBranchedEvent from data."""
        return ConversationBranchedEvent(
            timestamp=timestamp,
            original_conversation_id=data["original_conversation_id"],
            new_conversation_id=data["new_conversation_id"],
            branch_point_turn=data["branch_point_turn"],
            reason=data.get("reason", "manual_branch"),
        )

    @classmethod
    def build_experiment_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ExperimentCompleteEvent:
        """Build ExperimentCompleteEvent from data."""
        return ExperimentCompleteEvent(
            timestamp=timestamp,
            experiment_id=data["experiment_id"],
            total_conversations=data["total_conversations"],
            successful_conversations=data["successful_conversations"],
            failed_conversations=data["failed_conversations"],
            duration_seconds=data["duration_seconds"],
        )

    @classmethod
    def build_post_processing_start(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> PostProcessingStartEvent:
        """Build PostProcessingStartEvent from data."""
        return PostProcessingStartEvent(
            timestamp=timestamp,
            experiment_id=data["experiment_id"],
        )

    @classmethod
    def build_post_processing_complete(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> PostProcessingCompleteEvent:
        """Build PostProcessingCompleteEvent from data."""
        return PostProcessingCompleteEvent(
            timestamp=timestamp,
            experiment_id=data["experiment_id"],
            duration_seconds=data.get("duration_seconds", 0),
        )