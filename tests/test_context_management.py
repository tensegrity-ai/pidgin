"""Tests for context window management and limit handling."""

import pytest
from unittest.mock import Mock, patch

from pidgin.context_manager import ContextWindowManager


class TestContextWindowManager:
    """Test context window tracking and prediction."""

    def test_token_counting(self):
        """Test basic token counting for different models."""
        cm = ContextWindowManager()

        # Test approximate counting
        text = "Hello world! This is a test message."

        # All models should return reasonable approximations
        claude_tokens = cm.count_tokens(text, "claude-4-opus-20250514")
        gpt_tokens = cm.count_tokens(text, "gpt-4-turbo")

        assert claude_tokens > 0
        assert gpt_tokens > 0
        assert abs(claude_tokens - gpt_tokens) <= 2  # Should be similar

    def test_context_limits(self):
        """Test that context limits are defined for known models."""
        cm = ContextWindowManager()

        # Check some key models have limits
        assert cm.context_limits["claude-4-opus-20250514"] == 200000
        assert cm.context_limits["gpt-4-turbo"] == 128000
        assert cm.context_limits["o3-mini"] == 100000

    def test_conversation_size_calculation(self):
        """Test conversation size calculation."""
        cm = ContextWindowManager()

        messages = [
            {"content": "Hello world!"},
            {"content": "How are you today?"},
            {"content": "I'm doing great, thanks for asking!"},
        ]

        size = cm.get_conversation_size(messages, "claude-4-opus-20250514")
        assert size > 0
        assert size > len(messages) * 10  # Should account for overhead

    def test_remaining_capacity(self):
        """Test remaining capacity calculation."""
        cm = ContextWindowManager()

        messages = [{"content": "Short message"}]
        capacity = cm.get_remaining_capacity(messages, "claude-4-opus-20250514")

        assert capacity["used"] > 0
        assert capacity["limit"] == 198000  # 200k - 2k reserved
        assert capacity["total_limit"] == 200000
        assert capacity["remaining"] > 0
        assert capacity["percentage"] < 1  # Should be very small for one message

    def test_turns_prediction_insufficient_data(self):
        """Test turn prediction with insufficient history."""
        cm = ContextWindowManager()

        messages = [{"content": "Hi"}]
        turns = cm.predict_turns_remaining(messages, "claude-4-opus-20250514")

        assert turns == 999  # Should return high number

    def test_turns_prediction_with_history(self):
        """Test turn prediction with sufficient history."""
        from pidgin.types import Message

        cm = ContextWindowManager()

        # Create conversation with growing messages
        messages = []
        for i in range(10):
            content = "Message " + "x" * (i * 100)  # Growing messages
            # Alternate between agent_a and agent_b to create proper exchanges
            agent_id = "agent_a" if i % 2 == 0 else "agent_b"
            messages.append(
                Message(role="assistant", content=content, agent_id=agent_id)
            )

        turns = cm.predict_turns_remaining(messages, "claude-4-opus-20250514")

        assert turns > 0
        assert turns < 999  # Should have a real prediction

    def test_warning_threshold(self):
        """Test warning threshold checking."""
        cm = ContextWindowManager()

        # Mock a conversation near capacity
        with patch.object(cm, "get_remaining_capacity") as mock_capacity:
            mock_capacity.return_value = {"percentage": 85}

            assert cm.should_warn([], "test-model", warning_threshold=80) is True
            assert cm.should_warn([], "test-model", warning_threshold=90) is False

    def test_pause_threshold(self):
        """Test auto-pause threshold checking."""
        cm = ContextWindowManager()

        # Mock a conversation at capacity
        with patch.object(cm, "get_remaining_capacity") as mock_capacity:
            mock_capacity.return_value = {"percentage": 96}

            assert cm.should_pause([], "test-model", pause_threshold=95) is True
            assert cm.should_pause([], "test-model", pause_threshold=98) is False

    def test_usage_formatting(self):
        """Test usage formatting."""
        cm = ContextWindowManager()

        capacity = {"used": 50000, "limit": 200000, "percentage": 25.0}

        formatted = cm.format_usage(capacity)
        assert "50,000/200,000 tokens (25.0%)" == formatted

    def test_truncation_point(self):
        """Test finding truncation point."""
        cm = ContextWindowManager()

        # Create messages of varying sizes
        messages = [
            {"content": "A" * 100},  # 100 chars
            {"content": "B" * 200},  # 200 chars
            {"content": "C" * 300},  # 300 chars
            {"content": "D" * 400},  # 400 chars
        ]

        # Ask for truncation to 50% of a small limit
        with patch.object(cm, "context_limits", {"test-model": 1000}):
            truncation_point = cm.get_truncation_point(
                messages, "test-model", target_percentage=50
            )

            # Should keep some recent messages
            assert truncation_point >= 0
            assert truncation_point < len(messages)


class TestContextLimitHandling:
    """Test handling of conversations approaching context limits."""

    def test_context_limit_scenario(self):
        """Verify graceful handling as context approaches limit."""
        from pidgin.dialogue import DialogueEngine
        from pidgin.types import Agent

        # Mock components
        mock_router = Mock()
        mock_transcript_manager = Mock()
        mock_config = {
            "context_management": {
                "enabled": True,
                "warning_threshold": 80,
                "auto_pause_threshold": 95,
                "show_usage": True,
            }
        }

        # Create engine
        engine = DialogueEngine(mock_router, mock_transcript_manager, mock_config)

        # Verify context manager is initialized
        assert engine.context_manager is not None
        assert engine.context_warning_threshold == 80
        assert engine.context_auto_pause_threshold == 95
        # show_context_usage doesn't exist anymore in the refactored version

    def test_large_message_scenario(self):
        """Test handling of artificially large messages."""
        cm = ContextWindowManager()

        # Create conversation with progressively larger messages
        messages = []
        for i in range(5):
            # Each message is 10k chars (roughly 2.5k tokens)
            content = "Large message content " * 500 * (i + 1)
            messages.append({"content": content})

        capacity = cm.get_remaining_capacity(messages, "gpt-4-turbo")  # 128k limit

        # Should show significant usage
        assert capacity["percentage"] > 10

        # Should predict fewer turns remaining as messages grow
        turns = cm.predict_turns_remaining(messages, "gpt-4-turbo")
        assert turns < 100  # Should be constrained

    def test_different_model_limits(self):
        """Test that different models have different constraints."""
        cm = ContextWindowManager()

        # Same conversation size, different models
        large_messages = [{"content": "x" * 10000} for _ in range(10)]

        claude_capacity = cm.get_remaining_capacity(
            large_messages, "claude-4-opus-20250514"
        )
        gpt_capacity = cm.get_remaining_capacity(large_messages, "gpt-4-turbo")

        # Claude should have more remaining capacity (200k vs 128k)
        assert claude_capacity["remaining"] > gpt_capacity["remaining"]
        assert claude_capacity["percentage"] < gpt_capacity["percentage"]
