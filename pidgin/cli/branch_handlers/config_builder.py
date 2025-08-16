"""Build configuration for branched experiments."""

from typing import Any, Dict, List, Optional

from ...experiments import ExperimentConfig
from ..helpers import validate_model_id


class BranchConfigBuilder:
    """Build configuration for branched experiments."""

    def __init__(self, original_config: Dict[str, Any]):
        self.original_config = original_config
        self.branch_config = original_config.copy()

    def apply_model_overrides(
        self, agent_a: Optional[str], agent_b: Optional[str]
    ) -> List[str]:
        """Apply model overrides and return any errors."""
        errors = []
        if agent_a:
            try:
                self.branch_config["agent_a_model"] = validate_model_id(agent_a)[0]
            except ValueError as e:
                errors.append(f"Invalid agent A model: {e}")

        if agent_b:
            try:
                self.branch_config["agent_b_model"] = validate_model_id(agent_b)[0]
            except ValueError as e:
                errors.append(f"Invalid agent B model: {e}")

        return errors

    def apply_temperature_overrides(
        self,
        temperature: Optional[float],
        temp_a: Optional[float],
        temp_b: Optional[float],
    ):
        """Apply temperature overrides."""
        if temperature is not None:
            self.branch_config["temperature_a"] = temperature
            self.branch_config["temperature_b"] = temperature
        if temp_a is not None:
            self.branch_config["temperature_a"] = temp_a
        if temp_b is not None:
            self.branch_config["temperature_b"] = temp_b

    def apply_awareness_overrides(
        self,
        awareness: Optional[str],
        awareness_a: Optional[str],
        awareness_b: Optional[str],
    ):
        """Apply awareness overrides."""
        if awareness:
            self.branch_config["awareness_a"] = awareness
            self.branch_config["awareness_b"] = awareness
        if awareness_a:
            self.branch_config["awareness_a"] = awareness_a
        if awareness_b:
            self.branch_config["awareness_b"] = awareness_b

    def apply_other_overrides(self, max_turns: Optional[int]):
        """Apply other parameter overrides."""
        if max_turns is not None:
            self.branch_config["max_turns"] = max_turns

    def get_changes(self) -> List[str]:
        """Get list of configuration changes."""
        changes = []

        if self.branch_config["agent_a_model"] != self.original_config["agent_a_model"]:
            changes.append(
                f"Agent A: {self.original_config['agent_a_model']} → "
                f"{self.branch_config['agent_a_model']}"
            )

        if self.branch_config["agent_b_model"] != self.original_config["agent_b_model"]:
            changes.append(
                f"Agent B: {self.original_config['agent_b_model']} → "
                f"{self.branch_config['agent_b_model']}"
            )

        if self.branch_config.get("temperature_a") != self.original_config.get(
            "temperature_a"
        ):
            changes.append(
                f"Temp A: {self.original_config.get('temperature_a', 'default')} → "
                f"{self.branch_config.get('temperature_a')}"
            )

        if self.branch_config.get("temperature_b") != self.original_config.get(
            "temperature_b"
        ):
            changes.append(
                f"Temp B: {self.original_config.get('temperature_b', 'default')} → "
                f"{self.branch_config.get('temperature_b')}"
            )

        return changes

    def build_experiment_config(
        self,
        name: str,
        repetitions: int,
        messages: List[Any],
        conversation_id: str,
        branch_point: int,
    ) -> ExperimentConfig:
        """Build ExperimentConfig for the branch."""
        return ExperimentConfig(
            name=name,
            agent_a_model=self.branch_config["agent_a_model"],
            agent_b_model=self.branch_config["agent_b_model"],
            repetitions=repetitions,
            max_turns=self.branch_config["max_turns"],
            temperature_a=self.branch_config.get("temperature_a"),
            temperature_b=self.branch_config.get("temperature_b"),
            custom_prompt=self.branch_config.get("initial_prompt"),
            awareness_a=self.branch_config.get("awareness_a", "basic"),
            awareness_b=self.branch_config.get("awareness_b", "basic"),
            prompt_tag=self.branch_config.get("prompt_tag"),
            branch_from_conversation=conversation_id,
            branch_from_turn=branch_point,
            branch_messages=messages,
        )
