"""Core experiment management."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid

from pidgin.llm.base import LLM


class ExperimentStatus(str, Enum):
    """Experiment status."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MediationLevel(str, Enum):
    """Mediation level for experiments."""
    FULL = "full"  # Human approves every message
    LIGHT = "light"  # Human can intervene anytime
    OBSERVE = "observe"  # Watch only, no intervention
    AUTO = "auto"  # Fully autonomous


@dataclass
class ExperimentConfig:
    """Configuration for an experiment."""
    name: str
    max_turns: int = 100
    mediation_level: MediationLevel = MediationLevel.OBSERVE
    
    # Compression settings
    compression_enabled: bool = False
    compression_start_turn: Optional[int] = None
    compression_rate: float = 0.1  # Increase compression by 10% each phase
    
    # Meditation settings
    meditation_mode: bool = False
    meditation_style: str = "wandering"  # wandering, focused, recursive, deep
    basin_detection: bool = False
    
    # Other settings
    allow_parallel_turns: bool = False
    save_frequency: int = 5  # Save every N turns
    
    def __post_init__(self):
        # Convert string to enum if needed
        if isinstance(self.mediation_level, str):
            self.mediation_level = MediationLevel(self.mediation_level)


@dataclass
class ExperimentMetrics:
    """Metrics tracked during an experiment."""
    total_turns: int = 0
    total_tokens: int = 0
    compression_ratio: float = 1.0
    symbols_emerged: List[str] = field(default_factory=list)
    basin_reached: bool = False
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get experiment duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class Experiment:
    """Represents an AI communication experiment."""
    config: ExperimentConfig
    llms: List[LLM]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ExperimentStatus = ExperimentStatus.CREATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    metrics: ExperimentMetrics = field(default_factory=ExperimentMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime state
    current_turn: int = 0
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    compression_active: bool = False
    
    def __post_init__(self):
        # Validate configuration
        if self.config.meditation_mode and len(self.llms) != 1:
            raise ValueError("Meditation mode requires exactly one LLM")
        
        if not self.config.meditation_mode and len(self.llms) < 2:
            raise ValueError("Regular experiments require at least 2 LLMs")
        
        if self.config.compression_enabled and not self.config.compression_start_turn:
            self.config.compression_start_turn = 20  # Default
    
    @property
    def is_active(self) -> bool:
        """Check if experiment is currently active."""
        return self.status in [ExperimentStatus.RUNNING, ExperimentStatus.PAUSED]
    
    @property
    def can_start(self) -> bool:
        """Check if experiment can be started."""
        return self.status == ExperimentStatus.CREATED
    
    @property
    def can_resume(self) -> bool:
        """Check if experiment can be resumed."""
        return self.status == ExperimentStatus.PAUSED
    
    def start(self):
        """Start the experiment."""
        if not self.can_start:
            raise ValueError(f"Cannot start experiment in {self.status} status")
        
        self.status = ExperimentStatus.RUNNING
        self.metrics.start_time = datetime.utcnow()
    
    def pause(self):
        """Pause the experiment."""
        if self.status != ExperimentStatus.RUNNING:
            raise ValueError(f"Cannot pause experiment in {self.status} status")
        
        self.status = ExperimentStatus.PAUSED
    
    def resume(self):
        """Resume the experiment."""
        if not self.can_resume:
            raise ValueError(f"Cannot resume experiment in {self.status} status")
        
        self.status = ExperimentStatus.RUNNING
    
    def complete(self):
        """Mark experiment as completed."""
        self.status = ExperimentStatus.COMPLETED
        self.metrics.end_time = datetime.utcnow()
    
    def fail(self, error: Optional[str] = None):
        """Mark experiment as failed."""
        self.status = ExperimentStatus.FAILED
        self.metrics.end_time = datetime.utcnow()
        if error:
            self.metadata["error"] = error
    
    def cancel(self):
        """Cancel the experiment."""
        self.status = ExperimentStatus.CANCELLED
        self.metrics.end_time = datetime.utcnow()
    
    def should_activate_compression(self) -> bool:
        """Check if compression should be activated."""
        return (
            self.config.compression_enabled and
            not self.compression_active and
            self.current_turn >= self.config.compression_start_turn
        )
    
    def add_turn(self, turn_data: Dict[str, Any]):
        """Add a turn to the conversation."""
        self.current_turn += 1
        self.metrics.total_turns = self.current_turn
        
        # Add to history
        turn_data["turn"] = self.current_turn
        turn_data["timestamp"] = datetime.utcnow().isoformat()
        self.conversation_history.append(turn_data)
        
        # Check compression activation
        if self.should_activate_compression():
            self.compression_active = True
            self.metadata["compression_activated_turn"] = self.current_turn
    
    def get_next_speaker(self) -> LLM:
        """Get the next LLM to speak."""
        if self.config.meditation_mode:
            return self.llms[0]
        
        # Simple round-robin for now
        # In meditation mode, it's always the same LLM
        return self.llms[self.current_turn % len(self.llms)]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert experiment to dictionary."""
        return {
            "id": self.id,
            "name": self.config.name,
            "status": self.status,
            "config": {
                "max_turns": self.config.max_turns,
                "mediation_level": self.config.mediation_level,
                "compression_enabled": self.config.compression_enabled,
                "compression_start_turn": self.config.compression_start_turn,
                "meditation_mode": self.config.meditation_mode,
                "meditation_style": self.config.meditation_style,
            },
            "llms": [
                {
                    "model": llm.config.model,
                    "archetype": llm.config.archetype_config.name,
                    "provider": llm.provider,
                }
                for llm in self.llms
            ],
            "metrics": {
                "total_turns": self.metrics.total_turns,
                "total_tokens": self.metrics.total_tokens,
                "compression_ratio": self.metrics.compression_ratio,
                "duration": self.metrics.duration,
            },
            "created_at": self.created_at.isoformat(),
            "current_turn": self.current_turn,
            "metadata": self.metadata,
        }