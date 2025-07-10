# pidgin/experiments/state_builder.py
"""State builder that uses manifests for efficient monitoring."""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field

from .state_types import ExperimentState, ConversationState
from ..io.logger import get_logger

logger = get_logger("state_builder")


class StateBuilder:
    """Builds experiment state efficiently using manifest files."""
    
    def __init__(self):
        """Initialize with empty cache."""
        self.cache: Dict[Path, Tuple[float, ExperimentState]] = {}
    
    def get_experiment_state(self, exp_dir: Path) -> Optional[ExperimentState]:
        """Get experiment state from manifest with caching.
        
        Args:
            exp_dir: Experiment directory
            
        Returns:
            ExperimentState or None if not found
        """
        manifest_path = exp_dir / "manifest.json"
        
        # Check if manifest exists
        if not manifest_path.exists():
            # Fall back to legacy metadata.json
            return self._get_legacy_state(exp_dir)
        
        # Check cache based on mtime
        try:
            current_mtime = manifest_path.stat().st_mtime
        except OSError:
            return None
        
        if exp_dir in self.cache:
            cached_mtime, cached_state = self.cache[exp_dir]
            if current_mtime == cached_mtime:
                logger.debug(f"Using cached state for {exp_dir.name}")
                return cached_state
        
        # Build from manifest
        state = self._build_from_manifest(exp_dir, manifest_path)
        if state:
            # Update cache
            self.cache[exp_dir] = (current_mtime, state)
            logger.debug(f"Built and cached state for {exp_dir.name}")
        
        return state
    
    def list_experiments(self, base_dir: Path, 
                        status_filter: Optional[List[str]] = None) -> List[ExperimentState]:
        """List all experiments efficiently.
        
        Args:
            base_dir: Base experiments directory
            status_filter: Optional list of statuses to include
            
        Returns:
            List of experiment states
        """
        experiments = []
        
        # Find all experiment directories
        for exp_dir in base_dir.glob("exp_*"):
            if not exp_dir.is_dir():
                continue
            
            state = self.get_experiment_state(exp_dir)
            if state:
                # Apply status filter if provided
                if status_filter is None or state.status in status_filter:
                    experiments.append(state)
        
        return experiments
    
    def clear_cache(self) -> None:
        """Clear the cache (useful after bulk operations)."""
        self.cache.clear()
    
    def _build_from_manifest(self, exp_dir: Path, manifest_path: Path) -> Optional[ExperimentState]:
        """Build experiment state from manifest file.
        
        Args:
            exp_dir: Experiment directory
            manifest_path: Path to manifest.json
            
        Returns:
            ExperimentState or None if invalid
        """
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read manifest {manifest_path}: {e}")
            return None
        
        # Extract experiment info
        exp_id = manifest.get("experiment_id", exp_dir.name)
        config = manifest.get("config", {})
        
        # Create experiment state
        state = ExperimentState(
            experiment_id=exp_id,
            name=manifest.get("name", exp_id),
            status=manifest.get("status", "unknown"),
            total_conversations=manifest.get("total_conversations", 0),
            completed_conversations=manifest.get("completed_conversations", 0),
            failed_conversations=manifest.get("failed_conversations", 0)
        )
        
        # Parse timestamps
        if created_at := manifest.get("created_at"):
            state.created_at = self._parse_timestamp(created_at)
        if started_at := manifest.get("started_at"):
            state.started_at = self._parse_timestamp(started_at)
        if completed_at := manifest.get("completed_at"):
            state.completed_at = self._parse_timestamp(completed_at)
        
        # Build conversation states
        for conv_id, conv_info in manifest.get("conversations", {}).items():
            conv_state = ConversationState(
                conversation_id=conv_id,
                experiment_id=exp_id,
                status=conv_info.get("status", "unknown"),
                current_turn=conv_info.get("turns_completed", 0),
                max_turns=config.get("max_turns", 20)
            )
            
            # Set model info from config
            conv_state.agent_a_model = config.get("agent_a_model", "unknown")
            conv_state.agent_b_model = config.get("agent_b_model", "unknown")
            
            # Parse timestamps
            if updated := conv_info.get("last_updated"):
                conv_state.started_at = self._parse_timestamp(updated)
            
            # Get convergence from last turn (would need JSONL for this)
            # For now, we'll leave it empty
            
            state.conversations[conv_id] = conv_state
        
        return state
    
    def _get_legacy_state(self, exp_dir: Path) -> Optional[ExperimentState]:
        """Get state from legacy metadata.json file.
        
        Args:
            exp_dir: Experiment directory
            
        Returns:
            ExperimentState or None if not found
        """
        metadata_path = exp_dir / "metadata.json"
        if not metadata_path.exists():
            return None
        
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        except Exception:
            return None
        
        # Create basic state from metadata
        exp_id = metadata.get("experiment_id", exp_dir.name)
        state = ExperimentState(
            experiment_id=exp_id,
            name=metadata.get("name", exp_id),
            status=metadata.get("status", "unknown"),
            total_conversations=metadata.get("total_conversations", 0),
            completed_conversations=metadata.get("completed_conversations", 0),
            failed_conversations=metadata.get("failed_conversations", 0)
        )
        
        # Parse timestamps
        if started := metadata.get("started_at"):
            state.started_at = self._parse_timestamp(started)
        if completed := metadata.get("completed_at"):
            state.completed_at = self._parse_timestamp(completed)
        
        # We don't have conversation details in legacy format
        # Would need to read JSONL files
        
        return state
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO format timestamp.
        
        Args:
            timestamp_str: Timestamp string
            
        Returns:
            datetime object
        """
        # Handle both with and without timezone
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        
        try:
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            # Try without microseconds
            try:
                return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                return datetime.now()


# Global instance for easy reuse
_state_builder = StateBuilder()

def get_state_builder() -> StateBuilder:
    """Get the global state builder instance."""
    return _state_builder