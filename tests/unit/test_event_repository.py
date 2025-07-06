"""Tests for EventRepository."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
import uuid

from pidgin.database.repositories.event_repository import EventRepository
from pidgin.database.async_duckdb import AsyncDuckDB


class TestEventRepository:
    """Test EventRepository functionality."""
    
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
        """Create an EventRepository instance."""
        return EventRepository(mock_db)
    
    @pytest.mark.asyncio
    async def test_emit_event_with_conversation_id(self, repository, mock_db):
        """Test emitting an event with conversation ID."""
        # Mock the return value
        mock_db.fetchone.return_value = {"event_id": "test-event-123"}
        
        # Emit event
        event_id = await repository.emit_event(
            event_type="message_complete",
            conversation_id="conv-123",
            data={"message": "Hello", "agent_id": "agent_a"}
        )
        
        assert event_id == "test-event-123"
        
        # Verify the query was executed
        mock_db.execute.assert_called()
        call_args = mock_db.execute.call_args[0][0]
        assert "INSERT INTO events" in call_args
        assert "event_type" in call_args
        assert "conversation_id" in call_args
    
    @pytest.mark.asyncio
    async def test_emit_event_without_conversation_id(self, repository, mock_db):
        """Test emitting a system event without conversation ID."""
        mock_db.fetchone.return_value = {"event_id": "system-event-456"}
        
        event_id = await repository.emit_event(
            event_type="system_startup",
            data={"version": "1.0.0"}
        )
        
        assert event_id == "system-event-456"
        mock_db.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_emit_event_with_experiment_id(self, repository, mock_db):
        """Test emitting an event with experiment ID."""
        mock_db.fetchone.return_value = {"event_id": "exp-event-789"}
        
        event_id = await repository.emit_event(
            event_type="experiment_started",
            experiment_id="exp-123",
            data={"name": "Test Experiment"}
        )
        
        assert event_id == "exp-event-789"
        
        # Check that experiment_id was included
        call_args = mock_db.execute.call_args[0]
        assert "experiment_id" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_get_events_by_conversation(self, repository, mock_db):
        """Test retrieving events for a specific conversation."""
        mock_events = [
            {
                "event_id": "1",
                "event_type": "turn_start",
                "conversation_id": "conv-123",
                "data": {"turn_number": 1},
                "timestamp": datetime.now()
            },
            {
                "event_id": "2", 
                "event_type": "message_complete",
                "conversation_id": "conv-123",
                "data": {"content": "Hello"},
                "timestamp": datetime.now()
            }
        ]
        mock_db.fetchall.return_value = mock_events
        
        events = await repository.get_events(conversation_id="conv-123")
        
        assert len(events) == 2
        assert events[0]["event_type"] == "turn_start"
        assert events[1]["event_type"] == "message_complete"
        
        # Check query included conversation filter
        call_args = mock_db.execute.call_args[0]
        assert "conversation_id = ?" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_get_events_by_type(self, repository, mock_db):
        """Test retrieving events by type."""
        mock_db.fetchall.return_value = []
        
        await repository.get_events(event_type="message_complete")
        
        # Check query included type filter
        call_args = mock_db.execute.call_args[0]
        assert "event_type = ?" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_get_events_with_time_range(self, repository, mock_db):
        """Test retrieving events within a time range."""
        mock_db.fetchall.return_value = []
        
        since = datetime(2024, 1, 1, 10, 0, 0)
        until = datetime(2024, 1, 1, 11, 0, 0)
        
        await repository.get_events(
            conversation_id="conv-123",
            since=since,
            until=until
        )
        
        # Check query included time filters
        call_args = mock_db.execute.call_args[0]
        query = call_args[0]
        assert "timestamp >= ?" in query
        assert "timestamp <= ?" in query
        
        # Check parameters
        params = call_args[1]
        assert since in params
        assert until in params
    
    @pytest.mark.asyncio
    async def test_get_events_with_limit(self, repository, mock_db):
        """Test retrieving limited number of events."""
        mock_db.fetchall.return_value = []
        
        await repository.get_events(limit=10)
        
        # Check query included LIMIT
        call_args = mock_db.execute.call_args[0]
        assert "LIMIT ?" in call_args[0]
        assert 10 in call_args[1]
    
    @pytest.mark.asyncio
    async def test_search_events(self, repository, mock_db):
        """Test searching events by content."""
        mock_results = [
            {
                "event_id": "1",
                "event_type": "message_complete", 
                "data": {"content": "Hello world"},
                "conversation_id": "conv-123"
            }
        ]
        mock_db.fetchall.return_value = mock_results
        
        results = await repository.search_events("hello")
        
        assert len(results) == 1
        assert "hello" in results[0]["data"]["content"].lower()
        
        # Check query used LIKE for search
        call_args = mock_db.execute.call_args[0]
        assert "LIKE" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_get_event_count(self, repository, mock_db):
        """Test getting event count."""
        mock_db.fetchone.return_value = {"count": 42}
        
        count = await repository.get_event_count(conversation_id="conv-123")
        
        assert count == 42
        
        # Check query
        call_args = mock_db.execute.call_args[0]
        assert "COUNT(*)" in call_args[0]
        assert "conversation_id = ?" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_delete_events_by_conversation(self, repository, mock_db):
        """Test deleting events for a conversation."""
        await repository.delete_events(conversation_id="conv-123")
        
        # Check DELETE query was executed
        call_args = mock_db.execute.call_args[0]
        assert "DELETE FROM events" in call_args[0]
        assert "conversation_id = ?" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_emit_event_generates_uuid(self, repository, mock_db):
        """Test that emit_event generates a UUID if database doesn't return one."""
        # Mock database returning None
        mock_db.fetchone.return_value = None
        
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = "generated-uuid-123"
            
            event_id = await repository.emit_event(
                event_type="test_event",
                data={}
            )
            
            assert event_id == "generated-uuid-123"