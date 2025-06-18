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
    
    # Prompt configuration (matching CLI)
    custom_prompt: Optional[str] = None  # Custom prompt or path to .md file
    dimensions: Optional[str] = None  # Dimensional prompt specification
    
    # Experiment parameters
    max_turns: int = 50  # Match CLI default
    repetitions: int = 10
    
    # Temperature settings (matching CLI)
    temperature: Optional[float] = None  # Temperature for both models
    temperature_a: Optional[float] = None  # Override for model A
    temperature_b: Optional[float] = None  # Override for model B
    
    # Awareness levels (matching CLI)
    awareness: str = 'basic'  # Default for both agents
    awareness_a: Optional[str] = None  # Override for agent A
    awareness_b: Optional[str] = None  # Override for agent B
    
    # Parallel execution
    max_parallel: Optional[int] = None  # None = auto-calculate based on providers
    
    # Turn control
    first_speaker: str = 'agent_a'  # Alternates per repetition for fairness
    
    # Agent capabilities
    choose_names: bool = False
    
    # Convergence settings
    convergence_threshold: Optional[float] = None  # Stop at threshold
    convergence_action: str = 'continue'  # 'stop' or 'warn'
    
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
        
        # Validate awareness levels (matching CLI choices)
        valid_awareness = ('none', 'basic', 'firm', 'research')
        
        if self.awareness not in valid_awareness:
            errors.append(f"awareness must be one of: {', '.join(valid_awareness)}")
        
        if self.awareness_a and self.awareness_a not in valid_awareness:
            errors.append(f"awareness_a must be one of: {', '.join(valid_awareness)}")
        
        if self.awareness_b and self.awareness_b not in valid_awareness:
            errors.append(f"awareness_b must be one of: {', '.join(valid_awareness)}")
        
        if self.convergence_action not in ('stop', 'warn', 'continue'):
            errors.append("convergence_action must be 'stop', 'warn', or 'continue'")
        
        if self.convergence_threshold is not None:
            if not 0 <= self.convergence_threshold <= 1:
                errors.append("convergence_threshold must be between 0 and 1")
        
        if self.temperature is not None:
            if not 0 <= self.temperature <= 2:
                errors.append("temperature must be between 0 and 2")
                
        if self.temperature_a is not None:
            if not 0 <= self.temperature_a <= 2:
                errors.append("temperature_a must be between 0 and 2")
        
        if self.temperature_b is not None:
            if not 0 <= self.temperature_b <= 2:
                errors.append("temperature_b must be between 0 and 2")
        
        return errors


