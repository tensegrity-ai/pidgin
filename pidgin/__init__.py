"""Pidgin - AI conversation research tool"""

__version__ = "0.1.0"

# Core exports
from .core import (
    Conductor,
    EventBus,
    Router,
    Agent,
    Message,
    Conversation,
)

# Analysis exports
from .analysis import (
    ConvergenceCalculator,
)

# Metrics exports
from .metrics import (
    calculate_turn_metrics,
    calculate_structural_similarity,
    MetricsCalculator,
)

# UI exports
from .ui import (
    DisplayFilter,
    EventLogger,
)

# Config exports
from .config import (
    Config,
    get_config,
    load_config,
    get_model_config,
    get_system_prompts,
    DimensionalPromptGenerator,
)

# IO exports
from .io import (
    OutputManager,
    TranscriptManager,
    get_logger,
)

__all__ = [
    # Version
    '__version__',
    
    # Core
    'Conductor',
    'EventBus',
    'Router',
    'Agent',
    'Message',
    'Conversation',
    
    # Analysis
    'ConvergenceCalculator',
    
    # Metrics
    'calculate_turn_metrics',
    'calculate_structural_similarity',
    'MetricsCalculator',
    
    # UI
    'DisplayFilter',
    'EventLogger',
    
    # Config
    'Config',
    'get_config',
    'load_config',
    'get_model_config',
    'get_system_prompts',
    'DimensionalPromptGenerator',
    
    # IO
    'OutputManager',
    'TranscriptManager',
    'get_logger',
]
