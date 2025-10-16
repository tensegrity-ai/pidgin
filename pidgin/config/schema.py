"""Pydantic schema for configuration validation."""

from typing import Dict, Literal, Optional, cast

from pydantic import BaseModel, Field, field_validator, model_validator

from ..metrics.constants import (
    DEFAULT_CONVERGENCE_ACTION,
    DEFAULT_CONVERGENCE_PROFILE,
    DEFAULT_CONVERGENCE_THRESHOLD,
    ConvergenceProfiles,
)


class ConvergenceWeights(BaseModel):
    """Schema for convergence weight validation."""

    content: float = Field(ge=0, le=1)
    structure: float = Field(ge=0, le=1)
    sentences: float = Field(ge=0, le=1)
    length: float = Field(ge=0, le=1)
    punctuation: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_sum(self) -> "ConvergenceWeights":
        """Ensure weights sum to 1.0 (with floating point tolerance)."""
        total = (
            self.content
            + self.structure
            + self.sentences
            + self.length
            + self.punctuation
        )
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"Convergence weights must sum to 1.0, but got {total:.3f}"
            )
        return self


class ConversationConfig(BaseModel):
    """Schema for conversation configuration."""

    convergence_threshold: float = Field(
        default=DEFAULT_CONVERGENCE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Threshold for high convergence detection",
    )
    convergence_action: Literal["stop", "warn"] = Field(
        default=cast(Literal["stop", "warn"], DEFAULT_CONVERGENCE_ACTION),
        description="Action to take on high convergence",
    )
    convergence_profile: str = Field(
        default=DEFAULT_CONVERGENCE_PROFILE,
        description="Convergence profile name or 'custom'",
    )

    @field_validator("convergence_profile")
    @classmethod
    def validate_profile(cls, v: str) -> str:
        """Validate convergence profile name."""
        valid_profiles = [*list(ConvergenceProfiles.__dict__.values()), "custom"]
        if v not in valid_profiles:
            raise ValueError(
                f"Invalid convergence profile '{v}'. "
                f"Must be one of: {', '.join(valid_profiles)}"
            )
        return v


class ConvergenceConfig(BaseModel):
    """Schema for convergence configuration."""

    profile: str = Field(
        default=DEFAULT_CONVERGENCE_PROFILE, description="Active convergence profile"
    )
    custom_weights: Optional[ConvergenceWeights] = Field(
        default=None, description="Custom weights when profile is 'custom'"
    )

    @field_validator("profile")
    @classmethod
    def validate_profile(cls, v: str) -> str:
        """Validate convergence profile name."""
        valid_profiles = [*list(ConvergenceProfiles.__dict__.values()), "custom"]
        if v not in valid_profiles:
            raise ValueError(
                f"Invalid convergence profile '{v}'. "
                f"Must be one of: {', '.join(valid_profiles)}"
            )
        return v


class ContextManagementConfig(BaseModel):
    """Schema for context management configuration."""

    enabled: bool = Field(default=True)
    warning_threshold: int = Field(
        default=80,
        ge=0,
        le=100,
        description="Warn at this percentage of context capacity",
    )
    auto_pause_threshold: int = Field(
        default=95,
        ge=0,
        le=100,
        description="Auto-pause at this percentage of context capacity",
    )
    show_usage: bool = Field(default=True, description="Display context usage in UI")


class DefaultsConfig(BaseModel):
    """Schema for default settings."""

    max_turns: int = Field(
        default=20, ge=1, le=1000, description="Default maximum turns per conversation"
    )
    manual_mode: bool = Field(
        default=False, description="Enable manual mode by default"
    )
    streaming_interrupts: bool = Field(
        default=False, description="Enable streaming interrupts (deprecated)"
    )
    human_tag: str = Field(
        default="[HUMAN]",
        description="Tag to prefix human/researcher prompts (empty to disable)",
    )


class ExperimentProfileConfig(BaseModel):
    """Schema for experiment profiles."""

    convergence_threshold: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Override convergence threshold"
    )
    convergence_action: Optional[Literal["stop", "warn"]] = Field(
        default=None, description="Override convergence action"
    )


class ExperimentsConfig(BaseModel):
    """Schema for experiments configuration."""

    unattended: ExperimentProfileConfig = Field(
        default_factory=lambda: ExperimentProfileConfig(
            convergence_threshold=0.75, convergence_action="stop"
        )
    )
    baseline: ExperimentProfileConfig = Field(
        default_factory=lambda: ExperimentProfileConfig(convergence_threshold=1.0)
    )


class ProviderRateLimit(BaseModel):
    """Schema for provider rate limits."""

    requests_per_minute: int = Field(gt=0)
    tokens_per_minute: int = Field(gt=0)


class ProviderOverride(BaseModel):
    """Schema for provider overrides."""

    tokens_per_minute: Optional[int] = Field(default=None, gt=0)
    context_limit: Optional[int] = Field(default=None, gt=0)


class RateLimitingConfig(BaseModel):
    """Schema for rate limiting configuration."""

    enabled: bool = Field(default=True)
    show_pacing_indicators: bool = Field(default=True)
    conservative_estimates: bool = Field(default=True)
    safety_margin: float = Field(default=0.9, gt=0, le=1)
    token_estimation_multiplier: float = Field(default=1.1, gt=1.0, le=2.0)
    backoff_base_delay: float = Field(default=1.0, gt=0)
    backoff_max_delay: float = Field(default=60.0, gt=0)
    sliding_window_minutes: int = Field(default=1, gt=0)
    custom_limits: Dict[str, ProviderRateLimit] = Field(default_factory=dict)


class ProviderContextConfig(BaseModel):
    """Schema for provider context management."""

    enabled: bool = Field(default=True)
    context_reserve_ratio: float = Field(
        default=0.25,
        ge=0,
        le=0.5,
        description="Reserve this ratio of context for response",
    )
    min_messages_retained: int = Field(
        default=10, ge=1, description="Never truncate below this many messages"
    )
    truncation_strategy: Literal["sliding_window"] = Field(default="sliding_window")
    safety_factor: float = Field(
        default=0.9, gt=0, le=1, description="Use this fraction of actual limits"
    )


class OllamaConfig(BaseModel):
    """Schema for Ollama configuration."""

    auto_start: bool = Field(
        default=False, description="Automatically start Ollama server without prompting"
    )


class ProvidersConfig(BaseModel):
    """Schema for providers configuration."""

    context_management: ProviderContextConfig = Field(
        default_factory=ProviderContextConfig
    )
    rate_limiting: RateLimitingConfig = Field(default_factory=RateLimitingConfig)
    overrides: Dict[str, ProviderOverride] = Field(default_factory=dict)


class PidginConfig(BaseModel):
    """Root schema for Pidgin configuration."""

    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    convergence: ConvergenceConfig = Field(default_factory=ConvergenceConfig)
    context_management: ContextManagementConfig = Field(
        default_factory=ContextManagementConfig
    )
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    experiments: ExperimentsConfig = Field(default_factory=ExperimentsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)

    model_config = {"extra": "allow"}  # Allow extra fields for backward compatibility
