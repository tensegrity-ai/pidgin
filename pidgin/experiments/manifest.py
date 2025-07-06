# pidgin/experiments/manifest.py
"""Manifest management for experiments."""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import threading


class ManifestManager:
    """Manages experiment manifest with atomic updates."""
    
    def __init__(self, experiment_dir: Path):
        """Initialize manifest manager.
        
        Args:
            experiment_dir: Directory containing the experiment
        """
        self.experiment_dir = experiment_dir
        self.manifest_path = experiment_dir / "manifest.json"
        self._lock = threading.Lock()
    
    def create(self, experiment_id: str, name: str, config: Dict[str, Any], 
               total_conversations: int) -> None:
        """Create initial manifest.
        
        Args:
            experiment_id: Unique experiment ID
            name: Human-readable experiment name
            config: Experiment configuration
            total_conversations: Total number of conversations to run
        """
        manifest = {
            "experiment_id": experiment_id,
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": config,
            "total_conversations": total_conversations,
            "status": "created",
            "conversations": {}
        }
        
        self._write_atomic(manifest)
    
    def add_conversation(self, conversation_id: str, jsonl_filename: str) -> None:
        """Add a new conversation to the manifest.
        
        Args:
            conversation_id: Unique conversation ID
            jsonl_filename: Name of the JSONL file for this conversation
        """
        with self._lock:
            manifest = self._read()
            manifest["conversations"][conversation_id] = {
                "status": "created",
                "jsonl": jsonl_filename,
                "last_line": 0,
                "turns_completed": 0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            # Update experiment status if needed
            if manifest["status"] == "created":
                manifest["status"] = "running"
                manifest["started_at"] = datetime.now(timezone.utc).isoformat()
            
            self._write_atomic(manifest)
    
    def update_conversation(self, conversation_id: str, status: str = None,
                          last_line: int = None, turns_completed: int = None,
                          error: str = None) -> None:
        """Update conversation status and progress.
        
        Args:
            conversation_id: Conversation to update
            status: New status (running, completed, failed)
            last_line: Last line number written to JSONL
            turns_completed: Number of turns completed
            error: Error message if failed
        """
        with self._lock:
            manifest = self._read()
            conv = manifest["conversations"].get(conversation_id, {})
            
            if status:
                conv["status"] = status
            if last_line is not None:
                conv["last_line"] = last_line
            if turns_completed is not None:
                conv["turns_completed"] = turns_completed
            if error:
                conv["error"] = error
            
            conv["last_updated"] = datetime.now(timezone.utc).isoformat()
            manifest["conversations"][conversation_id] = conv
            
            # Update experiment-level counts
            self._update_experiment_stats(manifest)
            
            self._write_atomic(manifest)
    
    def update_experiment_status(self, status: str, error: str = None) -> None:
        """Update experiment status.
        
        Args:
            status: New status (running, completed, failed, interrupted)
            error: Optional error message
        """
        with self._lock:
            manifest = self._read()
            manifest["status"] = status
            if error:
                manifest["error"] = error
            if status in ["completed", "failed", "interrupted"]:
                manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            self._write_atomic(manifest)
    
    def get_manifest(self) -> Dict[str, Any]:
        """Get current manifest data.
        
        Returns:
            Current manifest dictionary
        """
        return self._read()
    
    def _read(self) -> Dict[str, Any]:
        """Read manifest from disk.
        
        Returns:
            Manifest dictionary or empty dict if not found
        """
        if not self.manifest_path.exists():
            return {}
        
        try:
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _write_atomic(self, manifest: Dict[str, Any]) -> None:
        """Write manifest atomically.
        
        Args:
            manifest: Manifest data to write
        """
        # Write to temporary file first
        temp_path = self.manifest_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Atomic rename
        os.replace(temp_path, self.manifest_path)
    
    def _update_experiment_stats(self, manifest: Dict[str, Any]) -> None:
        """Update experiment-level statistics based on conversations.
        
        Args:
            manifest: Manifest to update (modified in place)
        """
        completed = 0
        failed = 0
        running = 0
        
        for conv in manifest["conversations"].values():
            if conv["status"] == "completed":
                completed += 1
            elif conv["status"] == "failed":
                failed += 1
            elif conv["status"] == "running":
                running += 1
        
        manifest["completed_conversations"] = completed
        manifest["failed_conversations"] = failed
        manifest["running_conversations"] = running
        
        # Update experiment status if all done
        total = manifest.get("total_conversations", 0)
        if completed + failed >= total and total > 0:
            if failed == 0:
                manifest["status"] = "completed"
            else:
                manifest["status"] = "completed_with_failures"