"""Build experiment state from JSONL event streams."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from ..io.logger import get_logger

logger = get_logger("state_builder")


@dataclass
class ConversationState:
    """Lightweight state for a single conversation."""
    conversation_id: str
    experiment_id: str
    status: str = "created"
    current_turn: int = 0
    max_turns: int = 20
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    agent_a_model: str = "unknown"
    agent_b_model: str = "unknown"
    convergence_scores: List[float] = field(default_factory=list)
    last_convergence: Optional[float] = None
    error_message: Optional[str] = None


@dataclass 
class ExperimentState:
    """Lightweight state for an experiment."""
    experiment_id: str
    name: str
    status: str = "created"
    total_conversations: int = 0
    completed_conversations: int = 0
    failed_conversations: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    conversations: Dict[str, ConversationState] = field(default_factory=dict)
    
    @property
    def active_conversations(self) -> int:
        """Count of currently running conversations."""
        return sum(1 for c in self.conversations.values() if c.status == "running")
    
    @property
    def progress(self) -> tuple[int, int]:
        """Return (completed, total) conversations."""
        completed = self.completed_conversations + self.failed_conversations
        return (completed, self.total_conversations)


class StateBuilder:
    """Builds experiment and conversation state from JSONL event streams."""
    
    @staticmethod
    def from_experiment_dir(exp_dir: Path) -> Optional[ExperimentState]:
        """Build experiment state from all JSONL files in experiment directory.
        
        Args:
            exp_dir: Path to experiment directory
            
        Returns:
            ExperimentState or None if no valid events found
        """
        if not exp_dir.exists():
            return None
            
        # Find all conversation JSONL files
        jsonl_files = list(exp_dir.glob("conv_*_events.jsonl"))
        if not jsonl_files:
            return None
            
        # Extract experiment ID from first conversation file
        first_file = jsonl_files[0]
        # Pattern: conv_{exp_id}_{uuid}_events.jsonl
        parts = first_file.stem.split('_')
        if len(parts) < 3:
            return None
            
        exp_id = parts[1]  # Extract exp ID
        
        # Initialize experiment state
        state = ExperimentState(
            experiment_id=exp_id,
            name=exp_id  # Will be updated from events
        )
        
        # Process each conversation's events
        for jsonl_file in jsonl_files:
            conv_state = StateBuilder._build_conversation_state(jsonl_file)
            if conv_state:
                state.conversations[conv_state.conversation_id] = conv_state
                
                # Update experiment-level counts
                if conv_state.status == "completed":
                    state.completed_conversations += 1
                elif conv_state.status == "failed":
                    state.failed_conversations += 1
        
        # Infer experiment status from conversations
        state.total_conversations = len(state.conversations)
        if state.active_conversations > 0:
            state.status = "running"
        elif state.completed_conversations + state.failed_conversations == state.total_conversations:
            state.status = "completed"
        
        return state
    
    @staticmethod
    def _build_conversation_state(jsonl_path: Path) -> Optional[ConversationState]:
        """Build conversation state from JSONL file.
        
        Args:
            jsonl_path: Path to conversation JSONL file
            
        Returns:
            ConversationState or None if no valid events
        """
        if not jsonl_path.exists():
            return None
            
        state = None
        
        try:
            with open(jsonl_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                        
                    try:
                        event = json.loads(line)
                        
                        # Initialize state from first event
                        if state is None and 'conversation_id' in event:
                            state = ConversationState(
                                conversation_id=event['conversation_id'],
                                experiment_id=event.get('experiment_id', 'unknown')
                            )
                        
                        if state:
                            StateBuilder._apply_event_to_conversation(state, event)
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping invalid JSON line in {jsonl_path}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading {jsonl_path}: {e}")
            
        return state
    
    @staticmethod
    def _apply_event_to_conversation(state: ConversationState, event: Dict[str, Any]):
        """Apply an event to conversation state.
        
        Args:
            state: ConversationState to update
            event: Event dictionary
        """
        event_type = event.get('event_type')
        
        if event_type == 'ConversationCreated':
            # Extract config
            data = event.get('data', {})
            state.agent_a_model = data.get('agent_a_model', state.agent_a_model)
            state.agent_b_model = data.get('agent_b_model', state.agent_b_model)
            state.max_turns = data.get('max_turns', state.max_turns)
            
        elif event_type == 'ConversationStartEvent':
            state.status = 'running'
            state.started_at = StateBuilder._parse_timestamp(event.get('timestamp'))
            
        elif event_type == 'TurnCompleteEvent':
            state.current_turn = event.get('turn_number', state.current_turn)
            convergence = event.get('convergence_score')
            if convergence is not None:
                state.convergence_scores.append(convergence)
                state.last_convergence = convergence
                
        elif event_type == 'ConversationEndEvent':
            state.status = 'completed'
            state.completed_at = StateBuilder._parse_timestamp(event.get('timestamp'))
            
        elif event_type == 'ConversationStatusChanged':
            data = event.get('data', {})
            state.status = data.get('status', state.status)
            if state.status == 'failed':
                state.error_message = data.get('error_message')
                
    @staticmethod
    def from_active_experiments(base_dir: Path) -> List[ExperimentState]:
        """Build states for all active experiments.
        
        Args:
            base_dir: Base directory containing experiments
            
        Returns:
            List of ExperimentState objects for active experiments
        """
        experiments = []
        
        # Look for experiment directories
        for exp_dir in base_dir.glob("exp_*"):
            if exp_dir.is_dir():
                state = StateBuilder.from_experiment_dir(exp_dir)
                if state and state.status in ["running", "created"]:
                    experiments.append(state)
                    
        return experiments
    
    @staticmethod
    def _parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO format timestamp string."""
        if not timestamp_str:
            return None
            
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception:
            return None
    
    @staticmethod
    def tail_events(jsonl_path: Path, callback):
        """Tail a JSONL file for new events.
        
        Args:
            jsonl_path: Path to JSONL file
            callback: Async function to call with each new event
        """
        import asyncio
        
        async def _tail():
            """Async tail implementation."""
            # Start at end of file
            with open(jsonl_path, 'r') as f:
                f.seek(0, 2)  # Go to end
                
                while True:
                    line = f.readline()
                    if line:
                        try:
                            event = json.loads(line)
                            await callback(event)
                        except json.JSONDecodeError:
                            pass
                    else:
                        # No new data, wait a bit
                        await asyncio.sleep(0.1)
                        
        return _tail()