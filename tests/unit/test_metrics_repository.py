"""Tests for MetricsRepository."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from pidgin.database.repositories.metrics_repository import MetricsRepository
from pidgin.database.async_duckdb import AsyncDuckDB


class TestMetricsRepository:
    """Test MetricsRepository functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database connection."""
        db = AsyncMock(spec=AsyncDuckDB)
        db.execute = AsyncMock()
        db.fetchone = AsyncMock()
        db.fetchall = AsyncMock()
        return db
    
    @pytest.fixture
    def repository(self, mock_db):
        """Create a MetricsRepository instance."""
        return MetricsRepository(mock_db)
    
    @pytest.mark.asyncio
    async def test_log_turn_metrics(self, repository, mock_db):
        """Test logging turn-level metrics."""
        metrics = {
            "vocabulary_overlap": 0.75,
            "message_length_variance": 0.2,
            "turn_taking_balance": 0.95,
            "engagement_score": 0.8
        }
        
        await repository.log_turn_metrics(
            conversation_id="conv-123",
            turn_number=5,
            metrics=metrics
        )
        
        # Verify INSERT was executed
        mock_db.execute.assert_called()
        call_args = mock_db.execute.call_args[0][0]
        assert "INSERT INTO turn_metrics" in call_args
        assert "conversation_id" in call_args
        assert "turn_number" in call_args
    
    @pytest.mark.asyncio
    async def test_log_message_metrics(self, repository, mock_db):
        """Test logging message-level metrics."""
        await repository.log_message_metrics(
            conversation_id="conv-123",
            turn_number=3,
            agent_id="agent_a",
            message_length=150,
            vocabulary_size=50,
            punctuation_ratio=0.05,
            sentiment_score=0.7
        )
        
        # Verify INSERT
        mock_db.execute.assert_called()
        call_args = mock_db.execute.call_args[0][0]
        assert "INSERT INTO message_metrics" in call_args
        assert "agent_id" in call_args
        assert "sentiment_score" in call_args
    
    @pytest.mark.asyncio
    async def test_log_word_frequencies(self, repository, mock_db):
        """Test logging word frequency data."""
        word_freqs = {
            "hello": 3,
            "world": 2,
            "test": 5,
            "conversation": 1
        }
        
        await repository.log_word_frequencies(
            conversation_id="conv-123",
            turn_number=2,
            agent_id="agent_b",
            word_frequencies=word_freqs
        )
        
        # Should insert multiple rows
        assert mock_db.execute.call_count >= 1
        call_args = mock_db.execute.call_args[0][0]
        assert "INSERT INTO word_frequencies" in call_args
    
    @pytest.mark.asyncio
    async def test_get_turn_metrics(self, repository, mock_db):
        """Test retrieving metrics for a specific turn."""
        mock_metrics = {
            "vocabulary_overlap": 0.65,
            "message_length_variance": 0.15,
            "turn_taking_balance": 0.9,
            "timestamp": datetime.now()
        }
        mock_db.fetchone.return_value = mock_metrics
        
        metrics = await repository.get_turn_metrics("conv-123", 5)
        
        assert metrics is not None
        assert metrics["vocabulary_overlap"] == 0.65
        assert metrics["turn_taking_balance"] == 0.9
    
    @pytest.mark.asyncio
    async def test_get_conversation_metrics(self, repository, mock_db):
        """Test retrieving all metrics for a conversation."""
        mock_turns = [
            {"turn_number": 1, "vocabulary_overlap": 0.5},
            {"turn_number": 2, "vocabulary_overlap": 0.6},
            {"turn_number": 3, "vocabulary_overlap": 0.7}
        ]
        mock_db.fetchall.return_value = mock_turns
        
        metrics = await repository.get_conversation_metrics("conv-123")
        
        assert len(metrics) == 3
        assert metrics[0]["turn_number"] == 1
        assert metrics[2]["vocabulary_overlap"] == 0.7
    
    @pytest.mark.asyncio
    async def test_get_experiment_metrics(self, repository, mock_db):
        """Test retrieving aggregated metrics for an experiment."""
        # Mock various metric queries
        mock_db.fetchone.side_effect = [
            {"avg_vocabulary_overlap": 0.72, "avg_engagement": 0.85},  # Turn metrics
            {"avg_message_length": 45.5, "avg_vocabulary_size": 32},  # Message metrics
            {"total_unique_words": 1500, "avg_words_per_turn": 25}    # Word stats
        ]
        
        metrics = await repository.get_experiment_metrics("exp-123")
        
        assert metrics["avg_vocabulary_overlap"] == 0.72
        assert metrics["avg_engagement"] == 0.85
        assert metrics["avg_message_length"] == 45.5
        assert metrics["total_unique_words"] == 1500
    
    @pytest.mark.asyncio
    async def test_get_agent_metrics(self, repository, mock_db):
        """Test retrieving metrics for a specific agent."""
        mock_metrics = {
            "total_messages": 50,
            "avg_message_length": 48.2,
            "total_words": 2410,
            "unique_words": 350,
            "avg_sentiment": 0.65
        }
        mock_db.fetchone.return_value = mock_metrics
        
        metrics = await repository.get_agent_metrics("conv-123", "agent_a")
        
        assert metrics["total_messages"] == 50
        assert metrics["avg_message_length"] == 48.2
        assert metrics["unique_words"] == 350
    
    @pytest.mark.asyncio
    async def test_get_vocabulary_overlap_series(self, repository, mock_db):
        """Test retrieving vocabulary overlap over time."""
        mock_series = [
            {"turn_number": 1, "vocabulary_overlap": 0.4},
            {"turn_number": 2, "vocabulary_overlap": 0.5},
            {"turn_number": 3, "vocabulary_overlap": 0.65},
            {"turn_number": 4, "vocabulary_overlap": 0.7}
        ]
        mock_db.fetchall.return_value = mock_series
        
        series = await repository.get_vocabulary_overlap_series("conv-123")
        
        assert len(series) == 4
        assert series[0]["vocabulary_overlap"] == 0.4
        assert series[3]["vocabulary_overlap"] == 0.7
        # Should show increasing overlap
        assert series[3]["vocabulary_overlap"] > series[0]["vocabulary_overlap"]
    
    @pytest.mark.asyncio
    async def test_calculate_convergence_metrics(self, repository, mock_db):
        """Test calculating convergence-related metrics."""
        # Mock data for convergence calculation
        mock_db.fetchall.side_effect = [
            # Vocabulary overlap series
            [{"turn_number": i, "vocabulary_overlap": 0.3 + i*0.1} for i in range(5)],
            # Message length variance series  
            [{"turn_number": i, "message_length_variance": 100 - i*10} for i in range(5)]
        ]
        
        convergence = await repository.calculate_convergence_metrics("conv-123")
        
        assert "vocabulary_convergence_rate" in convergence
        assert "message_length_convergence" in convergence
        assert "overall_convergence_score" in convergence
    
    @pytest.mark.asyncio
    async def test_get_top_words(self, repository, mock_db):
        """Test retrieving most frequent words."""
        mock_words = [
            {"word": "interesting", "total_frequency": 25},
            {"word": "understand", "total_frequency": 20},
            {"word": "think", "total_frequency": 18},
            {"word": "agree", "total_frequency": 15},
            {"word": "perhaps", "total_frequency": 12}
        ]
        mock_db.fetchall.return_value = mock_words
        
        top_words = await repository.get_top_words("conv-123", limit=5)
        
        assert len(top_words) == 5
        assert top_words[0]["word"] == "interesting"
        assert top_words[0]["total_frequency"] == 25
        # Should be ordered by frequency
        assert top_words[0]["total_frequency"] > top_words[4]["total_frequency"]
    
    @pytest.mark.asyncio
    async def test_delete_metrics(self, repository, mock_db):
        """Test deleting all metrics for a conversation."""
        await repository.delete_metrics("conv-123")
        
        # Should delete from multiple tables
        assert mock_db.execute.call_count >= 3
        
        # Check all metric tables were cleaned
        delete_calls = [call[0][0] for call in mock_db.execute.call_args_list]
        assert any("DELETE FROM turn_metrics" in call for call in delete_calls)
        assert any("DELETE FROM message_metrics" in call for call in delete_calls)
        assert any("DELETE FROM word_frequencies" in call for call in delete_calls)