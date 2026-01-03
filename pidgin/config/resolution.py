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
