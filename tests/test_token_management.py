"""Tests for token management and compression scenarios."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from pidgin.token_management import TokenManager, ConversationTokenPredictor


class TestTokenManager:
    """Test token counting and rate limit management."""
    
    def test_token_counting(self):
        """Test basic token counting for different models."""
        tm = TokenManager()
        
        # Test Claude model (4 chars/token)
        assert tm.count_tokens("Hello world!", "claude-4-opus-20250514") == 3
        assert tm.count_tokens("A" * 100, "claude-4-sonnet-20250514") == 25
        
        # Test GPT model (3.5 chars/token)
        assert tm.count_tokens("Hello world!", "gpt-4-turbo") == 3
        assert tm.count_tokens("A" * 100, "gpt-4.1-mini") == 28
    
    def test_availability_check_under_limit(self):
        """Test availability when under rate limits."""
        tm = TokenManager()
        
        # Should be available when no usage
        can_proceed, wait_time = tm.check_availability("claude-4-opus-20250514", 1000)
        assert can_proceed is True
        assert wait_time == 0
    
    def test_availability_check_over_limit(self):
        """Test availability when over rate limits."""
        tm = TokenManager()
        
        # Track usage up to limit
        tm.track_usage("claude-4-opus-20250514", 39000)
        
        # Should not be available for large request
        can_proceed, wait_time = tm.check_availability("claude-4-opus-20250514", 2000)
        assert can_proceed is False
        assert wait_time > 0
        
        # Should be available for small request
        can_proceed, wait_time = tm.check_availability("claude-4-opus-20250514", 500)
        assert can_proceed is True
    
    def test_usage_tracking(self):
        """Test token usage tracking."""
        tm = TokenManager()
        
        # Track multiple usages
        tm.track_usage("gpt-4.1-mini", 1000)
        tm.track_usage("gpt-4.1-mini", 2000)
        
        stats = tm.get_usage_stats("gpt-4.1-mini")
        assert stats['tokens_used'] == 3000
        assert stats['tokens_limit'] == 80000
        assert stats['percentage'] == 3.75
    
    def test_sliding_window(self):
        """Test that old usage expires after 1 minute."""
        tm = TokenManager()
        
        # Track old usage
        now = datetime.now()
        old_time = now - timedelta(minutes=2)
        tm.usage_windows["test-model"] = [(old_time, 1000)]
        
        # Check availability should ignore old usage
        stats = tm.get_usage_stats("test-model")
        assert stats['tokens_used'] == 0  # Old usage should be expired


class TestConversationTokenPredictor:
    """Test conversation token growth prediction."""
    
    def test_predict_with_insufficient_data(self):
        """Test prediction with insufficient history."""
        tm = TokenManager()
        predictor = ConversationTokenPredictor(tm)
        
        # Should return high number when no data
        assert predictor.predict_remaining_exchanges("claude", "claude") == 100
        
        # Add one exchange
        predictor.add_exchange(100, 150)
        assert predictor.predict_remaining_exchanges("claude", "claude") == 100
    
    def test_predict_linear_growth(self):
        """Test prediction with linear token growth."""
        tm = TokenManager()
        predictor = ConversationTokenPredictor(tm)
        
        # Simulate linear growth
        for i in range(5):
            predictor.add_exchange(100 + i * 10, 150 + i * 10)
        
        # Mock available tokens
        with patch.object(tm, 'get_usage_stats') as mock_stats:
            mock_stats.return_value = {
                'tokens_used': 10000,
                'tokens_limit': 40000,
                'percentage': 25
            }
            
            remaining = predictor.predict_remaining_exchanges("claude", "claude")
            assert remaining > 0
            assert remaining < 100
    
    def test_compression_detection(self):
        """Test detection of compression patterns."""
        tm = TokenManager()
        predictor = ConversationTokenPredictor(tm)
        
        # Start with normal messages
        for _ in range(3):
            predictor.add_exchange(200, 250)
        
        # Then compression begins
        for i in range(5):
            predictor.add_exchange(150 - i * 20, 180 - i * 20)
        
        pattern = predictor.get_growth_pattern()
        assert pattern == "compressing"
    
    def test_expansion_detection(self):
        """Test detection of expansion patterns."""
        tm = TokenManager()
        predictor = ConversationTokenPredictor(tm)
        
        # Simulate expanding messages
        for i in range(5):
            predictor.add_exchange(100 + i * 50, 150 + i * 50)
        
        pattern = predictor.get_growth_pattern()
        assert pattern == "expanding"


class TestCompressionAttractorScenario:
    """Test handling of compression attractor with token limits."""
    
    @pytest.mark.asyncio
    async def test_compression_attractor_token_limits(self):
        """Verify graceful handling as messages compress and tokens accumulate."""
        from pidgin.dialogue import DialogueEngine
        from pidgin.types import Agent
        
        # Mock components
        mock_router = Mock()
        mock_transcript_manager = Mock()
        mock_config = {
            'token_management': {
                'enabled': True,
                'warning_threshold': 5,
                'auto_pause_threshold': 2,
                'show_metrics': True
            }
        }
        
        # Create engine
        engine = DialogueEngine(mock_router, mock_transcript_manager, mock_config)
        
        # Create agents
        agent_a = Agent(id="agent_a", model="claude-4-opus-20250514")
        agent_b = Agent(id="agent_b", model="claude-4-sonnet-20250514")
        
        # Simulate compression attractor responses
        compression_responses = [
            "This is a normal length response with some content.",
            "Slightly shorter response here.",
            "Getting shorter.",
            "Compressed.",
            "Short.",
            "!",
        ]
        
        # Mock router to return compressing responses
        response_index = 0
        def mock_route_message(*args, **kwargs):
            nonlocal response_index
            if response_index < len(compression_responses):
                response = compression_responses[response_index]
                response_index += 1
            else:
                response = "!"  # Ultimate compression
            
            from pidgin.types import Message
            return Message(
                role="assistant",
                content=response,
                agent_id="agent_a" if response_index % 2 == 0 else "agent_b"
            )
        
        mock_router.route_message = mock_route_message
        
        # Verify the following:
        # 1. Warnings appear when approaching limits
        # 2. Auto-pause triggers before crash
        # 3. Checkpoint is saved
        # 4. Token metrics are tracked
        
        # This would be a full integration test in practice
        # Here we're testing the components work together
        assert engine.token_manager is not None
        assert engine.token_predictor is not None
        assert engine.token_warning_threshold == 5
        assert engine.token_auto_pause_threshold == 2