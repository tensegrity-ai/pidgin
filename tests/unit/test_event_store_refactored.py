"""Tests for refactored EventStore."""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
from datetime import datetime

from pidgin.database.event_store_refactored import RefactoredEventStore
from pidgin.database.async_duckdb import AsyncDuckDB
from pidgin.core.events import ConversationStartEvent, TurnStartEvent
from tests.builders import make_conversation_start_event, make_turn_start_event


class TestRefactoredEventStore:
    """Test the refactored EventStore implementation."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database connection."""
        db = AsyncMock(spec=AsyncDuckDB)
        db.execute = AsyncMock()
        db.fetchone = AsyncMock()
        db.fetchall = AsyncMock()
        return db
    
    @pytest.fixture
    def store(self, mock_db):
        """Create a RefactoredEventStore instance."""
        return RefactoredEventStore(mock_db)
    
    @pytest.mark.asyncio
    async def test_save_event_delegates_to_repository(self, store):
        """Test that save_event delegates to EventRepository."""
        event = make_conversation_start_event()
        
        # Mock the repository method
        store.events.save_event = AsyncMock()
        
        await store.save_event(event, "exp-123", "conv-456")
        
        # Verify delegation
        store.events.save_event.assert_called_once_with(
            event, "exp-123", "conv-456"
        )
    
    @pytest.mark.asyncio
    async def test_create_experiment_delegates_to_repository(self, store):
        """Test that create_experiment delegates to ExperimentRepository."""
        config = {"max_conversations": 10}
        
        # Mock the repository method
        store.experiments.create_experiment = AsyncMock()
        
        await store.create_experiment("exp-123", config)
        
        # Verify delegation
        store.experiments.create_experiment.assert_called_once_with(
            "exp-123", config
        )
    
    @pytest.mark.asyncio
    async def test_save_message_delegates_to_repository(self, store):
        """Test that save_message delegates to MessageRepository."""
        # Mock the repository method
        store.messages.save_message = AsyncMock()
        
        await store.save_message(
            conversation_id="conv-123",
            turn_number=5,
            agent_id="agent_a",
            role="user",
            content="Hello!",
            tokens_used=10
        )
        
        # Verify delegation
        store.messages.save_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_log_turn_metrics_delegates_to_repository(self, store):
        """Test that log_turn_metrics delegates to MetricsRepository."""
        metrics = {"vocabulary_overlap": 0.75}
        
        # Mock the repository method
        store.metrics.log_turn_metrics = AsyncMock()
        
        await store.log_turn_metrics("conv-123", 5, metrics)
        
        # Verify delegation
        store.metrics.log_turn_metrics.assert_called_once_with(
            "conv-123", 5, metrics
        )
    
    @pytest.mark.asyncio
    async def test_get_conversation_agent_configs(self, store):
        """Test backward compatibility method."""
        mock_conv = {
            "conversation_id": "conv-123",
            "config": {
                "agent_a": {"model": "gpt-4"},
                "agent_b": {"model": "claude-3"},
                "max_turns": 10
            }
        }
        
        store.conversations.get_conversation = AsyncMock(return_value=mock_conv)
        
        configs = await store.get_conversation_agent_configs("conv-123")
        
        assert configs is not None
        assert configs["agent_a"]["model"] == "gpt-4"
        assert configs["agent_b"]["model"] == "claude-3"
    
    @pytest.mark.asyncio
    async def test_get_experiment_summary(self, store):
        """Test experiment summary aggregation."""
        mock_exp = {
            "experiment_id": "exp-123",
            "status": "completed",
            "started_at": datetime.now(),
            "ended_at": datetime.now()
        }
        
        mock_convs = [
            {"conversation_id": "c1", "status": "completed"},
            {"conversation_id": "c2", "status": "completed"},
            {"conversation_id": "c3", "status": "failed"}
        ]
        
        mock_metrics = {
            "avg_vocabulary_overlap": 0.72,
            "avg_message_length": 45.5
        }
        
        store.experiments.get_experiment = AsyncMock(return_value=mock_exp)
        store.conversations.list_conversations_by_experiment = AsyncMock(
            return_value=mock_convs
        )
        store.metrics.get_experiment_metrics = AsyncMock(return_value=mock_metrics)
        
        summary = await store.get_experiment_summary("exp-123")
        
        assert summary["total_conversations"] == 3
        assert summary["completed"] == 2
        assert summary["failed"] == 1
        assert summary["running"] == 0
        assert summary["avg_vocabulary_overlap"] == 0.72
    
    @pytest.mark.asyncio
    async def test_delete_experiment_cascades(self, store):
        """Test that deleting experiment deletes all related data."""
        mock_convs = [
            {"conversation_id": "conv-1"},
            {"conversation_id": "conv-2"}
        ]
        
        store.conversations.list_conversations_by_experiment = AsyncMock(
            return_value=mock_convs
        )
        store.delete_conversation = AsyncMock()
        store.experiments.delete_experiment = AsyncMock()
        
        await store.delete_experiment("exp-123")
        
        # Should delete each conversation
        assert store.delete_conversation.call_count == 2
        store.delete_conversation.assert_any_call("conv-1")
        store.delete_conversation.assert_any_call("conv-2")
        
        # Should delete experiment
        store.experiments.delete_experiment.assert_called_once_with("exp-123")