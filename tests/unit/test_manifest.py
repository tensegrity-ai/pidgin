# tests/unit/test_manifest.py
"""Test manifest management functionality."""

import pytest
import json
from pathlib import Path
from datetime import datetime
from pidgin.experiments.manifest import ManifestManager


class TestManifestManager:
    """Test ManifestManager functionality."""
    
    @pytest.fixture
    def manifest_manager(self, tmp_path):
        """Create a manifest manager with temp directory."""
        return ManifestManager(tmp_path)
    
    def test_create_manifest(self, manifest_manager, tmp_path):
        """Test creating initial manifest."""
        experiment_id = "test_exp_123"
        name = "test-experiment"
        config = {"agent_a": "claude", "agent_b": "gpt"}
        total_conversations = 10
        
        manifest_manager.create(experiment_id, name, config, total_conversations)
        
        # Check manifest file exists
        manifest_path = tmp_path / "manifest.json"
        assert manifest_path.exists()
        
        # Read and verify content
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        assert manifest["experiment_id"] == experiment_id
        assert manifest["name"] == name
        assert manifest["config"] == config
        assert manifest["total_conversations"] == total_conversations
        assert manifest["status"] == "created"
        assert manifest["conversations"] == {}
        assert "created_at" in manifest
    
    def test_add_conversation(self, manifest_manager, tmp_path):
        """Test adding conversation to manifest."""
        # Create initial manifest
        manifest_manager.create("experiment_123", "test", {}, 5)
        
        # Add conversation
        conversation_id = "conv_456"
        jsonl_filename = "conv_456_events.jsonl"
        manifest_manager.add_conversation(conversation_id, jsonl_filename)
        
        # Read and verify
        with open(tmp_path / "manifest.json") as f:
            manifest = json.load(f)
        
        assert conversation_id in manifest["conversations"]
        conv_data = manifest["conversations"][conversation_id]
        assert conv_data["status"] == "created"
        assert conv_data["jsonl"] == jsonl_filename
        assert conv_data["last_line"] == 0
        assert conv_data["turns_completed"] == 0
        assert "last_updated" in conv_data
        
        # Status should change to running
        assert manifest["status"] == "running"
        assert "started_at" in manifest
    
    def test_update_conversation(self, manifest_manager, tmp_path):
        """Test updating conversation status."""
        # Setup
        manifest_manager.create("experiment_123", "test", {}, 5)
        manifest_manager.add_conversation("conv_456", "conv_456.jsonl")
        
        # Update conversation
        manifest_manager.update_conversation(
            "conv_456",
            status="completed",
            last_line=100,
            turns_completed=50
        )
        
        # Verify
        with open(tmp_path / "manifest.json") as f:
            manifest = json.load(f)
        
        conversation = manifest["conversations"]["conv_456"]
        assert conversation["status"] == "completed"
        assert conversation["last_line"] == 100
        assert conversation["turns_completed"] == 50
    
    def test_update_experiment_status(self, manifest_manager, tmp_path):
        """Test updating experiment status."""
        # Setup
        manifest_manager.create("experiment_123", "test", {}, 2)
        
        # Update status to completed
        manifest_manager.update_experiment_status("completed")
        
        # Verify
        with open(tmp_path / "manifest.json") as f:
            manifest = json.load(f)
        
        assert manifest["status"] == "completed"
        assert "completed_at" in manifest
    
    def test_update_experiment_status_with_error(self, manifest_manager, tmp_path):
        """Test updating experiment status with error."""
        # Setup
        manifest_manager.create("experiment_123", "test", {}, 1)
        
        # Update with error
        manifest_manager.update_experiment_status("failed", error="Test error message")
        
        # Verify
        with open(tmp_path / "manifest.json") as f:
            manifest = json.load(f)
        
        assert manifest["status"] == "failed"
        assert manifest["error"] == "Test error message"
        assert "completed_at" in manifest
    
    def test_get_manifest(self, manifest_manager, tmp_path):
        """Test getting manifest data."""
        # Create manifest
        manifest_manager.create("experiment_123", "test-exp", {"key": "value"}, 3)
        
        # Get manifest
        manifest = manifest_manager.get_manifest()
        
        assert manifest["experiment_id"] == "experiment_123"
        assert manifest["name"] == "test-exp"
        assert manifest["config"] == {"key": "value"}
        assert manifest["total_conversations"] == 3
    
    def test_automatic_status_update(self, manifest_manager, tmp_path):
        """Test automatic experiment status update when all conversations complete."""
        # Setup experiment with 2 conversations
        manifest_manager.create("experiment_123", "test", {}, 2)
        manifest_manager.add_conversation("conv_1", "conv_1.jsonl")
        manifest_manager.add_conversation("conv_2", "conv_2.jsonl")
        
        # Complete both conversations
        manifest_manager.update_conversation("conv_1", status="completed")
        manifest_manager.update_conversation("conv_2", status="completed")
        
        # Check experiment status was automatically updated
        manifest = manifest_manager.get_manifest()
        assert manifest["status"] == "completed"
        assert manifest["completed_conversations"] == 2
        assert manifest["failed_conversations"] == 0
    
    def test_status_with_failures(self, manifest_manager, tmp_path):
        """Test status update with some failed conversations."""
        # Setup
        manifest_manager.create("experiment_123", "test", {}, 3)
        manifest_manager.add_conversation("conv_1", "conv_1.jsonl")
        manifest_manager.add_conversation("conv_2", "conv_2.jsonl")
        manifest_manager.add_conversation("conv_3", "conv_3.jsonl")
        
        # Mix of completed and failed
        manifest_manager.update_conversation("conv_1", status="completed")
        manifest_manager.update_conversation("conv_2", status="failed", error="Test error")
        manifest_manager.update_conversation("conv_3", status="completed")
        
        # Check status
        manifest = manifest_manager.get_manifest()
        assert manifest["status"] == "completed_with_failures"
        assert manifest["completed_conversations"] == 2
        assert manifest["failed_conversations"] == 1
    
    def test_atomic_writes(self, manifest_manager, tmp_path):
        """Test atomic write operation."""
        # Create initial manifest
        manifest_manager.create("experiment_123", "test", {}, 1)
        
        # Read original content
        with open(tmp_path / "manifest.json") as f:
            original = json.load(f)
        
        # Update should be atomic (temp file + rename)
        manifest_manager.add_conversation("conv_1", "conv_1.jsonl")
        
        # File should still be valid JSON
        with open(tmp_path / "manifest.json") as f:
            updated = json.load(f)
        
        # Should have both old and new data
        assert updated["experiment_id"] == original["experiment_id"]
        assert "conv_1" in updated["conversations"]
    
    def test_concurrent_updates(self, manifest_manager, tmp_path):
        """Test that concurrent updates are handled safely."""
        import threading
        
        # Create initial manifest
        manifest_manager.create("experiment_123", "test", {}, 10)
        
        # Function to add conversations concurrently
        def add_conversation(conv_id):
            manifest_manager.add_conversation(conv_id, f"{conv_id}.jsonl")
        
        # Create threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=add_conversation, args=(f"conv_{i}",))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Verify all conversations were added
        with open(tmp_path / "manifest.json") as f:
            manifest = json.load(f)
        
        assert len(manifest["conversations"]) == 5
        for i in range(5):
            assert f"conv_{i}" in manifest["conversations"]
    
    def test_error_handling(self, manifest_manager, tmp_path):
        """Test error information in manifest."""
        manifest_manager.create("experiment_123", "test", {}, 1)
        manifest_manager.add_conversation("conv_1", "conv_1.jsonl")
        
        # Update with error
        error_msg = "API rate limit exceeded"
        manifest_manager.update_conversation("conv_1", status="failed", error=error_msg)
        
        # Verify error is stored
        with open(tmp_path / "manifest.json") as f:
            manifest = json.load(f)
        
        conversation = manifest["conversations"]["conv_1"]
        assert conversation["error"] == error_msg
        assert conversation["status"] == "failed"
    
    def test_read_nonexistent_manifest(self, manifest_manager):
        """Test reading when manifest doesn't exist."""
        manifest = manifest_manager.get_manifest()
        assert manifest == {}
    
    def test_experiment_stats_tracking(self, manifest_manager, tmp_path):
        """Test that experiment stats are properly tracked."""
        # Create experiment with multiple conversations
        manifest_manager.create("experiment_123", "test", {}, 4)
        
        # Add conversations in different states
        manifest_manager.add_conversation("conv_1", "conv_1.jsonl")
        manifest_manager.add_conversation("conv_2", "conv_2.jsonl")
        manifest_manager.add_conversation("conv_3", "conv_3.jsonl")
        manifest_manager.add_conversation("conv_4", "conv_4.jsonl")
        
        # Update to different statuses
        manifest_manager.update_conversation("conv_1", status="completed")
        manifest_manager.update_conversation("conv_2", status="running")
        manifest_manager.update_conversation("conv_3", status="failed")
        # conv_4 remains created
        
        # Check stats
        manifest = manifest_manager.get_manifest()
        assert manifest["completed_conversations"] == 1
        assert manifest["failed_conversations"] == 1
        assert manifest["running_conversations"] == 1