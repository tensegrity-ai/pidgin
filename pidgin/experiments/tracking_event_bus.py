# pidgin/experiments/tracking_event_bus.py
"""Event bus wrapper that tracks progress in manifest."""

from pathlib import Path

from ..core.constants import ConversationStatus
from ..core.event_bus import EventBus
from ..core.events import (
    ConversationEndEvent,
    ConversationStartEvent,
    ErrorEvent,
    Event,
    ThinkingCompleteEvent,
    TokenUsageEvent,
    TurnCompleteEvent,
)
from .manifest import ManifestManager


class TrackingEventBus(EventBus):
    """EventBus that updates manifest with progress."""

    def __init__(
        self,
        experiment_dir: Path,
        conversation_id: str,
        db_store=None,
        max_history_size: int = 1000,
    ):
        """Initialize tracking event bus.

        Args:
            experiment_dir: Experiment directory containing manifest
            conversation_id: ID of the conversation being tracked
            db_store: Optional database store (not used in JSONL-first approach)
            max_history_size: Maximum events to keep in memory
        """
        super().__init__(
            db_store=db_store,
            event_log_dir=experiment_dir,
            max_history_size=max_history_size,
        )

        self.experiment_dir = experiment_dir
        self.conversation_id = conversation_id
        self.manifest = ManifestManager(experiment_dir)
        self.line_count = 0
        self.total_turns = 0

    async def emit(self, event: Event) -> None:
        """Emit event and update manifest progress.

        Args:
            event: Event to emit
        """
        # Call parent emit first
        await super().emit(event)

        # Track line count
        self.line_count += 1

        # Update manifest based on event type
        if isinstance(event, ConversationStartEvent):
            self.manifest.update_conversation(
                self.conversation_id,
                status=ConversationStatus.RUNNING,
                last_line=self.line_count,
            )

        elif isinstance(event, TurnCompleteEvent):
            self.total_turns += 1
            self.manifest.update_conversation(
                self.conversation_id,
                last_line=self.line_count,
                total_turns=self.total_turns,
            )

        elif isinstance(event, ConversationEndEvent):
            # Map reasons to completed status
            completed_reasons = ["max_turns", "max_turns_reached", "high_convergence"]
            status = (
                ConversationStatus.COMPLETED
                if event.reason in completed_reasons
                else event.reason
            )
            self.manifest.update_conversation(
                self.conversation_id,
                status=status,
                last_line=self.line_count,
                total_turns=self.total_turns,
            )
            # Close JSONL file on conversation end
            self.close_conversation_log(self.conversation_id)

        elif isinstance(event, TokenUsageEvent):
            # Determine which agent based on event data
            agent_id = "agent_a" if event.agent_id == "agent_a" else "agent_b"
            self.manifest.update_token_usage(
                self.conversation_id,
                agent_id,
                event.prompt_tokens,
                event.completion_tokens,
                event.model,
            )

        elif isinstance(event, ThinkingCompleteEvent):
            # Track thinking token usage separately
            agent_id = "agent_a" if event.agent_id == "agent_a" else "agent_b"
            self.manifest.update_thinking_tokens(
                self.conversation_id,
                agent_id,
                event.thinking_tokens or 0,
            )

        elif isinstance(event, ErrorEvent):
            self.manifest.update_conversation(
                self.conversation_id,
                status=ConversationStatus.FAILED,
                last_line=self.line_count,
                error=event.error_message,
            )
            # Close JSONL file on error
            self.close_conversation_log(self.conversation_id)
