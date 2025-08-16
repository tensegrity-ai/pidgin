"""Metrics calculation for experiments and conversations."""

import json
from typing import Any

from ..config.models import get_model_config
from ..io.logger import get_logger

logger = get_logger("metrics_calculator")


class MetricsCalculator:
    """Calculates token usage and cost metrics for experiments."""

    def estimate_tokens_for_experiment(self, exp: Any) -> int:
        """Get total tokens used in an experiment from manifest.

        Args:
            exp: ExperimentState object with directory attribute

        Returns:
            Total token count
        """
        total_tokens = 0

        # Directly use exp.directory - no fallback
        manifest_path = exp.directory / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)

                # Sum up token usage from all conversations
                for conv_data in manifest.get("conversations", {}).values():
                    if "token_usage" in conv_data:
                        total_tokens += conv_data["token_usage"].get("total", 0)
            except (json.JSONDecodeError, OSError) as e:
                logger.debug(f"Error reading manifest for tokens: {e}")
                # Fallback to estimation based on turns
                total_turns = sum(
                    conv.current_turn for conv in exp.conversations.values()
                )
                return total_turns * 2 * 150  # Rough estimate

        # If no real data, fall back to estimation
        if total_tokens == 0:
            total_turns = sum(conv.current_turn for conv in exp.conversations.values())
            return total_turns * 2 * 150

        return total_tokens

    def estimate_cost_for_experiment(self, exp: Any, total_tokens: int) -> float:
        """Calculate actual cost for an experiment based on real token usage.

        Args:
            exp: ExperimentState object with directory attribute
            total_tokens: Total tokens used (for fallback calculation)

        Returns:
            Estimated cost in dollars
        """
        if not exp.conversations:
            return 0.0

        total_cost = 0.0

        # Directly use exp.directory - no fallback
        manifest_path = exp.directory / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)

                # Calculate cost per conversation based on actual token usage
                for conv_data in manifest.get("conversations", {}).values():
                    if "token_usage" in conv_data:
                        for agent_id in ["agent_a", "agent_b"]:
                            agent_usage = conv_data["token_usage"].get(agent_id, {})
                            model = agent_usage.get("model")
                            prompt_tokens = agent_usage.get("prompt_tokens", 0)
                            completion_tokens = agent_usage.get("completion_tokens", 0)

                            if model and (prompt_tokens > 0 or completion_tokens > 0):
                                config = get_model_config(model)
                                if config and config.input_cost_per_million is not None:
                                    cost = (prompt_tokens / 1_000_000) * (
                                        config.input_cost_per_million or 0
                                    ) + (completion_tokens / 1_000_000) * (
                                        config.output_cost_per_million or 0
                                    )
                                    total_cost += cost
                                else:
                                    # Fallback pricing for models without config
                                    total_cost += (
                                        (prompt_tokens + completion_tokens) / 1_000_000
                                    ) * 2.0

                return total_cost
            except (json.JSONDecodeError, OSError) as e:
                logger.debug(f"Error reading manifest for cost: {e}")

        # Fallback: estimate based on total tokens and model mix
        if exp.conversations:
            first_conv = next(iter(exp.conversations.values()))
            model_a = first_conv.agent_a_model
            model_b = first_conv.agent_b_model

            for model in [model_a, model_b]:
                config = get_model_config(model)
                if config and config.input_cost_per_million is not None:
                    # Assume 70/30 input/output split
                    input_tokens = total_tokens * 0.7 / 2
                    output_tokens = total_tokens * 0.3 / 2

                    cost = (input_tokens / 1_000_000) * (
                        config.input_cost_per_million or 0
                    ) + (output_tokens / 1_000_000) * (
                        config.output_cost_per_million or 0
                    )
                    total_cost += cost
                else:
                    total_cost += (total_tokens / 2_000_000) * 2.0

        return total_cost
