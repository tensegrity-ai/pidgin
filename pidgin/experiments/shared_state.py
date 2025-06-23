# pidgin/experiments/shared_state.py
"""Shared state for real-time experiment monitoring using shared memory."""

import json
import mmap
import os
import struct
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class ExperimentMetrics:
    """Real-time metrics for an experiment."""
    agent_a_model: str = ""
    agent_b_model: str = ""
    total_conversations: int = 0
    completed_conversations: int = 0
    failed_conversations: int = 0
    turn_count: int = 0
    convergence_scores: List[float] = None
    token_count: int = 0
    messages_per_turn: Dict[int, int] = None
    
    def __post_init__(self):
        if self.convergence_scores is None:
            self.convergence_scores = []
        if self.messages_per_turn is None:
            self.messages_per_turn = {}


class SharedState:
    """Shared memory state for experiment monitoring.
    
    Uses /dev/shm for fast inter-process communication between
    the experiment runner and dashboard.
    """
    
    HEADER_SIZE = 16  # timestamp (8) + size (4) + version (4)
    MAX_SIZE = 1024 * 1024  # 1MB max
    VERSION = 1
    
    def __init__(self, experiment_id: str, create: bool = False):
        """Initialize shared state.
        
        Args:
            experiment_id: Unique experiment identifier
            create: Whether to create new shared memory (True) or attach to existing (False)
        """
        self.experiment_id = experiment_id
        
        # Use platform-appropriate shared memory location
        if sys.platform == "darwin":  # macOS
            # Use /tmp for macOS (or could use ~/Library/Caches/)
            self.shm_path = Path(f"/tmp/pidgin_{experiment_id}")
        else:  # Linux
            self.shm_path = Path(f"/dev/shm/pidgin_{experiment_id}")
        
        self.fd = None
        self.mm = None
        
        if create:
            self._create()
        else:
            self._attach()
    
    def _create(self):
        """Create new shared memory segment."""
        # Remove if exists
        if self.shm_path.exists():
            self.shm_path.unlink()
        
        # Create file
        self.fd = os.open(str(self.shm_path), os.O_CREAT | os.O_RDWR)
        os.ftruncate(self.fd, self.MAX_SIZE)
        
        # Memory map
        self.mm = mmap.mmap(self.fd, self.MAX_SIZE)
        
        # Initialize with empty data
        self._write_data({
            'status': 'initializing',
            'models': {},
            'metrics': asdict(ExperimentMetrics()),
            'messages': [],
            'events': []
        })
    
    def _attach(self):
        """Attach to existing shared memory segment."""
        if not self.shm_path.exists():
            raise FileNotFoundError(f"Shared memory {self.shm_path} not found")
        
        self.fd = os.open(str(self.shm_path), os.O_RDWR)
        self.mm = mmap.mmap(self.fd, self.MAX_SIZE)
    
    def _write_data(self, data: Dict[str, Any]):
        """Write data to shared memory."""
        # Serialize to JSON
        json_data = json.dumps(data).encode('utf-8')
        
        if len(json_data) + self.HEADER_SIZE > self.MAX_SIZE:
            raise ValueError("Data too large for shared memory")
        
        # Write header
        timestamp = int(time.time() * 1000000)  # microseconds
        self.mm.seek(0)
        self.mm.write(struct.pack('<QII', timestamp, len(json_data), self.VERSION))
        
        # Write data
        self.mm.write(json_data)
        self.mm.flush()
    
    def _read_data(self) -> Dict[str, Any]:
        """Read data from shared memory."""
        self.mm.seek(0)
        
        # Read header
        header = self.mm.read(self.HEADER_SIZE)
        timestamp, size, version = struct.unpack('<QII', header)
        
        if version != self.VERSION:
            raise ValueError(f"Version mismatch: expected {self.VERSION}, got {version}")
        
        # Read data
        json_data = self.mm.read(size)
        return json.loads(json_data.decode('utf-8'))
    
    def set_status(self, status: str, error: Optional[str] = None):
        """Update experiment status."""
        data = self._read_data()
        data['status'] = status
        if error:
            data['error'] = error
        data['last_update'] = time.time()
        self._write_data(data)
    
    def get_status(self) -> str:
        """Get current experiment status."""
        data = self._read_data()
        return data.get('status', 'unknown')
    
    def set_models(self, agent_a: str, agent_b: str):
        """Set the models being used."""
        data = self._read_data()
        data['models'] = {
            'agent_a': agent_a,
            'agent_b': agent_b
        }
        self._write_data(data)
    
    def update_conversation_count(self, total: int, completed: int, failed: int = 0):
        """Update conversation progress."""
        data = self._read_data()
        if 'metrics' not in data:
            data['metrics'] = asdict(ExperimentMetrics())
        
        data['metrics']['total_conversations'] = total
        data['metrics']['completed_conversations'] = completed
        data['metrics']['failed_conversations'] = failed
        data['last_update'] = time.time()
        self._write_data(data)
    
    def add_message(self, role: str, content: str, turn: int):
        """Add a new message to the buffer."""
        data = self._read_data()
        if 'messages' not in data:
            data['messages'] = []
        
        # Keep only last 20 messages
        data['messages'].append({
            'role': role,
            'content': content[:200],  # Truncate for space
            'turn': turn,
            'timestamp': time.time()
        })
        
        if len(data['messages']) > 20:
            data['messages'] = data['messages'][-20:]
        
        self._write_data(data)
    
    def update_metrics(self, turn_count: int, convergence: Optional[float] = None,
                      tokens: Optional[int] = None):
        """Update experiment metrics."""
        data = self._read_data()
        if 'metrics' not in data:
            data['metrics'] = asdict(ExperimentMetrics())
        
        data['metrics']['turn_count'] = turn_count
        
        if convergence is not None:
            if 'convergence_scores' not in data['metrics']:
                data['metrics']['convergence_scores'] = []
            data['metrics']['convergence_scores'].append(convergence)
            # Keep only last 100 scores
            if len(data['metrics']['convergence_scores']) > 100:
                data['metrics']['convergence_scores'] = data['metrics']['convergence_scores'][-100:]
        
        if tokens is not None:
            data['metrics']['token_count'] = data['metrics'].get('token_count', 0) + tokens
        
        data['last_update'] = time.time()
        self._write_data(data)
    
    def get_all_data(self) -> Dict[str, Any]:
        """Get all shared state data."""
        return self._read_data()
    
    def get_metrics(self) -> Optional[ExperimentMetrics]:
        """Get experiment metrics."""
        data = self._read_data()
        if 'metrics' in data:
            metrics_dict = data['metrics']
            # Handle the models from the top-level data
            if 'models' in data:
                metrics_dict['agent_a_model'] = data['models'].get('agent_a', '')
                metrics_dict['agent_b_model'] = data['models'].get('agent_b', '')
            return ExperimentMetrics(**metrics_dict)
        return None
    
    def cleanup(self):
        """Clean up shared memory."""
        if self.mm:
            self.mm.close()
        if self.fd:
            os.close(self.fd)
        if self.shm_path.exists():
            self.shm_path.unlink()
    
    def close(self):
        """Close shared memory without removing it."""
        if self.mm:
            self.mm.close()
        if self.fd:
            os.close(self.fd)
    
    @classmethod
    def exists(cls, experiment_id: str) -> bool:
        """Check if shared state exists for an experiment."""
        if sys.platform == "darwin":  # macOS
            shm_path = Path(f"/tmp/pidgin_{experiment_id}")
        else:  # Linux
            shm_path = Path(f"/dev/shm/pidgin_{experiment_id}")
        return shm_path.exists()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
