"""Checkpoint system for saving and resuming conversations."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict, field
import tempfile
import shutil

from .types import Message


@dataclass
class ConversationState:
    """Serializable conversation state for pause/resume functionality."""
    version: str = "1.0"
    messages: List[Message] = field(default_factory=list)
    turn_count: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    pause_time: Optional[datetime] = None
    model_a: str = ""
    model_b: str = ""
    agent_a_id: str = ""
    agent_b_id: str = ""
    max_turns: int = 0
    initial_prompt: str = ""
    transcript_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO format
        data['start_time'] = self.start_time.isoformat()
        if self.pause_time:
            data['pause_time'] = self.pause_time.isoformat()
        # Convert Message objects to dicts (preserving all fields)
        data['messages'] = [{
            'role': m.role, 
            'content': m.content,
            'agent_id': getattr(m, 'agent_id', 'system')  # Default to 'system' if missing
        } for m in self.messages]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        if data.get('pause_time'):
            data['pause_time'] = datetime.fromisoformat(data['pause_time'])
        # Convert message dicts back to Message objects
        data['messages'] = [Message(**m) for m in data['messages']]
        return cls(**data)
    
    def add_message(self, message: Message) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)
        if message.role in ["assistant", "user"]:
            self.turn_count = len([m for m in self.messages if m.role in ["assistant", "user"]]) // 2
    
    def save_checkpoint(self, transcript_path: Optional[Path] = None) -> Path:
        """Save checkpoint to disk with atomic write."""
        if transcript_path:
            checkpoint_path = transcript_path.with_suffix('.checkpoint')
        elif self.transcript_path:
            checkpoint_path = Path(self.transcript_path).with_suffix('.checkpoint')
        else:
            raise ValueError("No transcript path available for checkpoint")
        
        # Update pause time
        self.pause_time = datetime.now()
        
        # Ensure parent directory exists
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write using temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, 
                                        dir=checkpoint_path.parent, 
                                        suffix='.tmp') as tmp:
            json.dump(self.to_dict(), tmp, indent=2)
            tmp_path = tmp.name
        
        # Atomic rename
        shutil.move(tmp_path, checkpoint_path)
        return checkpoint_path
    
    @classmethod
    def load_checkpoint(cls, checkpoint_path: Path) -> 'ConversationState':
        """Load checkpoint from disk."""
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        
        with open(checkpoint_path, 'r') as f:
            data = json.load(f)
        
        # Version check for future compatibility
        version = data.get('version', '1.0')
        if version != cls.version:
            # Handle version migration here if needed
            pass
        
        return cls.from_dict(data)
    
    def get_resume_info(self) -> Dict[str, Any]:
        """Get information for resuming the conversation."""
        return {
            'turn_count': self.turn_count,
            'max_turns': self.max_turns,
            'remaining_turns': self.max_turns - self.turn_count,
            'model_a': self.model_a,
            'model_b': self.model_b,
            'pause_time': self.pause_time.isoformat() if self.pause_time else None,
            'message_count': len(self.messages)
        }


class CheckpointManager:
    """Manages conversation checkpoints."""
    
    def __init__(self, checkpoint_dir: Optional[Path] = None):
        """Initialize with optional checkpoint directory."""
        self.checkpoint_dir = checkpoint_dir or Path.cwd()
    
    def find_latest_checkpoint(self) -> Optional[Path]:
        """Find the most recent checkpoint file."""
        checkpoints = list(self.checkpoint_dir.glob("**/*.checkpoint"))
        if not checkpoints:
            return None
        
        # Sort by modification time
        return max(checkpoints, key=lambda p: p.stat().st_mtime)
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints with info."""
        checkpoints = []
        for cp_path in self.checkpoint_dir.glob("**/*.checkpoint"):
            try:
                state = ConversationState.load_checkpoint(cp_path)
                info = state.get_resume_info()
                info['path'] = str(cp_path)
                info['size'] = cp_path.stat().st_size
                checkpoints.append(info)
            except Exception as e:
                # Skip corrupted checkpoints
                checkpoints.append({
                    'path': str(cp_path),
                    'error': str(e)
                })
        
        # Sort by pause time (newest first)
        checkpoints.sort(key=lambda x: x.get('pause_time', ''), reverse=True)
        return checkpoints
    
    def clean_old_checkpoints(self, days: int = 7) -> int:
        """Remove checkpoints older than N days."""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        removed = 0
        
        for cp_path in self.checkpoint_dir.glob("**/*.checkpoint"):
            if cp_path.stat().st_mtime < cutoff:
                cp_path.unlink()
                removed += 1
        
        return removed