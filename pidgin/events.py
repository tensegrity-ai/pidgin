"""Event-sourced data pipeline for Pidgin experiments."""

import json
import time
import uuid
import gzip
import shutil
import sqlite3
import hashlib
import traceback
from enum import Enum
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Any, Optional, List, Callable, Set, Dict, Tuple


class EventType(Enum):
    """All possible events in a Pidgin experiment."""
    
    # Experiment lifecycle
    EXPERIMENT_STARTED = "experiment.started"
    EXPERIMENT_COMPLETED = "experiment.completed"
    EXPERIMENT_FAILED = "experiment.failed"
    
    # Turn flow
    TURN_STARTED = "turn.started"
    PROMPT_SENT = "prompt.sent"
    RESPONSE_STARTED = "response.started"
    RESPONSE_STREAMING = "response.streaming"
    RESPONSE_COMPLETED = "response.completed"
    RESPONSE_INTERRUPTED = "response.interrupted"
    TURN_COMPLETED = "turn.completed"
    
    # Interventions
    PAUSE_REQUESTED = "pause.requested"
    CHECKPOINT_SAVED = "checkpoint.saved"
    CONVERSATION_RESUMED = "conversation.resumed"
    CONDUCTOR_INTERVENTION = "conductor.intervention"
    
    # Detections
    ATTRACTOR_DETECTED = "attractor.detected"
    CONVERGENCE_MEASURED = "convergence.measured"
    CONTEXT_USAGE = "context.usage"
    RATE_LIMIT_WARNING = "rate_limit.warning"
    
    # Provider events
    API_CALL_STARTED = "api.call.started"
    API_CALL_COMPLETED = "api.call.completed"
    API_CALL_FAILED = "api.call.failed"
    STREAM_CHUNK_RECEIVED = "stream.chunk.received"


