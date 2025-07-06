"""Tests for ConversationRepository."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
import json

from pidgin.database.repositories.conversation_repository import ConversationRepository
from pidgin.database.async_duckdb import AsyncDuckDB


class TestConversationRepository:
    """Test ConversationRepository functionality."""
    
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
        """Create a ConversationRepository instance."""
        return ConversationRepository(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_conversation(self, repository, mock_db):
        """Test creating a new conversation."""
        await repository.create_conversation(
            experiment_id="exp-123",
            conversation_id="conv-456",
            config={
                "agent_a": {"model": "gpt-4", "temperature": 0.7},
                "agent_b": {"model": "claude-3", "temperature": 0.7},
                "max_turns": 10
            }
        )
        
        # Verify INSERT was executed
        mock_db.execute.assert_called()
        call_args = mock_db.execute.call_args[0][0]
        assert "INSERT INTO conversations" in call_args
        assert "experiment_id" in call_args
        assert "conversation_id" in call_args
    
    @pytest.mark.asyncio
    async def test_get_conversation(self, repository, mock_db):
        """Test retrieving a conversation."""
        mock_conv = {
            "conversation_id": "conv-123",
            "experiment_id": "exp-456",
            "status": "running",
            "config": json.dumps({"max_turns": 10}),
            "started_at": datetime.now(),
            "total_messages": 20,
            "total_turns": 10
        }
        mock_db.fetchone.return_value = mock_conv
        
        conv = await repository.get_conversation("conv-123")
        
        assert conv is not None
        assert conv["conversation_id"] == "conv-123"
        assert conv["status"] == "running"
        # Config should be parsed from JSON
        assert isinstance(conv["config"], dict)
        assert conv["config"]["max_turns"] == 10
    
    @pytest.mark.asyncio
    async def test_update_conversation_status(self, repository, mock_db):
        """Test updating conversation status."""
        # Mock that conversation exists
        mock_db.fetchone.return_value = {"count": 1}
        
        await repository.update_conversation_status(
            conversation_id="conv-123",
            status="completed",
            end_reason="max_turns"
        )
        
        # Check UPDATE was called
        all_calls = [call[0][0] for call in mock_db.execute.call_args_list]
        assert any("UPDATE conversations" in call and "status = ?" in call for call in all_calls)
    
    @pytest.mark.asyncio
    async def test_update_conversation_status_with_error(self, repository, mock_db):
        """Test updating conversation status with error."""
        mock_db.fetchone.return_value = {"count": 1}
        
        await repository.update_conversation_status(
            conversation_id="conv-123",
            status="failed",
            end_reason="api_error",
            error_message="Rate limit exceeded"
        )
        
        # Check error message was included
        all_calls = [call[0][0] for call in mock_db.execute.call_args_list]
        assert any("error_message = ?" in call for call in all_calls)
    
    @pytest.mark.asyncio
    async def test_get_conversation_history(self, repository, mock_db):
        """Test retrieving conversation message history."""
        mock_messages = [
            {
                "turn_number": 1,
                "agent_id": "agent_a",
                "role": "user",
                "content": "Hello!",
                "timestamp": datetime.now()
            },
            {
                "turn_number": 1,
                "agent_id": "agent_b", 
                "role": "assistant",
                "content": "Hi there!",
                "timestamp": datetime.now()
            }
        ]
        mock_db.fetchall.return_value = mock_messages
        
        history = await repository.get_conversation_history("conv-123")
        
        assert len(history) == 2
        assert history[0]["agent_id"] == "agent_a"
        assert history[1]["agent_id"] == "agent_b"
        
        # Check query
        call_args = mock_db.execute.call_args[0][0]
        assert "FROM messages" in call_args
        assert "WHERE conversation_id = ?" in call_args
        assert "ORDER BY turn_number, timestamp" in call_args
    
    @pytest.mark.asyncio
    async def test_log_agent_name(self, repository, mock_db):
        """Test logging agent chosen name."""
        await repository.log_agent_name(
            conversation_id="conv-123",
            agent_id="agent_a",
            chosen_name="Alice",
            turn_number=0
        )
        
        # Check INSERT was called
        call_args = mock_db.execute.call_args[0][0]
        assert "INSERT INTO agent_names" in call_args
        assert "conversation_id" in call_args
        assert "chosen_name" in call_args
    
    @pytest.mark.asyncio
    async def test_get_agent_names(self, repository, mock_db):
        """Test retrieving agent names for a conversation."""
        mock_names = [
            {"agent_id": "agent_a", "chosen_name": "Alice"},
            {"agent_id": "agent_b", "chosen_name": "Bob"}
        ]
        mock_db.fetchall.return_value = mock_names
        
        names = await repository.get_agent_names("conv-123")
        
        assert len(names) == 2
        assert names["agent_a"] == "Alice"
        assert names["agent_b"] == "Bob"
    
    @pytest.mark.asyncio
    async def test_list_conversations_by_experiment(self, repository, mock_db):
        """Test listing conversations for an experiment."""
        mock_convs = [
            {
                "conversation_id": "conv-1",
                "status": "completed",
                "started_at": datetime.now(),
                "ended_at": datetime.now(),
                "total_turns": 10
            },
            {
                "conversation_id": "conv-2",
                "status": "running",
                "started_at": datetime.now(),
                "ended_at": None,
                "total_turns": 5
            }
        ]
        mock_db.fetchall.return_value = mock_convs
        
        convs = await repository.list_conversations_by_experiment("exp-123")
        
        assert len(convs) == 2
        assert convs[0]["conversation_id"] == "conv-1"
        assert convs[0]["status"] == "completed"
        assert convs[1]["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_get_conversation_stats(self, repository, mock_db):
        """Test getting conversation statistics."""
        mock_stats = {
            "total_messages": 20,
            "total_turns": 10,
            "avg_message_length": 45.5,
            "total_tokens": 500
        }
        mock_db.fetchone.return_value = mock_stats
        
        stats = await repository.get_conversation_stats("conv-123")
        
        assert stats["total_messages"] == 20
        assert stats["total_turns"] == 10
        assert stats["avg_message_length"] == 45.5
    
    @pytest.mark.asyncio
    async def test_delete_conversation(self, repository, mock_db):
        """Test deleting a conversation and related data."""
        await repository.delete_conversation("conv-123")
        
        # Should execute multiple DELETE queries
        assert mock_db.execute.call_count >= 1
        
        # Check conversation delete was called
        delete_calls = [call[0][0] for call in mock_db.execute.call_args_list]
        assert any("DELETE FROM conversations" in call for call in delete_calls)
    
    @pytest.mark.asyncio
    async def test_update_conversation_metrics(self, repository, mock_db):
        """Test updating conversation metrics."""
        await repository.update_conversation_metrics(
            conversation_id="conv-123",
            total_messages=20,
            total_turns=10,
            total_tokens=500
        )
        
        # Check UPDATE was called
        call_args = mock_db.execute.call_args[0][0]
        assert "UPDATE conversations" in call_args
        assert "total_messages = ?" in call_args
        assert "total_turns = ?" in call_args
    
    @pytest.mark.asyncio
    async def test_get_active_conversations(self, repository, mock_db):
        """Test getting all active conversations."""
        mock_active = [
            {"conversation_id": "conv-1", "experiment_id": "exp-1"},
            {"conversation_id": "conv-2", "experiment_id": "exp-2"}
        ]
        mock_db.fetchall.return_value = mock_active
        
        active = await repository.get_active_conversations()
        
        assert len(active) == 2
        
        # Check query filtered by status
        call_args = mock_db.execute.call_args[0][0]
        assert "WHERE status = 'running'" in call_args