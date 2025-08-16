# pidgin/cli/branch_handlers/source_finder.py

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pidgin.experiments.state_builder import StateBuilder
from pidgin.experiments.state_types import ConversationState

from .models import BranchSource


class BranchSourceFinder:
    def __init__(self):
        self.state_builder = StateBuilder()

    def find_conversation(
        self, exp_dir: Path, conversation_id: str, turn: Optional[int] = None
    ) -> Optional[BranchSource]:
        """Find a conversation and prepare it for branching."""

        # Get the state object (lightweight metadata)
        state = self.state_builder.get_conversation_state(exp_dir, conversation_id)
        if not state:
            return None

        # Load what we actually need for branching
        messages = self._load_messages(exp_dir, conversation_id, turn)
        config = self._load_experiment_config(exp_dir, state)

        # Build metadata from state
        metadata = {
            "status": state.status,
            "current_turn": state.current_turn,
            "started_at": state.started_at.isoformat() if state.started_at else None,
            "completed_at": state.completed_at.isoformat()
            if state.completed_at
            else None,
            "convergence_scores": state.convergence_scores,
            "last_convergence": state.last_convergence,
        }

        # Determine branch point
        branch_point = turn if turn is not None else state.current_turn

        return BranchSource(
            conversation_id=conversation_id,
            experiment_dir=exp_dir,
            config=config,
            messages=messages,
            metadata=metadata,
            branch_point=branch_point,
        )

    def _load_messages(
        self, exp_dir: Path, conversation_id: str, up_to_turn: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Load messages from JSONL event files."""
        messages = []

        # Look for conversation JSONL file
        jsonl_path = exp_dir / f"conversation_{conversation_id}.jsonl"
        if not jsonl_path.exists():
            # Try the events file as fallback
            jsonl_path = exp_dir / "events.jsonl"

        if jsonl_path.exists():
            with open(jsonl_path, "r") as f:
                for line in f:
                    event = json.loads(line)
                    # Filter for message events
                    if event.get("type") in ["message_sent", "response_received"]:
                        turn_num = event.get("data", {}).get("turn", 0)
                        if up_to_turn is None or turn_num <= up_to_turn:
                            messages.append(event.get("data", {}).get("message", {}))

        return messages

    def _load_experiment_config(
        self, exp_dir: Path, state: ConversationState
    ) -> Dict[str, Any]:
        """Load or reconstruct experiment configuration."""

        # Try to load from experiment config file
        config_path = exp_dir / "experiment_config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                return json.load(f)

        # Fallback: reconstruct from state
        return {
            "max_turns": state.max_turns,
            "agents": {
                "agent_a": {"model": state.agent_a_model},
                "agent_b": {"model": state.agent_b_model},
            },
            "experiment_id": state.experiment_id,
            # Add other config fields as needed
        }
