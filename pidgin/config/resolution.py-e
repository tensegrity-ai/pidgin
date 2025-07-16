"""Configuration resolution utilities."""

from typing import Optional, Tuple


def resolve_temperatures(
    temperature: Optional[float], temp_a: Optional[float], temp_b: Optional[float]
) -> Tuple[Optional[float], Optional[float]]:
    """Resolve temperature settings for both agents.

    Args:
        temperature: General temperature for both agents
        temp_a: Specific temperature for agent A
        temp_b: Specific temperature for agent B

    Returns:
        Tuple of (temp_a, temp_b) with fallbacks applied
    """
    resolved_temp_a = temp_a if temp_a is not None else temperature
    resolved_temp_b = temp_b if temp_b is not None else temperature
    return resolved_temp_a, resolved_temp_b


def resolve_awareness_levels(
    awareness: str, awareness_a: Optional[str], awareness_b: Optional[str]
) -> Tuple[str, str]:
    """Resolve awareness levels for both agents.

    Args:
        awareness: General awareness level for both agents
        awareness_a: Specific awareness for agent A
        awareness_b: Specific awareness for agent B

    Returns:
        Tuple of (awareness_a, awareness_b) with fallbacks applied
    """
    resolved_awareness_a = awareness_a if awareness_a else awareness
    resolved_awareness_b = awareness_b if awareness_b else awareness
    return resolved_awareness_a, resolved_awareness_b
