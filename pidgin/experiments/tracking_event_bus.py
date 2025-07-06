# pidgin/experiments/tracking_event_bus.py
"""Event bus wrapper that tracks progress in manifest."""

from typing import Optional
from pathlib import Path

from ..core.event_bus import EventBus
from ..core.events import (
    Event, TurnCompleteEvent, ConversationEndEvent, 
    ConversationStartEvent, ErrorEvent
)
from .manifest import ManifestManager


class TrackingEventBus(EventBus):
    """EventBus that updates manifest with progress."""
    
    def __init__(self, experiment_dir: Path, conversation_id: str, 
                 db_store=None, max_history_size: int = 1000):
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
            max_history_size=max_history_size
        )
        
        self.experiment_dir = experiment_dir
        self.conversation_id = conversation_id
        self.manifest = ManifestManager(experiment_dir)
        self.line_count = 0
        self.turns_completed = 0
    
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
                status="running",
                last_line=self.line_count
            )
        
        elif isinstance(event, TurnCompleteEvent):
            self.turns_completed += 1
            self.manifest.update_conversation(
                self.conversation_id,
                last_line=self.line_count,
                turns_completed=self.turns_completed
            )
        
        elif isinstance(event, ConversationEndEvent):
            # Map reasons to completed status
            completed_reasons = ["max_turns", "max_turns_reached", "high_convergence"]
            status = "completed" if event.reason in completed_reasons else event.reason
            self.manifest.update_conversation(
                self.conversation_id,
                status=status,
                last_line=self.line_count,
                turns_completed=self.turns_completed
            )
            # Close JSONL file on conversation end
            self.close_conversation_log(self.conversation_id)
        
        elif isinstance(event, ErrorEvent):
            self.manifest.update_conversation(
                self.conversation_id,
                status="failed",
                last_line=self.line_count,
                error=event.error_message
            )
            # Close JSONL file on error
            self.close_conversation_log(self.conversation_id)