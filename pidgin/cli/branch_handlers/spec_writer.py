"""Handle branch specification file operations."""

from typing import Any, Dict, List, Optional

import yaml


class BranchSpecWriter:
    """Handle branch specification file operations."""

    def save_spec(
        self,
        spec_path: str,
        branch_config: Dict[str, Any],
        metadata: Dict[str, Any],
        messages: List[Any],
        name: str,
        repetitions: int,
        conversation_id: str,
        branch_point: int,
    ) -> Optional[str]:
        """Save branch specification to YAML file.

        Returns:
            Error message if failed, None if successful
        """
        spec_data = {
            "name": name,
            "agent_a_model": branch_config["agent_a_model"],
            "agent_b_model": branch_config["agent_b_model"],
            "repetitions": repetitions,
            "max_turns": branch_config["max_turns"],
            "temperature_a": branch_config.get("temperature_a"),
            "temperature_b": branch_config.get("temperature_b"),
            "awareness_a": branch_config.get("awareness_a", "basic"),
            "awareness_b": branch_config.get("awareness_b", "basic"),
            "branch_from": {
                "conversation_id": conversation_id,
                "turn": branch_point,
                "experiment_id": metadata.get("original_experiment_id"),
            },
            "initial_messages": [
                {"role": msg.role, "content": msg.content} for msg in messages
            ],
        }

        try:
            with open(spec_path, "w") as f:
                yaml.dump(spec_data, f, default_flow_style=False)
            return None
        except Exception as e:
            return str(e)
