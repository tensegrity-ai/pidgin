"""Unified metrics system for conversation analysis."""

from .optimized_calculator import OptimizedMetricsCalculator as MetricsCalculator
from .display import (
    calculate_turn_metrics,
    calculate_structural_similarity,
    update_phase_detection,
    count_emojis
)
from .constants import (
    HEDGE_WORDS,
    AGREEMENT_MARKERS,
    DISAGREEMENT_MARKERS,
    POLITENESS_MARKERS,
    FIRST_PERSON_SINGULAR,
    FIRST_PERSON_PLURAL,
    SECOND_PERSON,
    ARROWS,
    MATH_SYMBOLS,
    BOX_DRAWING,
    BULLETS,
    EMOJI_PATTERN,
    ARROW_PATTERN,
    MATH_PATTERN
)

__all__ = [
    # Main calculator
    'MetricsCalculator',
    
    # Display functions
    'calculate_turn_metrics',
    'calculate_structural_similarity', 
    'update_phase_detection',
    'count_emojis',
    
    # Constants (for reference)
    'HEDGE_WORDS',
    'AGREEMENT_MARKERS',
    'DISAGREEMENT_MARKERS',
    'POLITENESS_MARKERS',
    'FIRST_PERSON_SINGULAR',
    'FIRST_PERSON_PLURAL',
    'SECOND_PERSON',
    'ARROWS',
    'MATH_SYMBOLS',
    'BOX_DRAWING',
    'BULLETS',
    'EMOJI_PATTERN',
    'ARROW_PATTERN',
    'MATH_PATTERN',
]