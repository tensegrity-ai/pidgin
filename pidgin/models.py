"""Model configuration and metadata for Pidgin."""

from typing import Dict, List, Optional, Literal
from dataclasses import dataclass


@dataclass
class ModelCharacteristics:
    """Research-relevant characteristics of a model."""
    verbosity_level: int  # 1-10 scale
    avg_response_length: Literal["short", "medium", "long"]
    attractor_tendency: Literal["compression", "expansion", "balanced"]
    recommended_pairings: List[str]
    conversation_style: Literal["concise", "verbose", "analytical", "creative"]


@dataclass
class ModelConfig:
    """Complete configuration for a model."""
    model_id: str
    aliases: List[str]
    provider: Literal["anthropic", "openai"]
    context_window: int
    pricing_tier: Literal["economy", "standard", "premium"]
    characteristics: ModelCharacteristics
    deprecated: bool = False
    deprecation_date: Optional[str] = None
    notes: Optional[str] = None


# Model configurations with full metadata
MODELS: Dict[str, ModelConfig] = {
    # Anthropic Models
    "claude-4-opus-20250514": ModelConfig(
        model_id="claude-4-opus-20250514",
        aliases=["opus", "opus4", "claude-opus"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="long",
            attractor_tendency="expansion",
            recommended_pairings=["gpt-4.1", "o3"],
            conversation_style="analytical"
        )
    ),
    "claude-4-sonnet-20250514": ModelConfig(
        model_id="claude-4-sonnet-20250514",
        aliases=["sonnet", "sonnet4", "claude-sonnet", "claude"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=6,
            avg_response_length="medium",
            attractor_tendency="balanced",
            recommended_pairings=["gpt-4.1-mini", "claude-4-sonnet-20250514"],
            conversation_style="verbose"
        )
    ),
    "claude-3-7-sonnet-20250224": ModelConfig(
        model_id="claude-3-7-sonnet-20250224",
        aliases=["sonnet3.7", "claude-3.7"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="medium",
            attractor_tendency="balanced",
            recommended_pairings=["o4-mini", "gpt-4.1-mini"],
            conversation_style="analytical"
        ),
        notes="Hybrid reasoning model"
    ),
    "claude-3-5-haiku-20241022": ModelConfig(
        model_id="claude-3-5-haiku-20241022",
        aliases=["haiku", "haiku3.5", "claude-haiku"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=3,
            avg_response_length="short",
            attractor_tendency="compression",
            recommended_pairings=["gpt-4.1-nano", "claude-3-5-haiku-20241022"],
            conversation_style="concise"
        )
    ),
    "claude-3-haiku-20240307": ModelConfig(
        model_id="claude-3-haiku-20240307",
        aliases=["haiku3", "claude-3-haiku"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=3,
            avg_response_length="short",
            attractor_tendency="compression",
            recommended_pairings=["gpt-4o-mini", "claude-3-haiku-20240307"],
            conversation_style="concise"
        ),
        notes="Legacy Haiku model"
    ),
    
    # OpenAI Models
    "gpt-4.1": ModelConfig(
        model_id="gpt-4.1",
        aliases=["gpt4.1", "coding", "4.1"],
        provider="openai",
        context_window=1000000,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="medium",
            attractor_tendency="balanced",
            recommended_pairings=["claude-4-opus-20250514", "o3"],
            conversation_style="analytical"
        ),
        notes="Primary coding-focused model"
    ),
    "gpt-4.1-mini": ModelConfig(
        model_id="gpt-4.1-mini",
        aliases=["gpt4.1-mini", "coding-mini", "gpt-mini", "gpt"],
        provider="openai",
        context_window=1000000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=5,
            avg_response_length="medium",
            attractor_tendency="balanced",
            recommended_pairings=["claude-4-sonnet-20250514", "gpt-4.1-mini"],
            conversation_style="verbose"
        )
    ),
    "gpt-4.1-nano": ModelConfig(
        model_id="gpt-4.1-nano",
        aliases=["gpt4.1-nano", "coding-fast", "nano"],
        provider="openai",
        context_window=1000000,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=3,
            avg_response_length="short",
            attractor_tendency="compression",
            recommended_pairings=["claude-3-5-haiku-20241022", "gpt-4.1-nano"],
            conversation_style="concise"
        )
    ),
    "o3": ModelConfig(
        model_id="o3",
        aliases=["reasoning-premium"],
        provider="openai",
        context_window=128000,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=9,
            avg_response_length="long",
            attractor_tendency="expansion",
            recommended_pairings=["claude-4-opus-20250514", "gpt-4.1"],
            conversation_style="analytical"
        ),
        notes="Premium reasoning model"
    ),
    "o3-mini": ModelConfig(
        model_id="o3-mini",
        aliases=["reasoning-small"],
        provider="openai",
        context_window=128000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=6,
            avg_response_length="medium",
            attractor_tendency="balanced",
            recommended_pairings=["claude-3-7-sonnet-20250224", "o4-mini"],
            conversation_style="analytical"
        ),
        notes="Small reasoning model"
    ),
    "o4-mini": ModelConfig(
        model_id="o4-mini",
        aliases=["reasoning", "o4"],
        provider="openai",
        context_window=128000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="medium",
            attractor_tendency="balanced",
            recommended_pairings=["claude-3-7-sonnet-20250224", "gpt-4.1-mini"],
            conversation_style="analytical"
        ),
        notes="Latest small reasoning model (recommended over o3-mini)"
    ),
    "o4-mini-high": ModelConfig(
        model_id="o4-mini-high",
        aliases=["reasoning-high", "o4-high"],
        provider="openai",
        context_window=128000,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="long",
            attractor_tendency="expansion",
            recommended_pairings=["claude-4-opus-20250514", "o3"],
            conversation_style="analytical"
        ),
        notes="Enhanced reasoning variant"
    ),
    "gpt-4.5": ModelConfig(
        model_id="gpt-4.5",
        aliases=["gpt4.5", "4.5"],
        provider="openai",
        context_window=128000,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="medium",
            attractor_tendency="balanced",
            recommended_pairings=["claude-4-opus-20250514", "gpt-4.1"],
            conversation_style="analytical"
        ),
        deprecated=True,
        deprecation_date="2025-07",
        notes="Research preview - being deprecated July 2025"
    ),
    "gpt-4o": ModelConfig(
        model_id="gpt-4o",
        aliases=["gpt4o", "4o", "multimodal"],
        provider="openai",
        context_window=128000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=6,
            avg_response_length="medium",
            attractor_tendency="balanced",
            recommended_pairings=["claude-4-sonnet-20250514", "gpt-4o-mini"],
            conversation_style="verbose"
        ),
        notes="Multimodal model"
    ),
    "gpt-4o-mini": ModelConfig(
        model_id="gpt-4o-mini",
        aliases=["gpt4o-mini", "4o-mini"],
        provider="openai",
        context_window=128000,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=4,
            avg_response_length="short",
            attractor_tendency="compression",
            recommended_pairings=["claude-3-haiku-20240307", "gpt-4.1-nano"],
            conversation_style="concise"
        ),
        notes="Fast multimodal model"
    ),
    "gpt-image-1": ModelConfig(
        model_id="gpt-image-1",
        aliases=["image", "dalle"],
        provider="openai",
        context_window=0,  # Not applicable for image generation
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=0,
            avg_response_length="short",
            attractor_tendency="balanced",
            recommended_pairings=[],
            conversation_style="creative"
        ),
        notes="Latest image generation model - not for conversations"
    ),
}


def get_model_config(model_or_alias: str) -> Optional[ModelConfig]:
    """Get model configuration by ID or alias."""
    # Direct match
    if model_or_alias in MODELS:
        return MODELS[model_or_alias]
    
    # Search by alias
    for model_id, config in MODELS.items():
        if model_or_alias in config.aliases:
            return config
    
    return None


def get_all_aliases() -> Dict[str, str]:
    """Get a mapping of all aliases to model IDs."""
    aliases = {}
    for model_id, config in MODELS.items():
        for alias in config.aliases:
            aliases[alias] = model_id
    return aliases


def get_models_by_provider(provider: str) -> List[ModelConfig]:
    """Get all models for a specific provider."""
    return [
        config for config in MODELS.values() 
        if config.provider == provider
    ]


def get_model_shortcuts() -> Dict[str, str]:
    """Get simplified shortcuts for backward compatibility."""
    shortcuts = {}
    for model_id, config in MODELS.items():
        # Add the first alias as the primary shortcut
        if config.aliases:
            shortcuts[config.aliases[0]] = model_id
    return shortcuts