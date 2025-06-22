# pidgin/experiments/shared_state.py
"""Shared state for real-time experiment monitoring using shared memory."""

import json
import mmap
import os
import struct
import time
from pathlib import Path
from typing import Dict, Any, Optional, List


class SharedState:
    """Shared memory state for experiment monitoring.
    
    Uses a simple fixed-size shared memory region for fast IPC.
    Structure:
    - 4 bytes: version number
    - 4 bytes: last update timestamp
    - 8192 bytes: JSON data (padded with nulls)
    """
    
    VERSION = 1
    HEADER_SIZE = 8  # version (4) + timestamp (4)
    DATA_SIZE = 8192
    TOTAL_SIZE = HEADER_SIZE + DATA_SIZE
    
    def __init__(self, experiment_id: str, create: bool = False):
        """Initialize shared state.
        
        Args:
            experiment_id: Unique experiment identifier
            create: If True, create new shared memory; if False, attach to existing
        """
        self.experiment_id = experiment_id
        self.shm_name = f"/dev/shm/pidgin_{experiment_id}"
        self.fd = None
        self.mmap = None
        
        if create:
            self._create()
        else:
            self._attach()
    
    def _create(self):
        """Create new shared memory region."""
        # Remove existing file if present
        if os.path.exists(self.shm_name):
            os.unlink(self.shm_name)
            
        # Create and size the file
        self.fd = os.open(self.shm_name, os.O_CREAT | os.O_RDWR | os.O_EXCL, 0o644)
        os.ftruncate(self.fd, self.TOTAL_SIZE)
        
        # Memory map it
        self.mmap = mmap.mmap(self.fd, self.TOTAL_SIZE)
        
        # Initialize with empty data
        self._write_data({
            "status": "initializing",
            "status_message": "",
            "experiment_id": self.experiment_id,
            "models": {
                "agent_a": "unknown",
                "agent_b": "unknown"
            },
            "conversation_count": {
                "total": 0,
                "completed": 0
            },
            "current_conversation": "",
            "current_turn": 0,
            "metrics": {
                "convergence": [],
                "similarity": [],
                "vocabulary": [],
                "last_messages": []
            }
        })
    
    def _attach(self):
        """Attach to existing shared memory region."""
        if not os.path.exists(self.shm_name):
            raise FileNotFoundError(f"Shared memory {self.shm_name} does not exist")
            
        self.fd = os.open(self.shm_name, os.O_RDWR)
        self.mmap = mmap.mmap(self.fd, self.TOTAL_SIZE)
    
    def _write_data(self, data: Dict[str, Any]):
        """Write data to shared memory."""
        # Serialize to JSON
        json_bytes = json.dumps(data).encode('utf-8')
        
        # Ensure it fits
        if len(json_bytes) > self.DATA_SIZE:
            raise ValueError(f"Data too large: {len(json_bytes)} > {self.DATA_SIZE}")
        
        # Prepare header
        version = struct.pack('I', self.VERSION)
        timestamp = struct.pack('I', int(time.time()))
        
        # Write to memory
        self.mmap.seek(0)
        self.mmap.write(version)
        self.mmap.write(timestamp)
        self.mmap.write(json_bytes)
        
        # Pad with nulls
        padding = self.DATA_SIZE - len(json_bytes)
        if padding > 0:
            self.mmap.write(b'\x00' * padding)
        
        # Ensure written
        self.mmap.flush()
    
    def _read_data(self) -> Dict[str, Any]:
        """Read data from shared memory."""
        self.mmap.seek(0)
        
        # Read header
        version_bytes = self.mmap.read(4)
        timestamp_bytes = self.mmap.read(4)
        
        version = struct.unpack('I', version_bytes)[0]
        if version != self.VERSION:
            raise ValueError(f"Version mismatch: {version} != {self.VERSION}")
        
        # Read JSON data
        json_bytes = self.mmap.read(self.DATA_SIZE)
        
        # Find null terminator
        null_pos = json_bytes.find(b'\x00')
        if null_pos > 0:
            json_bytes = json_bytes[:null_pos]
        
        return json.loads(json_bytes.decode('utf-8'))
    
    def get_status(self) -> str:
        """Get current experiment status."""
        data = self._read_data()
        return data.get("status", "unknown")
    
    def set_status(self, status: str, error: Optional[str] = None):
        """Set experiment status.
        
        Args:
            status: One of: initializing, running, completed, failed
            error: Optional error message if failed
        """
        data = self._read_data()
        data["status"] = status
        data["status_message"] = error or ""
        self._write_data(data)
    
    def set_models(self, agent_a: str, agent_b: str):
        """Set model names."""
        data = self._read_data()
        data["models"] = {
            "agent_a": agent_a,
            "agent_b": agent_b
        }
        self._write_data(data)
    
    def update_conversation_count(self, total: int, completed: int):
        """Update conversation progress."""
        data = self._read_data()
        data["conversation_count"] = {
            "total": total,
            "completed": completed
        }
        self._write_data(data)
    
    def add_conversation_metrics(self,
                               turn: int,
                               convergence: float,
                               similarity: float,
                               vocabulary: float,
                               last_messages: List[Dict[str, str]],
                               conversation_id: Optional[str] = None):
        """Add metrics for current turn.
        
        Args:
            turn: Turn number
            convergence: Convergence score
            similarity: Structural similarity
            vocabulary: Vocabulary overlap
            last_messages: List of recent messages
            conversation_id: Optional conversation ID
        """
        data = self._read_data()
        
        # Update current state
        if conversation_id:
            data["current_conversation"] = conversation_id
        data["current_turn"] = turn
        
        # Append to metrics history (keep last 20)
        metrics = data.get("metrics", {})
        
        for key, value in [
            ("convergence", convergence),
            ("similarity", similarity),
            ("vocabulary", vocabulary)
        ]:
            if key not in metrics:
                metrics[key] = []
            metrics[key].append(value)
            # Keep only last 20
            metrics[key] = metrics[key][-20:]
        
        # Update last messages
        metrics["last_messages"] = last_messages[-6:]  # Keep last 6
        
        data["metrics"] = metrics
        self._write_data(data)
    
    def get_all_data(self) -> Dict[str, Any]:
        """Get all shared state data."""
        return self._read_data()
    
    def cleanup(self):
        """Clean up shared memory."""
        if self.mmap:
            self.mmap.close()
        if self.fd is not None:
            os.close(self.fd)
        
        # Only unlink if we created it
        if hasattr(self, '_created') and os.path.exists(self.shm_name):
            os.unlink(self.shm_name)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
