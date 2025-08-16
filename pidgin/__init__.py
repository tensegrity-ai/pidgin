"""Pidgin - AI conversation research tool"""

__version__ = "0.1.0"

# Analysis exports
from .analysis import ConvergenceCalculator

# Config exports
from .config import (
    Config,
    get_model_config,
    get_system_prompts,
)

# Core exports
from .core import EventBus
from .core.conductor import Conductor

# IO exports
from .io import OutputManager, get_logger

# Metrics exports
from .metrics import (
    MetricsCalculator,
    calculate_structural_similarity,
    calculate_turn_metrics,
)

# UI exports
from .ui import ChatDisplay, DisplayFilter, TailDisplay

__all__ = [
    # Version
    "__version__",
    # Core
    "Conductor",
    "EventBus",
    # Analysis
    "ConvergenceCalculator",
    # Metrics
    "calculate_turn_metrics",
    "calculate_structural_similarity",
    "MetricsCalculator",
    # UI
    "DisplayFilter",
    "TailDisplay",
    "ChatDisplay",
    # Config
    "Config",
    "get_model_config",
    "get_system_prompts",
    # IO
    "OutputManager",
    "get_logger",
]
