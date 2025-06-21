# pidgin/metrics/cost_estimator.py
"""Simple cost estimation for AI conversations."""

from typing import Dict, Tuple
from ..core.types import Message


class CostEstimator:
    """Estimate costs for AI API usage."""
    
    # Pricing per 1M tokens (as of late 2024)
    # Format: (input_cost, output_cost) in USD
    PRICING = {
        # Anthropic
        "claude-3-5-sonnet-20241022": (3.00, 15.00),
        "claude-3-5-haiku-20241022": (1.00, 5.00),
        "claude-3-opus-20240229": (15.00, 75.00),
        
        # OpenAI
        "gpt-4o": (2.50, 10.00),
        "gpt-4o-mini": (0.15, 0.60),
        "o1-preview": (15.00, 60.00),
        "o1-mini": (3.00, 12.00),
        
        # Google
        "gemini-1.5-pro": (1.25, 5.00),
        "gemini-1.5-flash": (0.075, 0.30),
        "gemini-2.0-flash-exp": (0.00, 0.00),  # Free during preview
        
        # xAI
        "grok-beta": (5.00, 15.00),
        "grok-2-beta": (2.00, 10.00),
        
        # Local models
        "local": (0.00, 0.00),  # Free!
    }
    
    # Same as context manager
    CHARS_PER_TOKEN = 3.5
    
    def estimate_message_cost(
        self, 
        message: Message, 
        model: str, 
        is_input: bool = True
    ) -> float:
        """Estimate cost for a single message."""
        tokens = len(message.content) / self.CHARS_PER_TOKEN
        
        # Get pricing for model
        pricing = self.PRICING.get(model, (0.0, 0.0))
        rate = pricing[0] if is_input else pricing[1]
        
        # Cost per million tokens
        return (tokens / 1_000_000) * rate
    
    def estimate_conversation_cost(
        self,
        messages: List[Message],
        model_a: str,
        model_b: str
    ) -> Dict[str, float]:
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
                cost_a_output += self.estimate_message_cost(msg, model_a, is_input=False)
                # B sees it as input
                cost_b_input += self.estimate_message_cost(msg, model_b, is_input=True)
            elif msg.agent_id == "agent_b":
                # B's output
                cost_b_output += self.estimate_message_cost(msg, model_b, is_input=False)
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
            }
        }
    
    def format_cost(self, cost: float) -> str:
        """Format cost for display."""
        if cost < 0.01:
            return f"${cost:.4f}"
        elif cost < 1.00:
            return f"${cost:.3f}"
        else:
            return f"${cost:.2f}"