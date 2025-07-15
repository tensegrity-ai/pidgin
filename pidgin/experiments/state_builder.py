# pidgin/experiments/state_builder.py
"""State builder that uses manifests for efficient monitoring."""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field

from .state_types import ExperimentState, ConversationState
from ..io.logger import get_logger
from ..core.types import Message

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
        
        # Find all experiment directories (both exp_* and experiment_* patterns)
        for pattern in ["exp_*", "experiment_*"]:
            for exp_dir in base_dir.glob(pattern):
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
                # Use last_updated as a proxy for both started and completed
                conv_state.started_at = self._parse_timestamp(updated)
                if conv_state.status == "completed":
                    conv_state.completed_at = self._parse_timestamp(updated)
            
            # Try to get more accurate timestamps from JSONL if available
            jsonl_timestamps = self._get_conversation_timestamps(exp_dir, conv_id)
            if jsonl_timestamps:
                if jsonl_timestamps.get('started_at'):
                    conv_state.started_at = jsonl_timestamps['started_at']
                if jsonl_timestamps.get('completed_at'):
                    conv_state.completed_at = jsonl_timestamps['completed_at']
            
            # Get convergence from JSONL files
            conv_state.last_convergence = self._get_last_convergence(exp_dir, conv_id)
            
            # Get truncation info from JSONL files
            truncation_info = self._get_truncation_info(exp_dir, conv_id)
            if truncation_info:
                conv_state.truncation_count = truncation_info.get('count', 0)
                conv_state.last_truncation_turn = truncation_info.get('last_turn')
            
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
            datetime object (always timezone-aware)
        """
        # Handle both with and without timezone
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        
        try:
            dt = datetime.fromisoformat(timestamp_str)
            # Ensure timezone awareness
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            # Try without microseconds
            try:
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
                # Make timezone aware
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                return datetime.now(timezone.utc)
    
    def _get_last_convergence(self, exp_dir: Path, conv_id: str) -> Optional[float]:
        """Get the last convergence score for a conversation from JSONL files.
        
        Args:
            exp_dir: Experiment directory
            conv_id: Conversation ID
            
        Returns:
            Last convergence score or None if not found
        """
        # Look for JSONL files in the experiment directory
        jsonl_files = list(exp_dir.glob("*.jsonl"))
        if not jsonl_files:
            return None
        
        # Read the most recent JSONL file (typically there's only one per conversation)
        last_convergence = None
        for jsonl_file in jsonl_files:
            if conv_id in jsonl_file.name:
                try:
                    with open(jsonl_file, 'r') as f:
                        # Read file backwards to find the last TurnCompleteEvent
                        lines = f.readlines()
                        for line in reversed(lines):
                            if not line.strip():
                                continue
                            try:
                                event = json.loads(line.strip())
                                if (event.get('event_type') == 'TurnCompleteEvent' and 
                                    event.get('conversation_id') == conv_id and 
                                    event.get('convergence_score') is not None):
                                    last_convergence = event.get('convergence_score')
                                    break
                            except (json.JSONDecodeError, KeyError):
                                continue
                except (OSError, IOError):
                    continue
                
                # If we found a convergence score, we're done
                if last_convergence is not None:
                    break
        
        return last_convergence
    
    def _get_conversation_timestamps(self, exp_dir: Path, conv_id: str) -> Dict[str, Optional[datetime]]:
        """Get start and end timestamps for a conversation from JSONL files.
        
        Args:
            exp_dir: Experiment directory
            conv_id: Conversation ID
            
        Returns:
            Dictionary with 'started_at' and 'completed_at' keys
        """
        jsonl_files = list(exp_dir.glob("*.jsonl"))
        if not jsonl_files:
            return {}
        
        started_at = None
        completed_at = None
        
        for jsonl_file in jsonl_files:
            if conv_id in jsonl_file.name:
                try:
                    with open(jsonl_file, 'r') as f:
                        lines = f.readlines()
                        
                        # Find first ConversationStartEvent
                        for line in lines:
                            if not line.strip():
                                continue
                            try:
                                event = json.loads(line.strip())
                                if (event.get('event_type') == 'ConversationStartEvent' and 
                                    event.get('conversation_id') == conv_id):
                                    started_at = self._parse_timestamp(event.get('timestamp'))
                                    break
                            except (json.JSONDecodeError, KeyError):
                                continue
                        
                        # Find last ConversationEndEvent
                        for line in reversed(lines):
                            if not line.strip():
                                continue
                            try:
                                event = json.loads(line.strip())
                                if (event.get('event_type') == 'ConversationEndEvent' and 
                                    event.get('conversation_id') == conv_id):
                                    completed_at = self._parse_timestamp(event.get('timestamp'))
                                    break
                            except (json.JSONDecodeError, KeyError):
                                continue
                                
                except (OSError, IOError):
                    continue
                
                # If we found timestamps, we're done
                if started_at is not None:
                    break
        
        return {
            'started_at': started_at,
            'completed_at': completed_at
        }
    
    def _get_truncation_info(self, exp_dir: Path, conv_id: str) -> Dict[str, Any]:
        """Get truncation information for a conversation from JSONL files.
        
        Args:
            exp_dir: Experiment directory
            conv_id: Conversation ID
            
        Returns:
            Dictionary with 'count' and 'last_turn' keys
        """
        jsonl_files = list(exp_dir.glob("*.jsonl"))
        if not jsonl_files:
            return {}
        
        truncation_count = 0
        last_truncation_turn = None
        
        for jsonl_file in jsonl_files:
            if conv_id in jsonl_file.name:
                try:
                    with open(jsonl_file, 'r') as f:
                        lines = f.readlines()
                        
                        # Count ContextTruncationEvent occurrences
                        for line in lines:
                            if not line.strip():
                                continue
                            try:
                                event = json.loads(line.strip())
                                if (event.get('event_type') == 'ContextTruncationEvent' and 
                                    event.get('conversation_id') == conv_id):
                                    truncation_count += 1
                                    last_truncation_turn = event.get('turn_number')
                            except (json.JSONDecodeError, KeyError):
                                continue
                                
                except (OSError, IOError):
                    continue
                
                # If we found truncations, we're done
                if truncation_count > 0:
                    break
        
        return {
            'count': truncation_count,
            'last_turn': last_truncation_turn
        }
    
    def get_conversation_state(self, exp_dir: Path, conversation_id: str, 
                                up_to_turn: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Extract conversation state up to a specific turn for branching.
        
        Args:
            exp_dir: Experiment directory
            conversation_id: Conversation ID
            up_to_turn: Turn number to extract up to (None for all)
            
        Returns:
            Dictionary with messages and configuration
        """
        # Find JSONL file for this conversation
        jsonl_files = list(exp_dir.glob(f"*{conversation_id}*.jsonl"))
        if not jsonl_files:
            logger.error(f"No JSONL file found for conversation {conversation_id}")
            return None
        
        jsonl_file = jsonl_files[0]  # Should only be one
        
        messages = []
        config = {}
        metadata = {}
        
        try:
            with open(jsonl_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        event = json.loads(line.strip())
                        event_type = event.get('event_type')
                        
                        # Extract configuration from start event
                        if event_type == 'ConversationStartEvent':
                            config = {
                                'agent_a_model': event.get('agent_a_model'),
                                'agent_b_model': event.get('agent_b_model'),
                                'initial_prompt': event.get('initial_prompt'),
                                'max_turns': event.get('max_turns'),
                                'temperature_a': event.get('temperature_a'),
                                'temperature_b': event.get('temperature_b'),
                                'awareness_a': event.get('awareness_a'),
                                'awareness_b': event.get('awareness_b'),
                                'first_speaker': event.get('first_speaker', 'agent_a'),
                                'prompt_tag': event.get('prompt_tag'),
                            }
                            metadata['original_experiment_id'] = event.get('experiment_id')
                            metadata['started_at'] = event.get('timestamp')
                        
                        # Collect messages
                        elif event_type == 'MessageCompleteEvent':
                            turn_number = event.get('turn_number', 0)
                            
                            # Check if we've reached the turn limit
                            if up_to_turn is not None and turn_number > up_to_turn:
                                break
                            
                            message = Message(
                                role=event.get('agent_id', 'assistant'),
                                content=event.get('content', ''),
                                turn_number=turn_number
                            )
                            messages.append(message)
                        
                        # Track system prompts
                        elif event_type == 'SystemPromptEvent':
                            # Store system prompts separately
                            if 'system_prompts' not in metadata:
                                metadata['system_prompts'] = {}
                            agent_id = event.get('agent_id')
                            if agent_id:
                                metadata['system_prompts'][agent_id] = event.get('prompt')
                    
                    except json.JSONDecodeError:
                        continue
            
            # Validate we have enough data
            if not config or not messages:
                logger.error(f"Incomplete data for conversation {conversation_id}")
                return None
            
            return {
                'conversation_id': conversation_id,
                'messages': messages,
                'config': config,
                'metadata': metadata,
                'branch_point': up_to_turn or len(messages)
            }
            
        except Exception as e:
            logger.error(f"Error reading conversation state: {e}")
            return None


# Global instance for easy reuse
_state_builder = StateBuilder()

def get_state_builder() -> StateBuilder:
    """Get the global state builder instance."""
    return _state_builder