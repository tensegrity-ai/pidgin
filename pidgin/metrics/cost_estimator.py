# pidgin/metrics/cost_estimator.py
"""Simple cost estimation for AI conversations."""

from typing import Any, Dict, List, Tuple

from ..config.models import get_model_config
from ..core.types import Message


class CostEstimator:
    """Estimate costs for AI API usage."""

    # Same as context manager
    CHARS_PER_TOKEN = 3.5

    def get_model_pricing(self, model_id: str) -> Tuple[float, float]:
        """Get pricing for a model from its configuration.

        Returns:
            Tuple of (input_cost_per_million, output_cost_per_million)
        """
        # Try to get from model config first
        config = get_model_config(model_id)
        if config and config.input_cost_per_million is not None:
            return (
                config.input_cost_per_million or 0.0,
                config.output_cost_per_million or 0.0,
            )

        # Fallback for unknown models or models without pricing
        # Conservative estimate
        return (2.00, 8.00)

    def estimate_message_cost(
        self, message: Message, model: str, is_input: bool = True
    ) -> float:
        """Estimate cost for a single message."""
        tokens = len(message.content) / self.CHARS_PER_TOKEN

        # Get pricing for model
        pricing = self.get_model_pricing(model)
        rate = pricing[0] if is_input else pricing[1]

        # Cost per million tokens
        return (tokens / 1_000_000) * rate

    def estimate_conversation_cost(
        self, messages: List[Message], model_a: str, model_b: str
    ) -> Dict[str, Any]:
        """Estimate total cost for a conversation."""
        cost_a_input = 0.0
        cost_a_output = 0.0
        cost_b_input = 0.0
        cost_b_output = 0.0

        # For each turn, both models see all previous messages as input
        for i, msg in enumerate(messages):
            if msg.role == "system":
                # System messages are input for both
                cost_a_input += self.estimate_message_cost(msg, model_a, is_input=True)
                cost_b_input += self.estimate_message_cost(msg, model_b, is_input=True)
            elif msg.agent_id == "agent_a":
                # A's output
                cost_a_output += self.estimate_message_cost(
                    msg, model_a, is_input=False
                )
                # B sees it as input
                cost_b_input += self.estimate_message_cost(msg, model_b, is_input=True)
            elif msg.agent_id == "agent_b":
                # B's output
                cost_b_output += self.estimate_message_cost(
                    msg, model_b, is_input=False
                )
                # A sees it as input
                cost_a_input += self.estimate_message_cost(msg, model_a, is_input=True)

        return {
            "model_a_total": cost_a_input + cost_a_output,
            "model_b_total": cost_b_input + cost_b_output,
            "total": cost_a_input + cost_a_output + cost_b_input + cost_b_output,
            "breakdown": {
                "model_a_input": cost_a_input,
                "model_a_output": cost_a_output,
                "model_b_input": cost_b_input,
                "model_b_output": cost_b_output,
            },
        }

    def format_cost(self, cost: float) -> str:
        """Format cost for display."""
        if cost < 0.01:
            return f"${cost:.4f}"
        elif cost < 1.00:
            return f"${cost:.3f}"
        else:
            return f"${cost:.2f}"
