"""Analysis modules for pidgin."""

# Re-export from new metrics module for backward compatibility
from ..metrics import calculate_structural_similarity, calculate_turn_metrics
from .convergence import ConvergenceCalculator

__all__ = [
    "ConvergenceCalculator",
    "calculate_turn_metrics",
    "calculate_structural_similarity",
]
