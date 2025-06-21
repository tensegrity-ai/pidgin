"""Analysis modules for pidgin."""

from .convergence import ConvergenceCalculator
from .enrichment import MetricsEnricher

# Re-export from new metrics module for backward compatibility
from ..metrics import calculate_turn_metrics, calculate_structural_similarity

__all__ = [
    'ConvergenceCalculator',
    'MetricsEnricher',
    'calculate_turn_metrics',
    'calculate_structural_similarity',
]
