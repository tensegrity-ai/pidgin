"""Model configuration types.

This module defines the ModelConfig dataclass separately from models.py
to avoid circular import issues.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


@dataclass
class ModelConfig:
    """Configuration for a model based on actual API data."""

    model_id: str  # Exact model ID from API
    display_name: str  # Display name from API (if available)
    aliases: List[str]  # Convenient aliases for CLI
    provider: Literal["anthropic", "openai", "google", "xai", "local"]
    context_window: int  # Actual context window size
    created_at: Optional[str] = None  # From API response
    deprecated: bool = False
    notes: Optional[str] = None