"""Tests for checkpoint system."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from pidgin.checkpoint import ConversationState, CheckpointManager
from pidgin.types import Message


class TestConversationState:
    """Test conversation state serialization and checkpoint functionality."""
    
    def test_state_creation(self):
        """Test creating a conversation state."""
        state = ConversationState(
            model_a="claude-3-opus-20240229",
            model_b="gpt-4",
            agent_a_id="agent_a",
            agent_b_id="agent_b",
            max_turns=10,
            initial_prompt="Hello!"
        )
        
        assert state.model_a == "claude-3-opus-20240229"
        assert state.model_b == "gpt-4"
        assert state.turn_count == 0
        assert len(state.messages) == 0
    
    def test_add_message(self):
        """Test adding messages and turn counting."""
        state = ConversationState()
        
        # Add system message (shouldn't count as turn)
        state.add_message(Message(role="system", content="Start"))
        assert state.turn_count == 0
        
        # Add user and assistant messages
        state.add_message(Message(role="user", content="Hello"))
        state.add_message(Message(role="assistant", content="Hi there"))
        assert state.turn_count == 1
        
        # Add another pair
        state.add_message(Message(role="user", content="How are you?"))
        state.add_message(Message(role="assistant", content="I'm well"))
        assert state.turn_count == 2
    
    def test_serialization(self):
        """Test conversion to/from dictionary."""
        state = ConversationState(
            model_a="claude",
            model_b="gpt-4",
            max_turns=5
        )
        state.add_message(Message(role="user", content="Test"))
        
        # Convert to dict
        data = state.to_dict()
        assert data['model_a'] == "claude"
        assert data['version'] == "1.0"
        assert len(data['messages']) == 1
        assert isinstance(data['start_time'], str)  # ISO format
        
        # Convert back
        restored = ConversationState.from_dict(data)
        assert restored.model_a == state.model_a
        assert restored.turn_count == state.turn_count
        assert len(restored.messages) == len(state.messages)
    
    def test_checkpoint_save_load(self):
        """Test saving and loading checkpoints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            transcript_path = tmppath / "test_transcript.md"
            
            # Create state
            state = ConversationState(
                model_a="claude",
                model_b="gpt-4",
                transcript_path=str(transcript_path)
            )
            state.add_message(Message(role="user", content="Hello"))
            state.add_message(Message(role="assistant", content="Hi"))
            
            # Save checkpoint
            checkpoint_path = state.save_checkpoint()
            assert checkpoint_path.exists()
            assert checkpoint_path.suffix == '.checkpoint'
            
            # Load checkpoint
            loaded = ConversationState.load_checkpoint(checkpoint_path)
            assert loaded.model_a == state.model_a
            assert loaded.model_b == state.model_b
            assert len(loaded.messages) == len(state.messages)
            assert loaded.pause_time is not None
    
    def test_resume_info(self):
        """Test getting resume information."""
        state = ConversationState(
            model_a="claude",
            model_b="gpt-4",
            max_turns=10,
            turn_count=3
        )
        
        info = state.get_resume_info()
        assert info['turn_count'] == 3
        assert info['max_turns'] == 10
        assert info['remaining_turns'] == 7
        assert info['model_a'] == "claude"
        assert info['model_b'] == "gpt-4"


class TestCheckpointManager:
    """Test checkpoint management functionality."""
    
    def test_find_latest_checkpoint(self):
        """Test finding the most recent checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            manager = CheckpointManager(tmppath)
            
            # No checkpoints initially
            assert manager.find_latest_checkpoint() is None
            
            # Create some checkpoints
            cp1 = tmppath / "conv1.checkpoint"
            cp2 = tmppath / "conv2.checkpoint"
            cp3 = tmppath / "subdir" / "conv3.checkpoint"
            
            cp3.parent.mkdir(parents=True)
            
            # Write in order with small delays
            import time
            cp1.write_text("{}")
            time.sleep(0.01)
            cp2.write_text("{}")
            time.sleep(0.01)
            cp3.write_text("{}")
            
            # Should find the most recent
            latest = manager.find_latest_checkpoint()
            assert latest == cp3
    
    def test_list_checkpoints(self):
        """Test listing all checkpoints with info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            manager = CheckpointManager(tmppath)
            
            # Create a valid checkpoint
            state = ConversationState(
                model_a="claude",
                model_b="gpt-4",
                max_turns=10,
                transcript_path=str(tmppath / "test.md")
            )
            checkpoint_path = state.save_checkpoint()
            
            # List checkpoints
            checkpoints = manager.list_checkpoints()
            assert len(checkpoints) == 1
            assert checkpoints[0]['model_a'] == "claude"
            assert checkpoints[0]['model_b'] == "gpt-4"
            assert 'path' in checkpoints[0]
            assert 'size' in checkpoints[0]