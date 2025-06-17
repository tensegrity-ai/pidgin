"""Configuration types for experiments."""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


@dataclass
class ExperimentConfig:
    """Configuration for an experiment run."""
    
    # Required fields
    name: str
    agent_a_model: str
    agent_b_model: str
    initial_prompt: str = "Hello! Let's have a conversation."
    
    # Experiment parameters
    max_turns: int = 20
    repetitions: int = 10
    
    # Temperature settings
    temperature_a: Optional[float] = None
    temperature_b: Optional[float] = None
    
    # Parallel execution
    max_parallel: Optional[int] = None  # None = auto-calculate based on providers
    
    # Turn control
    first_speaker: str = 'agent_a'  # Alternates per repetition for fairness
    
    # Agent capabilities
    choose_names: bool = False
    awareness_a: str = 'basic'  # 'basic', 'enhanced', 'full'
    awareness_b: str = 'basic'
    
    # Convergence settings
    convergence_threshold: Optional[float] = None  # Stop at threshold
    convergence_action: str = 'continue'  # 'stop' or 'warn'
    
    # Output control
    save_transcripts: bool = True
    save_events: bool = True
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def get_conversation_config(self, repetition: int) -> Dict[str, Any]:
        """Get configuration for a specific conversation repetition.
        
        Args:
            repetition: 0-indexed repetition number
            
        Returns:
            Configuration dict for this specific conversation
        """
        config = self.dict()
        
        # Alternate first speaker for fairness
        if repetition % 2 == 1:
            config['first_speaker'] = 'agent_b'
        
        # Add repetition info
        config['repetition_number'] = repetition
        
        return config
    
    def validate(self) -> List[str]:
        """Validate configuration and return any errors."""
        errors = []
        
        if self.repetitions < 1:
            errors.append("repetitions must be at least 1")
        
        if self.max_turns < 1:
            errors.append("max_turns must be at least 1")
        
        if self.first_speaker not in ('agent_a', 'agent_b'):
            errors.append("first_speaker must be 'agent_a' or 'agent_b'")
        
        if self.awareness_a not in ('basic', 'enhanced', 'full'):
            errors.append("awareness_a must be 'basic', 'enhanced', or 'full'")
        
        if self.awareness_b not in ('basic', 'enhanced', 'full'):
            errors.append("awareness_b must be 'basic', 'enhanced', or 'full'")
        
        if self.convergence_action not in ('stop', 'warn', 'continue'):
            errors.append("convergence_action must be 'stop', 'warn', or 'continue'")
        
        if self.convergence_threshold is not None:
            if not 0 <= self.convergence_threshold <= 1:
                errors.append("convergence_threshold must be between 0 and 1")
        
        if self.temperature_a is not None:
            if not 0 <= self.temperature_a <= 2:
                errors.append("temperature_a must be between 0 and 2")
        
        if self.temperature_b is not None:
            if not 0 <= self.temperature_b <= 2:
                errors.append("temperature_b must be between 0 and 2")
        
        return errors


@dataclass
class BatchExperimentConfig:
    """Configuration for batch experiments with parameter sweeps."""
    
    name: str
    base_config: ExperimentConfig
    
    # Parameter sweeps (Phase 3)
    model_pairs: Optional[List[tuple]] = None
    temperature_sweep: Optional[List[float]] = None
    prompt_variations: Optional[List[str]] = None
    
    # Execution settings
    parallel_conversations: int = 1  # Phase 3: parallelization
    rate_limit_delay: float = 1.0  # Seconds between conversation starts
    
    def generate_experiments(self) -> List[ExperimentConfig]:
        """Generate individual experiment configs from batch config.
        
        For Phase 2, this just returns the base config.
        Phase 3 will implement parameter sweeps.
        """
        # Phase 2: Just return base config
        return [self.base_config]