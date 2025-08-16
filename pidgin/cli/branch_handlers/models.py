"""Data models for branch command components."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class BranchSource:
    """Source conversation data for branching."""

    conversation_id: str
    experiment_dir: Path
    config: Dict[str, Any]
    messages: List[Any]
    metadata: Dict[str, Any]
    branch_point: int

    def get_info(self) -> str:
        """Format source info for display."""
        return "\n".join(
            [
                f"Source: {self.experiment_dir.name}",
                f"Conversation: {self.conversation_id}",
                f"Branch point: Turn {self.branch_point} of {len(self.messages)}",
                f"Original models: {self.config['agent_a_model']} ↔ {self.config['agent_b_model']}",
            ]
        )
