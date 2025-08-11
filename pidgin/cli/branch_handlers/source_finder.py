"""Find and load source conversations for branching."""

from pathlib import Path
from typing import Optional

from ...experiments.state_builder import StateBuilder
from .models import BranchSource


class BranchSourceFinder:
    """Find and load source conversations for branching."""

    def __init__(self, experiments_dir: Path):
        self.experiments_dir = experiments_dir
        self.state_builder = StateBuilder()

    def find_conversation(
        self, conversation_id: str, turn: Optional[int] = None
    ) -> Optional[BranchSource]:
        """Find conversation and return source data.

        Args:
            conversation_id: ID of conversation to find
            turn: Optional turn number to branch from

        Returns:
            BranchSource if found, None otherwise
        """
        for exp_dir in self.experiments_dir.glob("exp_*"):
            if not exp_dir.is_dir():
                continue

            state = self.state_builder.get_conversation_state(
                exp_dir, conversation_id, turn
            )
            if state:
                return BranchSource(
                    conversation_id=conversation_id,
                    experiment_dir=exp_dir,
                    config=state["config"],
                    messages=state["messages"],
                    metadata=state["metadata"],
                    branch_point=state["branch_point"],
                )
        return None