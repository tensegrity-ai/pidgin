"""Tests for CostEstimator."""

from unittest.mock import Mock

import pytest

from pidgin.core.types import Message
from pidgin.metrics.cost_estimator import CostEstimator


class TestCostEstimator:
    """Test CostEstimator functionality."""

    @pytest.fixture
    def cost_estimator(self):
        """Create a CostEstimator instance."""
        return CostEstimator()

    @pytest.fixture
    def sample_message(self):
        """Create a sample message for testing."""
        message = Mock(spec=Message)
        message.content = "This is a test message with some content"
        message.role = "user"
        message.agent_id = "agent_a"
        return message

    def test_init(self, cost_estimator):
        """Test cost estimator initialization."""
        assert hasattr(cost_estimator, "CHARS_PER_TOKEN")
        assert cost_estimator.CHARS_PER_TOKEN == 3.5
        
        # Test that we can get pricing for common models
        # These should return non-zero values from model configs
        claude_input, claude_output = cost_estimator.get_model_pricing("claude-3-5-sonnet-20241022")
        assert claude_input > 0
        assert claude_output > 0
        
        gpt_input, gpt_output = cost_estimator.get_model_pricing("gpt-4o")
        assert gpt_input > 0
        assert gpt_output > 0

    def test_pricing_structure(self, cost_estimator):
        """Test pricing structure is correct."""
        # Test a few known models
        test_models = ["claude-3-5-sonnet-20241022", "gpt-4o", "gemini-2.0-flash-exp"]
        
        for model in test_models:
            input_cost, output_cost = cost_estimator.get_model_pricing(model)
            assert isinstance(input_cost, (int, float))
            assert isinstance(output_cost, (int, float))
            assert input_cost >= 0  # costs should be non-negative
            assert output_cost >= 0

    def test_estimate_message_cost_input(self, cost_estimator, sample_message):
        """Test message cost estimation for input."""
        # Use a known model
        model = "claude-3-5-sonnet-20241022"
        cost = cost_estimator.estimate_message_cost(
            sample_message, model, is_input=True
        )

        expected_tokens = len(sample_message.content) / cost_estimator.CHARS_PER_TOKEN
        input_cost_per_million, _ = cost_estimator.get_model_pricing(model)
        expected_cost = (expected_tokens / 1_000_000) * input_cost_per_million

        assert cost == expected_cost
        assert cost > 0  # Should have some cost

    def test_estimate_message_cost_output(self, cost_estimator, sample_message):
        """Test message cost estimation for output."""
        model = "claude-3-5-sonnet-20241022"
        cost = cost_estimator.estimate_message_cost(
            sample_message, model, is_input=False
        )

        expected_tokens = len(sample_message.content) / cost_estimator.CHARS_PER_TOKEN
        _, output_cost_per_million = cost_estimator.get_model_pricing(model)
        expected_cost = (expected_tokens / 1_000_000) * output_cost_per_million

        assert cost == expected_cost
        assert cost > 0

    def test_estimate_message_cost_unknown_model(self, cost_estimator, sample_message):
        """Test message cost estimation for unknown model."""
        cost = cost_estimator.estimate_message_cost(
            sample_message, "unknown-model", is_input=True
        )
        # Should use fallback pricing (2.00 per million tokens for input)
        expected_tokens = len(sample_message.content) / cost_estimator.CHARS_PER_TOKEN
        expected_cost = (expected_tokens / 1_000_000) * 2.00
        assert cost == expected_cost
        assert cost > 0

    def test_estimate_message_cost_local_model(self, cost_estimator, sample_message):
        """Test message cost estimation for local model."""
        cost_input = cost_estimator.estimate_message_cost(
            sample_message, "local", is_input=True
        )
        cost_output = cost_estimator.estimate_message_cost(
            sample_message, "local", is_input=False
        )

        # Local models might use fallback pricing now
        # Check if local:test has pricing set to 0
        input_price, output_price = cost_estimator.get_model_pricing("local")
        if input_price == 0 and output_price == 0:
            assert cost_input == 0.0
            assert cost_output == 0.0
        else:
            # Fallback pricing
            assert cost_input > 0
            assert cost_output > 0

    def test_estimate_message_cost_empty_message(self, cost_estimator):
        """Test message cost estimation for empty message."""
        empty_message = Mock(spec=Message)
        empty_message.content = ""
        empty_message.role = "user"
        empty_message.agent_id = "agent_a"

        cost = cost_estimator.estimate_message_cost(
            empty_message, "claude-3-5-sonnet-20241022", is_input=True
        )
        assert cost == 0.0

    def test_estimate_conversation_cost_basic(self, cost_estimator):
        """Test basic conversation cost estimation."""
        # Create test messages
        system_msg = Mock(spec=Message)
        system_msg.content = "You are a helpful assistant."
        system_msg.role = "system"
        system_msg.agent_id = None

        user_msg = Mock(spec=Message)
        user_msg.content = "Hello, how are you?"
        user_msg.role = "user"
        user_msg.agent_id = "agent_a"

        assistant_msg = Mock(spec=Message)
        assistant_msg.content = "I'm doing well, thank you!"
        assistant_msg.role = "assistant"
        assistant_msg.agent_id = "agent_b"

        messages = [system_msg, user_msg, assistant_msg]

        cost_breakdown = cost_estimator.estimate_conversation_cost(
            messages, "claude-3-5-sonnet-20241022", "gpt-4o"
        )

        # Check structure
        assert "model_a_total" in cost_breakdown
        assert "model_b_total" in cost_breakdown
        assert "total" in cost_breakdown
        assert "breakdown" in cost_breakdown

        # Check breakdown structure
        breakdown = cost_breakdown["breakdown"]
        assert "model_a_input" in breakdown
        assert "model_a_output" in breakdown
        assert "model_b_input" in breakdown
        assert "model_b_output" in breakdown

        # Check calculations
        assert (
            cost_breakdown["model_a_total"]
            == breakdown["model_a_input"] + breakdown["model_a_output"]
        )
        assert (
            cost_breakdown["model_b_total"]
            == breakdown["model_b_input"] + breakdown["model_b_output"]
        )
        assert (
            cost_breakdown["total"]
            == cost_breakdown["model_a_total"] + cost_breakdown["model_b_total"]
        )

        # All values should be non-negative
        for key, value in cost_breakdown.items():
            if key != "breakdown":
                assert value >= 0

        for key, value in breakdown.items():
            assert value >= 0

    def test_estimate_conversation_cost_system_messages(self, cost_estimator):
        """Test conversation cost with system messages."""
        system_msg = Mock(spec=Message)
        system_msg.content = "System prompt here"
        system_msg.role = "system"
        system_msg.agent_id = None

        messages = [system_msg]

        cost_breakdown = cost_estimator.estimate_conversation_cost(
            messages, "claude-3-5-sonnet-20241022", "gpt-4o"
        )

        # System messages should be input for both models
        assert cost_breakdown["breakdown"]["model_a_input"] > 0
        assert cost_breakdown["breakdown"]["model_b_input"] > 0
        assert cost_breakdown["breakdown"]["model_a_output"] == 0
        assert cost_breakdown["breakdown"]["model_b_output"] == 0

    def test_estimate_conversation_cost_agent_messages(self, cost_estimator):
        """Test conversation cost with agent messages."""
        agent_a_msg = Mock(spec=Message)
        agent_a_msg.content = "Message from agent A"
        agent_a_msg.role = "user"
        agent_a_msg.agent_id = "agent_a"

        agent_b_msg = Mock(spec=Message)
        agent_b_msg.content = "Message from agent B"
        agent_b_msg.role = "assistant"
        agent_b_msg.agent_id = "agent_b"

        messages = [agent_a_msg, agent_b_msg]

        cost_breakdown = cost_estimator.estimate_conversation_cost(
            messages, "claude-3-5-sonnet-20241022", "gpt-4o"
        )

        # Agent A's message should be output for A, input for B
        assert cost_breakdown["breakdown"]["model_a_output"] > 0
        assert cost_breakdown["breakdown"]["model_b_input"] > 0

        # Agent B's message should be output for B, input for A
        assert cost_breakdown["breakdown"]["model_b_output"] > 0
        assert cost_breakdown["breakdown"]["model_a_input"] > 0

    def test_estimate_conversation_cost_empty_messages(self, cost_estimator):
        """Test conversation cost with empty message list."""
        cost_breakdown = cost_estimator.estimate_conversation_cost(
            [], "claude-3-5-sonnet-20241022", "gpt-4o"
        )

        assert cost_breakdown["total"] == 0.0
        assert cost_breakdown["model_a_total"] == 0.0
        assert cost_breakdown["model_b_total"] == 0.0

        for key, value in cost_breakdown["breakdown"].items():
            assert value == 0.0

    def test_estimate_conversation_cost_local_models(self, cost_estimator):
        """Test conversation cost with local models."""
        message = Mock(spec=Message)
        message.content = "Test message"
        message.role = "user"
        message.agent_id = "agent_a"

        messages = [message]

        cost_breakdown = cost_estimator.estimate_conversation_cost(
            messages, "local", "local"
        )

        # Check if local model has zero pricing
        input_price, output_price = cost_estimator.get_model_pricing("local")
        if input_price == 0 and output_price == 0:
            assert cost_breakdown["total"] == 0.0
            assert cost_breakdown["model_a_total"] == 0.0
            assert cost_breakdown["model_b_total"] == 0.0
        else:
            # Fallback pricing is used
            assert cost_breakdown["total"] > 0
            assert cost_breakdown["model_a_total"] > 0
            assert cost_breakdown["model_b_total"] > 0

    def test_format_cost_small_amounts(self, cost_estimator):
        """Test cost formatting for small amounts."""
        # Less than $0.01
        assert cost_estimator.format_cost(0.0001) == "$0.0001"
        assert cost_estimator.format_cost(0.0056) == "$0.0056"
        assert cost_estimator.format_cost(0.009) == "$0.0090"

    def test_format_cost_medium_amounts(self, cost_estimator):
        """Test cost formatting for medium amounts."""
        # Between $0.01 and $1.00
        assert cost_estimator.format_cost(0.01) == "$0.010"
        assert cost_estimator.format_cost(0.123) == "$0.123"
        assert cost_estimator.format_cost(0.999) == "$0.999"

    def test_format_cost_large_amounts(self, cost_estimator):
        """Test cost formatting for large amounts."""
        # $1.00 and above
        assert cost_estimator.format_cost(1.0) == "$1.00"
        assert cost_estimator.format_cost(1.234) == "$1.23"
        assert cost_estimator.format_cost(12.3456) == "$12.35"
        assert cost_estimator.format_cost(123.456) == "$123.46"

    def test_format_cost_zero(self, cost_estimator):
        """Test cost formatting for zero cost."""
        assert cost_estimator.format_cost(0.0) == "$0.0000"

    def test_cost_calculation_accuracy(self, cost_estimator):
        """Test that cost calculations are accurate."""
        # Create a message with known content
        message = Mock(spec=Message)
        message.content = "x" * 350  # 350 chars = 100 tokens at 3.5 chars/token
        message.role = "user"
        message.agent_id = "agent_a"

        # Test with claude-3-5-sonnet (input: $3.00 per 1M tokens)
        cost = cost_estimator.estimate_message_cost(
            message, "claude-3-5-sonnet-20241022", is_input=True
        )

        expected_cost = (100 / 1_000_000) * 3.00  # 100 tokens * $3.00/1M tokens
        assert abs(cost - expected_cost) < 1e-10  # Allow for floating point precision

    def test_conversation_cost_scaling(self, cost_estimator):
        """Test that conversation costs scale properly with message count."""
        # Create identical messages
        message_template = Mock(spec=Message)
        message_template.content = "Test message"
        message_template.role = "user"
        message_template.agent_id = "agent_a"

        # Test with 1 message
        messages_1 = [message_template]
        cost_1 = cost_estimator.estimate_conversation_cost(
            messages_1, "claude-3-5-sonnet-20241022", "gpt-4o"
        )

        # Test with 2 identical messages
        messages_2 = [message_template, message_template]
        cost_2 = cost_estimator.estimate_conversation_cost(
            messages_2, "claude-3-5-sonnet-20241022", "gpt-4o"
        )

        # Cost should scale (though not linearly due to input/output differences)
        assert cost_2["total"] > cost_1["total"]

    def test_different_models_different_costs(self, cost_estimator):
        """Test that different models produce different costs."""
        message = Mock(spec=Message)
        message.content = "Test message for cost comparison"
        message.role = "user"
        message.agent_id = "agent_a"

        messages = [message]

        # Compare expensive model (claude-3-opus) vs cheaper model (claude-3-5-haiku)
        cost_expensive = cost_estimator.estimate_conversation_cost(
            messages, "claude-3-opus-20240229", "claude-3-opus-20240229"
        )

        cost_cheap = cost_estimator.estimate_conversation_cost(
            messages, "claude-3-5-haiku-20241022", "claude-3-5-haiku-20241022"
        )

        assert cost_expensive["total"] > cost_cheap["total"]

    def test_input_output_cost_difference(self, cost_estimator, sample_message):
        """Test that input and output costs are different for most models."""
        model = "claude-3-5-sonnet-20241022"

        input_cost = cost_estimator.estimate_message_cost(
            sample_message, model, is_input=True
        )
        output_cost = cost_estimator.estimate_message_cost(
            sample_message, model, is_input=False
        )

        # For most models, output is more expensive than input
        assert output_cost > input_cost

    def test_comprehensive_model_coverage(self, cost_estimator):
        """Test that all major model families are covered."""
        from pidgin.config.models import MODELS
        
        # Test that we can get pricing for various model families
        model_families = {
            "claude": False,
            "gpt": False,
            "o1": False,
            "gemini": False,
            "grok": False,
            "local": False
        }
        
        for model_id in MODELS.keys():
            # Try to get pricing - should not raise exceptions
            input_cost, output_cost = cost_estimator.get_model_pricing(model_id)
            
            # Mark which families we've seen
            for family in model_families:
                if family in model_id:
                    model_families[family] = True
        
        # Check that all major families are covered
        assert model_families["claude"], "No Claude models found"
        assert model_families["gpt"], "No GPT models found"
        assert model_families["gemini"], "No Gemini models found"
        assert model_families["grok"], "No Grok models found"
        assert model_families["local"], "No local models found"
