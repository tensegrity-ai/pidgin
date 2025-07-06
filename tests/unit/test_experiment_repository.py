"""Tests for ExperimentRepository."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
import uuid
import json

from pidgin.database.repositories.experiment_repository import ExperimentRepository
from pidgin.database.async_duckdb import AsyncDuckDB


class TestExperimentRepository:
    """Test ExperimentRepository functionality."""
    
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
        """Create an ExperimentRepository instance."""
        return ExperimentRepository(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_experiment(self, repository, mock_db):
        """Test creating a new experiment."""
        # Mock UUID generation
        test_id = "exp-test-123"
        with patch('uuid.uuid4', return_value=Mock(hex=test_id)):
            exp_id = await repository.create_experiment(
                name="Test Experiment",
                config={
                    "model_a": "gpt-4",
                    "model_b": "claude-3",
                    "max_turns": 10,
                    "temperature_a": 0.7,
                    "temperature_b": 0.7
                }
            )
        
        assert exp_id == test_id
        
        # Verify the query was executed
        mock_db.execute.assert_called()
        call_args = mock_db.execute.call_args[0][0]
        assert "INSERT INTO experiments" in call_args
    
    @pytest.mark.asyncio
    async def test_get_experiment(self, repository, mock_db):
        """Test retrieving an experiment by ID."""
        mock_exp = {
            "experiment_id": "exp-123",
            "name": "Test Experiment",
            "config": json.dumps({"model_a": "gpt-4", "model_b": "claude-3"}),
            "status": "running",
            "created_at": datetime.now(),
            "total_conversations": 10,
            "completed_conversations": 5
        }
        mock_db.fetchone.return_value = mock_exp
        
        exp = await repository.get_experiment("exp-123")
        
        assert exp is not None
        assert exp["experiment_id"] == "exp-123"
        assert exp["name"] == "Test Experiment"
        assert exp["status"] == "running"
        # Config should be parsed from JSON
        assert isinstance(exp["config"], dict)
        assert exp["config"]["model_a"] == "gpt-4"
    
    @pytest.mark.asyncio
    async def test_get_experiment_not_found(self, repository, mock_db):
        """Test retrieving non-existent experiment."""
        mock_db.fetchone.return_value = None
        
        exp = await repository.get_experiment("non-existent")
        
        assert exp is None
    
    @pytest.mark.asyncio
    async def test_update_experiment_status(self, repository, mock_db):
        """Test updating experiment status."""
        # Mock that the experiment exists
        mock_db.fetchone.return_value = {"count": 1}
        
        await repository.update_experiment_status("exp-123", "completed")
        
        # Should have executed UPDATE query
        mock_db.execute.assert_called()
        # Check all executed queries
        all_calls = [call[0][0] for call in mock_db.execute.call_args_list]
        assert any("UPDATE experiments" in call and "status = ?" in call for call in all_calls)
    
    @pytest.mark.asyncio
    async def test_update_experiment_status_with_error(self, repository, mock_db):
        """Test updating experiment status with error message."""
        mock_db.fetchone.return_value = {"count": 1}
        
        await repository.update_experiment_status(
            "exp-123", 
            "failed",
            error_message="Connection timeout"
        )
        
        # Should include error in update
        all_calls = [call[0][0] for call in mock_db.execute.call_args_list]
        assert any("error_message = ?" in call for call in all_calls)
    
    @pytest.mark.asyncio
    async def test_list_experiments(self, repository, mock_db):
        """Test listing all experiments."""
        mock_exps = [
            {
                "experiment_id": "exp-1",
                "name": "Experiment 1",
                "status": "completed",
                "config": json.dumps({"model_a": "gpt-4"}),
                "created_at": datetime.now(),
                "completed_at": datetime.now()
            },
            {
                "experiment_id": "exp-2",
                "name": "Experiment 2", 
                "status": "running",
                "config": json.dumps({"model_a": "claude-3"}),
                "created_at": datetime.now(),
                "completed_at": None
            }
        ]
        mock_db.fetchall.return_value = mock_exps
        
        exps = await repository.list_experiments()
        
        assert len(exps) == 2
        assert exps[0]["experiment_id"] == "exp-1"
        assert exps[1]["experiment_id"] == "exp-2"
        # Config should be parsed
        assert isinstance(exps[0]["config"], dict)
    
    @pytest.mark.asyncio
    async def test_list_experiments_with_filter(self, repository, mock_db):
        """Test listing experiments with status filter."""
        mock_db.fetchall.return_value = []
        
        await repository.list_experiments(status_filter="completed")
        
        # Check query included WHERE clause
        call_args = mock_db.execute.call_args[0][0]
        assert "WHERE status = ?" in call_args
    
    @pytest.mark.asyncio
    async def test_mark_running_conversations_failed(self, repository, mock_db):
        """Test marking all running conversations as failed."""
        await repository.mark_running_conversations_failed("exp-123")
        
        # Should update conversations table
        mock_db.execute.assert_called()
        call_args = mock_db.execute.call_args[0][0]
        assert "UPDATE conversations" in call_args
        assert "SET status = ?" in call_args
        assert "WHERE experiment_id = ?" in call_args
        assert "status = 'running'" in call_args
    
    @pytest.mark.asyncio
    async def test_get_experiment_stats(self, repository, mock_db):
        """Test getting experiment statistics."""
        mock_stats = {
            "total_conversations": 100,
            "completed_conversations": 95,
            "failed_conversations": 5,
            "total_messages": 2000,
            "avg_turns_per_conversation": 10.5,
            "total_tokens": 150000
        }
        mock_db.fetchone.return_value = mock_stats
        
        stats = await repository.get_experiment_stats("exp-123")
        
        assert stats["total_conversations"] == 100
        assert stats["completed_conversations"] == 95
        assert stats["avg_turns_per_conversation"] == 10.5
    
    @pytest.mark.asyncio
    async def test_delete_experiment(self, repository, mock_db):
        """Test deleting an experiment."""
        await repository.delete_experiment("exp-123")
        
        # Should execute multiple DELETE queries (cascade)
        assert mock_db.execute.call_count >= 1
        
        # Check that experiments table delete was called
        delete_calls = [call[0][0] for call in mock_db.execute.call_args_list]
        assert any("DELETE FROM experiments" in call for call in delete_calls)
    
    @pytest.mark.asyncio
    async def test_get_experiment_by_name(self, repository, mock_db):
        """Test finding experiment by name."""
        mock_exp = {
            "experiment_id": "exp-123",
            "name": "My Test Experiment",
            "config": json.dumps({"test": True})
        }
        mock_db.fetchone.return_value = mock_exp
        
        exp = await repository.get_experiment_by_name("My Test Experiment")
        
        assert exp is not None
        assert exp["name"] == "My Test Experiment"
        
        # Check query
        call_args = mock_db.execute.call_args[0][0]
        assert "WHERE name = ?" in call_args
    
    @pytest.mark.asyncio
    async def test_update_experiment_config(self, repository, mock_db):
        """Test updating experiment configuration."""
        new_config = {
            "model_a": "gpt-4-turbo",
            "model_b": "claude-3-opus",
            "temperature_a": 0.8
        }
        
        await repository.update_experiment_config("exp-123", new_config)
        
        # Should update config field
        call_args = mock_db.execute.call_args[0][0]
        assert "UPDATE experiments" in call_args
        assert "SET config = ?" in call_args
        
        # Config should be JSON serialized
        params = mock_db.execute.call_args[0][1]
        assert json.dumps(new_config) in params