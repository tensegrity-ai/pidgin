"""Analysis and metrics for pidgin."""

from .convergence import ConvergenceCalculator
from .metrics import calculate_turn_metrics, calculate_structural_similarity
from .context_manager import ContextWindowManager

__all__ = [
    'ConvergenceCalculator',
    'calculate_turn_metrics',
    'calculate_structural_similarity',
    'ContextWindowManager',
]