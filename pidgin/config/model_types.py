"""Model configuration types.

This module defines the ModelConfig dataclass separately from models.py
to avoid circular import issues.
"""

from dataclasses import dataclass
from typing import List, Literal, Optional


@dataclass
class ModelConfig:
    """Configuration for a model based on actual API data."""

    model_id: str  # Exact model ID from API
    display_name: str  # Display name from API (if available)
    aliases: List[str]  # Convenient aliases for CLI
    provider: Literal["anthropic", "openai", "google", "xai", "local", "silent"]
    context_window: int  # Actual context window size
    created_at: Optional[str] = None  # From API response
    deprecated: bool = False
    notes: Optional[str] = None
    # Pricing information (per million tokens in USD)
    input_cost_per_million: Optional[float] = None
    output_cost_per_million: Optional[float] = None
    # For providers with caching support (e.g., Anthropic)
    supports_caching: bool = False
    cache_read_cost_per_million: Optional[float] = None
    cache_write_cost_per_million: Optional[float] = None
    # Track when pricing was last updated
    pricing_updated: Optional[str] = None  # ISO date string
    # Whether this model is curated (recommended for default view)
    curated: bool = False
    # Whether this model is stable (production-ready, not experimental/preview)
    stable: bool = False
