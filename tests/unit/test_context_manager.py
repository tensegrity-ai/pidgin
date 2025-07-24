"""Test provider context window management."""


import pytest

from pidgin.providers.context_manager import ProviderContextManager
from tests.builders import make_message


class TestProviderContextManager:
    """Test suite for ProviderContextManager."""

    @pytest.fixture
    def manager(self):
        """Create a context manager instance."""
        return ProviderContextManager()

    @pytest.fixture
    def short_messages(self):
        """Create a list of short messages."""
        return [
            make_message("System prompt", role="system"),
            make_message("Hello", role="user"),
            make_message("Hi there!", role="assistant"),
            make_message("How are you?", role="user"),
            make_message("I'm doing well!", role="assistant"),
        ]

    @pytest.fixture
    def long_messages(self):
        """Create messages that exceed context limits."""
        # Create very long content to exceed token limits
        long_content = "x" * 10000  # ~2857 tokens
        messages = [
            make_message("System", role="system"),
        ]
        # Add 60 long messages (~171,420 tokens total) to exceed Anthropic's 160k limit
        for i in range(60):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append(make_message(long_content, role=role))
        return messages

    def test_chars_per_token_constant(self, manager):
        """Test that token estimation constant is set correctly."""
        assert manager.CHARS_PER_TOKEN == 3.5

    def test_context_limits_defined(self, manager):
        """Test that context limits are defined for providers."""
        assert "anthropic" in manager.CONTEXT_LIMITS
        assert "openai" in manager.CONTEXT_LIMITS
        assert "google" in manager.CONTEXT_LIMITS
        assert "xai" in manager.CONTEXT_LIMITS
        assert "local" in manager.CONTEXT_LIMITS

        # Verify limits are reasonable
        assert manager.CONTEXT_LIMITS["anthropic"] == 160000
        assert manager.CONTEXT_LIMITS["openai"] == 100000
        assert manager.CONTEXT_LIMITS["google"] == 800000
        assert manager.CONTEXT_LIMITS["xai"] == 100000
        assert manager.CONTEXT_LIMITS["local"] == 4000

    def test_model_specific_limits(self, manager):
        """Test model-specific context limits."""
        assert "qwen2.5:3b" in manager.MODEL_LIMITS
        assert manager.MODEL_LIMITS["qwen2.5:3b"] == 32768
        assert manager.MODEL_LIMITS["phi3"] == 4096
        assert manager.MODEL_LIMITS["mistral"] == 8192
        assert manager.MODEL_LIMITS["llama3.2"] == 131072

    def test_prepare_context_under_limit(self, manager, short_messages):
        """Test that messages under limit are returned as-is."""
        result = manager.prepare_context(short_messages, "anthropic")
        assert result == short_messages
        assert len(result) == len(short_messages)

    def test_prepare_context_over_limit_anthropic(self, manager, long_messages):
        """Test context truncation for Anthropic."""
        result = manager.prepare_context(long_messages, "anthropic", allow_truncation=True)

        # Should have truncated messages
        assert len(result) < len(long_messages)
        assert len(result) == 56  # Expected result based on limit
        # Should keep system message
        assert result[0].role == "system"
        # Verify messages were truncated from the beginning
        assert result[-1] == long_messages[-1]  # Last message preserved

    def test_prepare_context_local_provider(self, manager, long_messages):
        """Test context truncation for local models with small limits."""
        result = manager.prepare_context(long_messages, "local", allow_truncation=True)

        # Local has 4000 token limit, should truncate heavily
        assert len(result) <= 3  # System + maybe 1-2 messages
        assert result[0].role == "system"
        # Verify it kept the most recent messages
        if len(result) > 1:
            assert result[-1] == long_messages[-1]

    def test_prepare_context_model_specific_limit(self, manager):
        """Test using model-specific limit instead of provider limit."""
        # Create messages that fit in phi3 (4k) but not in the calculated limit
        messages = []
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append(make_message("x" * 1000, role=role))  # ~286 tokens each

        # Should use phi3's 4096 token limit
        result = manager.prepare_context(messages, "local", "phi3")

        # Verify it used the model-specific limit
        total_chars = sum(len(m.content) + 20 for m in result)
        estimated_tokens = int(total_chars / manager.CHARS_PER_TOKEN)
        assert estimated_tokens < 4096

    def test_prepare_context_unknown_provider(self, manager, long_messages):
        """Test fallback for unknown provider."""
        result = manager.prepare_context(long_messages, "unknown_provider", allow_truncation=True)

        # Should use default 8000 token limit
        assert len(result) < len(long_messages)
        total_chars = sum(len(m.content) + 20 for m in result)
        estimated_tokens = int(total_chars / manager.CHARS_PER_TOKEN)
        assert estimated_tokens < 8000

    def test_prepare_context_preserves_system_messages(self, manager):
        """Test that system messages are always preserved."""
        messages = [
            make_message("System 1", role="system"),
            make_message("System 2", role="system"),
        ]
        # Add many large messages
        for i in range(100):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append(make_message("x" * 5000, role=role))

        result = manager.prepare_context(messages, "local", allow_truncation=True)  # Small limit

        # Both system messages should be preserved
        system_msgs = [m for m in result if m.role == "system"]
        assert len(system_msgs) == 2
        assert system_msgs[0].content == "System 1"
        assert system_msgs[1].content == "System 2"

    def test_prepare_context_binary_search_efficiency(self, manager):
        """Test that binary search finds optimal message count."""
        # Create messages with known sizes
        messages = [make_message("System", role="system")]

        # Add 800 messages of 500 chars each (~143 tokens each = ~114,400 tokens total)
        for i in range(800):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append(make_message("x" * 500, role=role))

        # Use openai with 100k limit
        result = manager.prepare_context(messages, "openai", allow_truncation=True)

        # Should keep less than all messages
        assert len(result) < len(messages)

        # Verify we're close to but under the limit
        total_chars = sum(len(m.content) + 20 for m in result)
        estimated_tokens = int(total_chars / manager.CHARS_PER_TOKEN)
        assert estimated_tokens < 100000
        assert estimated_tokens > 80000  # Should be reasonably close to limit

    def test_prepare_context_no_truncation_by_default(self, manager, long_messages):
        """Test that truncation is disabled by default."""
        # Without allow_truncation, should return all messages
        result = manager.prepare_context(long_messages, "anthropic")
        
        # Should return all messages unchanged
        assert len(result) == len(long_messages)
        assert result == long_messages
    
    def test_prepare_context_single_message_over_limit(self, manager):
        """Test handling when even a single message exceeds limit."""
        # Create a message larger than local limit (4000 tokens)
        huge_message = make_message("x" * 20000, role="user")  # ~5714 tokens
        messages = [make_message("System", role="system"), huge_message]

        # Without truncation, should return all messages
        result = manager.prepare_context(messages, "local")
        assert len(result) == 2
        assert result == messages
        
        # With truncation enabled
        result_truncated = manager.prepare_context(messages, "local", allow_truncation=True)
        # Should at minimum keep system message 
        assert len(result_truncated) >= 1
        assert result_truncated[0].role == "system"

    def test_prepare_context_empty_messages(self, manager):
        """Test handling empty message list."""
        result = manager.prepare_context([], "anthropic")
        assert result == []

    def test_prepare_context_only_system_messages(self, manager):
        """Test handling when only system messages exist."""
        messages = [
            make_message("System 1", role="system"),
            make_message("System 2", role="system"),
        ]

        result = manager.prepare_context(messages, "anthropic")
        assert result == messages

    def test_token_estimation_accuracy(self, manager):
        """Test token estimation calculation."""
        # Test with known content
        messages = [
            make_message("Hello world"),  # 11 chars + 20 = 31 chars = ~8.8 tokens
            make_message("Test message"),  # 12 chars + 20 = 32 chars = ~9.1 tokens
        ]

        total_chars = sum(len(m.content) + 20 for m in messages)
        assert total_chars == 63

        estimated_tokens = int(total_chars / manager.CHARS_PER_TOKEN)
        assert estimated_tokens == 18  # 63 / 3.5 = 18
