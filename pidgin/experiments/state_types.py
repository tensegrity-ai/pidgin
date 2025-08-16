"""Data types for experiment state management."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..core.constants import ConversationStatus, ExperimentStatus


@dataclass
class ConversationState:
    """Lightweight state for a single conversation."""

    conversation_id: str
    experiment_id: str
    status: str = ConversationStatus.CREATED
    current_turn: int = 0
    max_turns: int = 20
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    agent_a_model: str = "unknown"
    agent_b_model: str = "unknown"
    convergence_scores: List[float] = field(default_factory=list)
    last_convergence: Optional[float] = None
    error_message: Optional[str] = None
    truncation_count: int = 0
    last_truncation_turn: Optional[int] = None


@dataclass
class ExperimentState:
    """Lightweight state for an experiment."""

    experiment_id: str
    name: str
    status: str = ExperimentStatus.CREATED
    total_conversations: int = 0
    completed_conversations: int = 0
    failed_conversations: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    conversations: Dict[str, ConversationState] = field(default_factory=dict)
    error: Optional[str] = None
    directory: Optional[Path] = None  # Full path to experiment directory

    @property
    def active_conversations(self) -> int:
        """Count of currently running conversations."""
        return sum(
            1
            for c in self.conversations.values()
            if c.status == ConversationStatus.RUNNING
        )

    @property
    def progress(self) -> tuple[int, int]:
        """Return (completed, total) conversations."""
        return (
            self.completed_conversations + self.failed_conversations,
            self.total_conversations,
        )