@dataclass
class Event:
    """A single event in the experiment timeline."""
    
    id: str  # UUID for each event
    type: EventType
    experiment_id: str
    timestamp: float
    turn_number: Optional[int]
    agent_id: Optional[str]
    data: Dict[str, Any]
    version: int = 1  # Schema version for future evolution
    
    def to_json_line(self) -> str:
        """Serialize for JSONL storage."""
        return json.dumps({
            'v': self.version,  # Short key to save space
            'id': self.id,
            'type': self.type.value,
            'experiment_id': self.experiment_id,
            'timestamp': self.timestamp,
            'turn_number': self.turn_number,
            'agent_id': self.agent_id,
            'data': self.data
        })
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Deserialize from JSON dict."""
        return cls(
            id=data['id'],
            type=EventType(data['type']),
            experiment_id=data['experiment_id'],
            timestamp=data['timestamp'],
            turn_number=data.get('turn_number'),
            agent_id=data.get('agent_id'),
            data=data['data'],
            version=data.get('v', 1)  # Handle old events without version
        )


class PrivacyFilter:
    """Filter PII from events before storage/export."""
    
    def __init__(self, 
                 remove_content: bool = False,
                 hash_models: bool = False,
                 redact_patterns: Optional[Set[str]] = None):
        self.remove_content = remove_content
        self.hash_models = hash_models
        self.redact_patterns = redact_patterns or set()
        
    def filter_event(self, event: Event) -> Event:
        """Apply privacy filters to an event."""
        filtered_data = event.data.copy()
        
        # Remove message content if configured
        if self.remove_content and 'content' in filtered_data:
            original_content = filtered_data['content']
            filtered_data['content'] = "[REDACTED]"
            # Keep a hash for deduplication/analysis
            filtered_data['content_hash'] = hashlib.sha256(
                original_content.encode()
            ).hexdigest()[:16]
            filtered_data['content_length'] = len(original_content)
        
        # Hash model names if configured
        if self.hash_models:
            for key in ['model', 'model_a', 'model_b']:
                if key in filtered_data:
                    filtered_data[f'{key}_hash'] = hashlib.sha256(
                        filtered_data[key].encode()
                    ).hexdigest()[:8]
                    filtered_data[key] = f"model_{filtered_data[f'{key}_hash']}"
        
        # Apply custom redaction patterns
        if self.redact_patterns:
            content_fields = ['content', 'initial_prompt', 'intervention_content']
            for field in content_fields:
                if field in filtered_data and isinstance(filtered_data[field], str):
                    for pattern in self.redact_patterns:
                        filtered_data[field] = filtered_data[field].replace(
                            pattern, "[REDACTED]"
                        )
        
        return Event(
            id=event.id,
            type=event.type,
            experiment_id=event.experiment_id,
            timestamp=event.timestamp,
            turn_number=event.turn_number,
            agent_id=event.agent_id,
            data=filtered_data,
            version=event.version
        )
    
    def filter_experiment(self, events: List[Event]) -> List[Event]:
        """Filter all events in an experiment."""
        return [self.filter_event(event) for event in events]


class EventStore:
    """Manages event persistence and querying."""
    
    def __init__(self, 
                 data_dir: Path,
                 privacy_filter: Optional[PrivacyFilter] = None,
                 compress_completed: bool = True):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.privacy_filter = privacy_filter
        self.compress_completed = compress_completed
        
        # Initialize SQLite for indexing
        self.db_path = self.data_dir / "events.db"
        self._init_db()
        
        # Real-time subscribers
        self.subscribers: List[Callable[[Event], None]] = []
        
    def _init_db(self):
        """Create indexes for common queries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    turn_number INTEGER,
                    agent_id TEXT,
                    data_json TEXT NOT NULL,
                    
                    -- Extracted fields for querying
                    convergence_score REAL,
                    tokens_used INTEGER,
                    message_length INTEGER,
                    interrupted BOOLEAN,
                    attractor_type TEXT
                )
            """)
            
            # Indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_turn ON events(experiment_id, turn_number)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type_time ON events(type, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_convergence ON events(experiment_id, convergence_score)")
    
    def append(self, event: Event) -> None:
        """Append event to both JSONL and index."""
        # Apply privacy filter if configured
        filtered_event = event
        if self.privacy_filter:
            filtered_event = self.privacy_filter.filter_event(event)
        
        # 1. Write to experiment's event log
        event_file = self.data_dir / f"{event.experiment_id}.events.jsonl"
        with open(event_file, 'a') as f:
            f.write(filtered_event.to_json_line() + '\n')
        
        # 2. Update SQLite indexes with filtered data
        self._index_event(filtered_event)
        
        # 3. Notify subscribers with original event
        for subscriber in self.subscribers:
            try:
                subscriber(event)
            except Exception as e:
                print(f"Subscriber error: {e}")
        
        # 4. Auto-compress if experiment completed
        if self.compress_completed and event.type == EventType.EXPERIMENT_COMPLETED:
            self._compress_experiment(event.experiment_id)
    
    def _index_event(self, event: Event):
        """Extract queryable fields and index them."""
        with sqlite3.connect(self.db_path) as conn:
            # Extract common fields based on event type
            extracted = {
                'convergence_score': None,
                'tokens_used': None,
                'message_length': None,
                'interrupted': None,
                'attractor_type': None
            }
            
            if event.type == EventType.CONVERGENCE_MEASURED:
                extracted['convergence_score'] = event.data.get('score')
            elif event.type == EventType.RESPONSE_COMPLETED:
                extracted['tokens_used'] = event.data.get('tokens')
                extracted['message_length'] = event.data.get('length')
            elif event.type == EventType.RESPONSE_INTERRUPTED:
                extracted['interrupted'] = True
            elif event.type == EventType.ATTRACTOR_DETECTED:
                extracted['attractor_type'] = event.data.get('type')
            
            conn.execute("""
                INSERT INTO events 
                (id, type, experiment_id, timestamp, turn_number, agent_id, 
                 data_json, convergence_score, tokens_used, message_length, 
                 interrupted, attractor_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.id, event.type.value, event.experiment_id, 
                event.timestamp, event.turn_number, event.agent_id,
                json.dumps(event.data), 
                extracted['convergence_score'], extracted['tokens_used'],
                extracted['message_length'], extracted['interrupted'],
                extracted['attractor_type']
            ))
    
    def _compress_experiment(self, experiment_id: str):
        """Compress completed experiment to save space."""
        event_file = self.data_dir / f"{experiment_id}.events.jsonl"
        gz_file = self.data_dir / f"{experiment_id}.events.jsonl.gz"
        
        if not event_file.exists():
            return
        
        # Get file size before compression
        original_size = event_file.stat().st_size
        
        # Compress
        with open(event_file, 'rb') as f_in:
            with gzip.open(gz_file, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove uncompressed version
        event_file.unlink()
        
        # Log compression stats
        compressed_size = gz_file.stat().st_size
        ratio = compressed_size / original_size if original_size > 0 else 0
        print(f"Compressed {experiment_id}: {ratio:.1%} of original size")
    
    def replay_experiment(self, experiment_id: str) -> List[Event]:
        """Replay all events for an experiment in order."""
        # Try compressed first
        gz_file = self.data_dir / f"{experiment_id}.events.jsonl.gz"
        if gz_file.exists():
            with gzip.open(gz_file, 'rt') as f:
                lines = f.readlines()
        else:
            # Fall back to uncompressed
            event_file = self.data_dir / f"{experiment_id}.events.jsonl"
            if event_file.exists():
                with open(event_file, 'r') as f:
                    lines = f.readlines()
            else:
                return []
        
        # Parse events
        events = []
        for line in lines:
            if line.strip():  # Skip empty lines
                data = json.loads(line)
                events.append(Event.from_dict(data))
        
        # Ensure timestamp ordering
        return sorted(events, key=lambda e: e.timestamp)
    
    def query_convergence_trend(self, experiment_id: str) -> List[Tuple]:
        """Get convergence scores over time."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("""
                SELECT turn_number, convergence_score, timestamp
                FROM events
                WHERE experiment_id = ? 
                  AND type = 'convergence.measured'
                  AND convergence_score IS NOT NULL
                ORDER BY turn_number
            """, (experiment_id,)).fetchall()
    
    def query_interruptions(self, experiment_id: str) -> List[Tuple]:
        """Get all interruption events."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("""
                SELECT turn_number, agent_id, timestamp, data_json
                FROM events
                WHERE experiment_id = ? 
                  AND type = 'response.interrupted'
                ORDER BY timestamp
            """, (experiment_id,)).fetchall()
    
    def query_attractors(self, experiment_id: str) -> List[Tuple]:
        """Get all attractor detection events."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("""
                SELECT turn_number, attractor_type, timestamp, data_json
                FROM events
                WHERE experiment_id = ? 
                  AND type = 'attractor.detected'
                ORDER BY timestamp
            """, (experiment_id,)).fetchall()
    
    def get_experiment_summary(self, experiment_id: str) -> Dict[str, Any]:
        """Get summary statistics for an experiment."""
        with sqlite3.connect(self.db_path) as conn:
            # Get basic stats
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_events,
                    MIN(timestamp) as start_time,
                    MAX(timestamp) as end_time,
                    MAX(turn_number) as max_turn,
                    SUM(CASE WHEN type = 'response.interrupted' THEN 1 ELSE 0 END) as interruptions,
                    COUNT(DISTINCT CASE WHEN type = 'attractor.detected' THEN id END) as attractors
                FROM events
                WHERE experiment_id = ?
            """, (experiment_id,)).fetchone()
            
            # Get convergence stats
            convergence = conn.execute("""
                SELECT MAX(convergence_score) as max_convergence
                FROM events
                WHERE experiment_id = ? AND convergence_score IS NOT NULL
            """, (experiment_id,)).fetchone()
            
            return {
                'experiment_id': experiment_id,
                'total_events': stats[0],
                'duration': stats[2] - stats[1] if stats[1] and stats[2] else 0,
                'turns': stats[3] or 0,
                'interruptions': stats[4],
                'attractors': stats[5],
                'max_convergence': convergence[0] if convergence[0] else 0
            }
    
    def subscribe(self, callback: Callable[[Event], None]):
        """Subscribe to real-time event stream."""
        self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[Event], None]):
        """Unsubscribe from event stream."""
        if callback in self.subscribers:
            self.subscribers.remove(callback)


def create_event(event_type: EventType, 
                 experiment_id: str,
                 turn_number: Optional[int] = None,
                 agent_id: Optional[str] = None,
                 data: Optional[Dict[str, Any]] = None) -> Event:
    """Helper to create events with consistent IDs and timestamps."""
    return Event(
        id=uuid.uuid4().hex,
        type=event_type,
        experiment_id=experiment_id,
        timestamp=time.time(),
        turn_number=turn_number,
        agent_id=agent_id,
        data=data or {}
    )