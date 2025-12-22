"""Model configuration types for v2 schema.

This module defines the ModelConfig dataclass and nested types
for the v2 schema with explicit per-model capabilities.
"""

from dataclasses import dataclass, field
from typing import List, Literal, Optional


@dataclass
class ApiConfig:
    """Provider-specific API configuration."""

    model_id: str  # Exact identifier to send to API
    ollama_model: Optional[str] = None  # Ollama-specific model name
    api_version: Optional[str] = None  # API version string


@dataclass
class Capabilities:
    """Explicit model capabilities (no provider-level inheritance)."""

    streaming: bool
    vision: bool
    tool_calling: bool
    system_messages: bool
    extended_thinking: bool = False
    json_mode: bool = False
    prompt_caching: bool = False


@dataclass
class Limits:
    """Token limits for the model."""

    max_context_tokens: Optional[int]  # None = unlimited
    max_output_tokens: Optional[int] = None  # None = same as context or unlimited
    max_thinking_tokens: Optional[int] = None  # None = N/A or unlimited


@dataclass
class ParameterSpec:
    """Specification for a single parameter."""

    supported: bool
    range: Optional[List[float]] = None  # [min, max] if supported
    default: Optional[float] = None


@dataclass
class Parameters:
    """Supported parameters with validation ranges."""

    temperature: ParameterSpec = field(
        default_factory=lambda: ParameterSpec(supported=False)
    )
    top_p: ParameterSpec = field(default_factory=lambda: ParameterSpec(supported=False))
    top_k: ParameterSpec = field(default_factory=lambda: ParameterSpec(supported=False))


@dataclass
class Cost:
    """Pricing information in USD per million tokens."""

    input_per_1m_tokens: float
    output_per_1m_tokens: float
    currency: str = "USD"
    last_updated: Optional[str] = None  # ISO date
    cache_read_per_1m_tokens: Optional[float] = None
    cache_write_per_1m_tokens: Optional[float] = None


@dataclass
class Metadata:
    """Descriptive information about the model."""

    status: Literal["available", "preview", "deprecated"] = "available"
    curated: bool = False
    stable: bool = False
    release_date: Optional[str] = None  # ISO date
    deprecation_date: Optional[str] = None  # ISO date
    description: Optional[str] = None
    notes: Optional[str] = None
    size: Optional[str] = None  # For local models


@dataclass
class RateLimits:
    """API rate limits."""

    requests_per_minute: int
    tokens_per_minute: int


ProviderType = Literal[
    "anthropic", "openai", "google", "xai", "ollama", "local", "silent"
]


@dataclass
class ModelConfig:
    """Complete configuration for a model based on v2 schema."""

    # Required identity fields
    model_id: str
    provider: ProviderType
    display_name: str

    # Aliases for CLI
    aliases: List[str] = field(default_factory=list)

    # API configuration
    api: ApiConfig = field(default_factory=lambda: ApiConfig(model_id=""))

    # Explicit capabilities (no provider inheritance)
    capabilities: Capabilities = field(
        default_factory=lambda: Capabilities(
            streaming=True,
            vision=False,
            tool_calling=False,
            system_messages=True,
        )
    )

    # Token limits
    limits: Limits = field(default_factory=lambda: Limits(max_context_tokens=4096))

    # Parameter support
    parameters: Parameters = field(default_factory=Parameters)

    # Pricing (None for free/local models)
    cost: Optional[Cost] = None

    # Metadata
    metadata: Metadata = field(default_factory=Metadata)

    # Rate limits (None for local models)
    rate_limits: Optional[RateLimits] = None

    # === Convenience properties for backward compatibility ===

    @property
    def context_window(self) -> int:
        """Backward compatible access to context window."""
        return self.limits.max_context_tokens or 4096

    @property
    def input_cost_per_million(self) -> Optional[float]:
        """Backward compatible access to input cost."""
        return self.cost.input_per_1m_tokens if self.cost else None

    @property
    def output_cost_per_million(self) -> Optional[float]:
        """Backward compatible access to output cost."""
        return self.cost.output_per_1m_tokens if self.cost else None

    @property
    def supports_caching(self) -> bool:
        """Backward compatible access to caching support."""
        return self.capabilities.prompt_caching

    @property
    def cache_read_cost_per_million(self) -> Optional[float]:
        """Backward compatible access to cache read cost."""
        return self.cost.cache_read_per_1m_tokens if self.cost else None

    @property
    def cache_write_cost_per_million(self) -> Optional[float]:
        """Backward compatible access to cache write cost."""
        return self.cost.cache_write_per_1m_tokens if self.cost else None

    @property
    def curated(self) -> bool:
        """Backward compatible access to curated flag."""
        return self.metadata.curated

    @property
    def stable(self) -> bool:
        """Backward compatible access to stable flag."""
        return self.metadata.stable

    @property
    def deprecated(self) -> bool:
        """Backward compatible access to deprecated flag."""
        return self.metadata.status == "deprecated"

    @property
    def created_at(self) -> Optional[str]:
        """Backward compatible access to release date."""
        return self.metadata.release_date

    @property
    def notes(self) -> Optional[str]:
        """Backward compatible access to notes."""
        return self.metadata.notes

    @property
    def pricing_updated(self) -> Optional[str]:
        """Backward compatible access to pricing update date."""
        return self.cost.last_updated if self.cost else None
