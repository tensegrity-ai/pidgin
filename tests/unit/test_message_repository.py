"""Tests for MessageRepository."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from pidgin.database.repositories.message_repository import MessageRepository
from pidgin.database.async_duckdb import AsyncDuckDB


class TestMessageRepository:
    """Test MessageRepository functionality."""
    
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
        """Create a MessageRepository instance."""
        return MessageRepository(mock_db)
    
    @pytest.mark.asyncio
    async def test_save_message(self, repository, mock_db):
        """Test saving a message."""
        await repository.save_message(
            conversation_id="conv-123",
            turn_number=5,
            agent_id="agent_a",
            role="user",
            content="Hello, how are you?",
            tokens_used=10
        )
        
        # Verify INSERT was executed
        mock_db.execute.assert_called()
        call_args = mock_db.execute.call_args[0][0]
        assert "INSERT INTO messages" in call_args
        assert "conversation_id" in call_args
        assert "agent_id" in call_args
    
    @pytest.mark.asyncio
    async def test_get_message(self, repository, mock_db):
        """Test retrieving a specific message."""
        mock_message = {
            "message_id": 1,
            "conversation_id": "conv-123",
            "turn_number": 3,
            "agent_id": "agent_b",
            "role": "assistant",
            "content": "I'm doing well, thanks!",
            "timestamp": datetime.now()
        }
        mock_db.fetchone.return_value = mock_message
        
        message = await repository.get_message("conv-123", 3, "agent_b")
        
        assert message is not None
        assert message["agent_id"] == "agent_b"
        assert message["content"] == "I'm doing well, thanks!"
    
    @pytest.mark.asyncio
    async def test_get_turn_messages(self, repository, mock_db):
        """Test retrieving all messages for a turn."""
        mock_messages = [
            {
                "agent_id": "agent_a",
                "role": "user",
                "content": "What's the weather?",
                "timestamp": datetime.now()
            },
            {
                "agent_id": "agent_b",
                "role": "assistant",
                "content": "It's sunny today!",
                "timestamp": datetime.now()
            }
        ]
        mock_db.fetchall.return_value = mock_messages
        
        messages = await repository.get_turn_messages("conv-123", 5)
        
        assert len(messages) == 2
        assert messages[0]["agent_id"] == "agent_a"
        assert messages[1]["agent_id"] == "agent_b"
    
    @pytest.mark.asyncio
    async def test_get_agent_messages(self, repository, mock_db):
        """Test retrieving all messages for an agent."""
        mock_messages = [
            {"turn_number": 1, "content": "Hello!"},
            {"turn_number": 3, "content": "How are you?"},
            {"turn_number": 5, "content": "Great to hear!"}
        ]
        mock_db.fetchall.return_value = mock_messages
        
        messages = await repository.get_agent_messages("conv-123", "agent_a")
        
        assert len(messages) == 3
        assert messages[0]["turn_number"] == 1
        assert messages[2]["content"] == "Great to hear!"
    
    @pytest.mark.asyncio
    async def test_get_conversation_messages(self, repository, mock_db):
        """Test retrieving all messages for a conversation."""
        mock_messages = [
            {
                "turn_number": 1,
                "agent_id": "agent_a",
                "content": "Hello"
            },
            {
                "turn_number": 1,
                "agent_id": "agent_b",
                "content": "Hi there"
            }
        ]
        mock_db.fetchall.return_value = mock_messages
        
        messages = await repository.get_conversation_messages("conv-123")
        
        assert len(messages) == 2
        
        # Check query ordering
        call_args = mock_db.execute.call_args[0][0]
        assert "ORDER BY turn_number, timestamp" in call_args
    
    @pytest.mark.asyncio
    async def test_count_messages(self, repository, mock_db):
        """Test counting messages in a conversation."""
        mock_db.fetchone.return_value = {"count": 42}
        
        count = await repository.count_messages("conv-123")
        
        assert count == 42
    
    @pytest.mark.asyncio
    async def test_get_last_message(self, repository, mock_db):
        """Test retrieving the last message in a conversation."""
        mock_message = {
            "turn_number": 10,
            "agent_id": "agent_b",
            "content": "Goodbye!",
            "timestamp": datetime.now()
        }
        mock_db.fetchone.return_value = mock_message
        
        message = await repository.get_last_message("conv-123")
        
        assert message is not None
        assert message["turn_number"] == 10
        assert message["content"] == "Goodbye!"
        
        # Check query ordering
        call_args = mock_db.execute.call_args[0][0]
        assert "ORDER BY turn_number DESC, timestamp DESC" in call_args
        assert "LIMIT 1" in call_args
    
    @pytest.mark.asyncio
    async def test_update_message_tokens(self, repository, mock_db):
        """Test updating token count for a message."""
        await repository.update_message_tokens(
            conversation_id="conv-123",
            turn_number=5,
            agent_id="agent_a",
            input_tokens=50,
            output_tokens=100
        )
        
        # Check UPDATE was called
        call_args = mock_db.execute.call_args[0][0]
        assert "UPDATE messages" in call_args
        assert "input_tokens = ?" in call_args
        assert "output_tokens = ?" in call_args
    
    @pytest.mark.asyncio
    async def test_search_messages(self, repository, mock_db):
        """Test searching messages by content."""
        mock_results = [
            {
                "turn_number": 3,
                "agent_id": "agent_a",
                "content": "Tell me about Python programming"
            },
            {
                "turn_number": 7,
                "agent_id": "agent_b",
                "content": "Python is a versatile language"
            }
        ]
        mock_db.fetchall.return_value = mock_results
        
        results = await repository.search_messages("conv-123", "Python")
        
        assert len(results) == 2
        assert "Python" in results[0]["content"]
        assert "Python" in results[1]["content"]
        
        # Check LIKE query (case-insensitive by default)
        call_args = mock_db.execute.call_args[0][0]
        assert "WHERE conversation_id = ? AND LOWER(content) LIKE LOWER(?)" in call_args
    
    @pytest.mark.asyncio
    async def test_get_message_stats(self, repository, mock_db):
        """Test getting message statistics."""
        mock_stats = {
            "total_messages": 20,
            "avg_length": 45.5,
            "max_length": 150,
            "min_length": 5,
            "total_tokens": 500
        }
        mock_db.fetchone.return_value = mock_stats
        
        stats = await repository.get_message_stats("conv-123")
        
        assert stats["total_messages"] == 20
        assert stats["avg_length"] == 45.5
        assert stats["max_length"] == 150
    
    @pytest.mark.asyncio
    async def test_delete_messages(self, repository, mock_db):
        """Test deleting all messages for a conversation."""
        await repository.delete_messages("conv-123")
        
        # Check DELETE was called
        call_args = mock_db.execute.call_args[0][0]
        assert "DELETE FROM messages" in call_args
        assert "WHERE conversation_id = ?" in call_args