# tests/unit/test_token_utils.py
"""Test token utility functions."""

import pytest
from pidgin.providers.token_utils import (
    estimate_tokens, 
    estimate_messages_tokens,
    parse_usage_from_response
)
from pidgin.core.types import Message
from datetime import datetime


class TestEstimateTokens:
    """Test estimate_tokens function."""
    
    def test_empty_text(self):
        """Test with empty text."""
        assert estimate_tokens("") == 0
        assert estimate_tokens(None) == 0
    
    def test_simple_text(self):
        """Test with simple text."""
        # "Hello world" - 2 words, 11 chars
        # char estimate: 11/4 = 2.75
        # word estimate: 2 * 1.3 = 2.6
        # average: (2.75 + 2.6) / 2 = 2.675 ≈ 2
        result = estimate_tokens("Hello world")
        assert result == 2
    
    def test_longer_text(self):
        """Test with longer text."""
        text = "This is a longer piece of text with multiple words"
        # 10 words, 49 chars
        # char estimate: 49/4 = 12.25
        # word estimate: 10 * 1.3 = 13
        # average: (12.25 + 13) / 2 = 12.625 ≈ 12
        result = estimate_tokens(text)
        assert result == 12
    
    def test_model_specific_adjustments(self):
        """Test model-specific token adjustments."""
        text = "Test text for model adjustments"
        
        # Base estimation
        base = estimate_tokens(text)
        
        # GPT models should have 1.1x adjustment
        gpt_result = estimate_tokens(text, "gpt-4")
        assert gpt_result == int(base * 1.1)
        
        # Claude should have no adjustment
        claude_result = estimate_tokens(text, "claude-3-sonnet")
        assert claude_result == base
        
        # Gemini should have 1.05x adjustment  
        gemini_result = estimate_tokens(text, "gemini-pro")
        assert gemini_result == int(base * 1.05)


class TestEstimateMessagesTokens:
    """Test estimate_messages_tokens function."""
    
    def test_empty_messages(self):
        """Test with empty message list."""
        assert estimate_messages_tokens([]) == 3  # Just conversation overhead
    
    def test_single_message(self):
        """Test with single message."""
        messages = [
            Message(
                role="user",
                content="Hello",
                agent_id="test",
                timestamp=datetime.now()
            )
        ]
        # "Hello" = ~1 token + 4 overhead + 3 conversation = 8
        result = estimate_messages_tokens(messages)
        assert result == 8
    
    def test_multiple_messages(self):
        """Test with multiple messages."""
        messages = [
            Message(
                role="user", 
                content="Hello there",
                agent_id="agent_a",
                timestamp=datetime.now()
            ),
            Message(
                role="assistant",
                content="Hi! How can I help?",
                agent_id="agent_b", 
                timestamp=datetime.now()
            )
        ]
        # Message 1: "Hello there" ≈ 2 tokens + 4 overhead = 6
        # Message 2: "Hi! How can I help?" ≈ 5 tokens + 4 overhead = 9
        # Total: 6 + 9 + 3 conversation overhead = 18
        result = estimate_messages_tokens(messages)
        assert 15 <= result <= 20  # Allow some variance in estimation


class TestParseUsageFromResponse:
    """Test parse_usage_from_response function."""
    
    def test_openai_format(self):
        """Test parsing OpenAI response format."""
        # Mock OpenAI response
        class MockUsage:
            prompt_tokens = 10
            completion_tokens = 20
            total_tokens = 30
            
        class MockResponse:
            usage = MockUsage()
        
        result = parse_usage_from_response(MockResponse(), "openai")
        assert result == {
            'prompt_tokens': 10,
            'completion_tokens': 20,
            'total_tokens': 30
        }
    
    def test_anthropic_format(self):
        """Test parsing Anthropic response format."""
        # Mock Anthropic response
        class MockUsage:
            input_tokens = 15
            output_tokens = 25
            
        class MockResponse:
            usage = MockUsage()
        
        result = parse_usage_from_response(MockResponse(), "anthropic")
        assert result == {
            'prompt_tokens': 15,
            'completion_tokens': 25,
            'total_tokens': 40
        }
    
    def test_google_format(self):
        """Test parsing Google response format."""
        # Mock Google response
        class MockResponse:
            metadata = {
                'input_token_count': 12,
                'output_token_count': 18
            }
        
        result = parse_usage_from_response(MockResponse(), "google")
        assert result == {
            'prompt_tokens': 12,
            'completion_tokens': 18,
            'total_tokens': 30
        }
    
    def test_missing_usage_data(self):
        """Test with missing usage data."""
        class MockResponse:
            pass
        
        result = parse_usage_from_response(MockResponse(), "openai")
        assert result == {
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0
        }
    
    def test_unknown_provider(self):
        """Test with unknown provider."""
        result = parse_usage_from_response({}, "unknown")
        assert result == {
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0
        }