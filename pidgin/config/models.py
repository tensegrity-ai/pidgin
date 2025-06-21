"""Model configuration and metadata for Pidgin."""

from typing import Dict, List, Optional, Literal
from dataclasses import dataclass


@dataclass
class ModelCharacteristics:
    """Research-relevant characteristics of a model."""

    verbosity_level: int  # 1-10 scale
    avg_response_length: Literal["short", "medium", "long"]
    recommended_pairings: List[str]
    conversation_style: Literal["concise", "verbose", "analytical", "creative"]


@dataclass
class ModelConfig:
    """Complete configuration for a model."""

    model_id: str
    shortname: str
    aliases: List[str]
    provider: Literal["anthropic", "openai", "google", "xai", "local"]
    context_window: int
    pricing_tier: Literal["economy", "standard", "premium", "free"]
    characteristics: ModelCharacteristics
    deprecated: bool = False
    deprecation_date: Optional[str] = None
    notes: Optional[str] = None


# Model configurations with full metadata
MODELS: Dict[str, ModelConfig] = {
    # Anthropic Models
    "claude-4-opus-20250514": ModelConfig(
        model_id="claude-4-opus-20250514",
        shortname="Opus",
        aliases=["opus", "opus4", "claude-opus"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="long",
            recommended_pairings=["gpt-4.1", "o3"],
            conversation_style="analytical",
        ),
    ),
    "claude-4-sonnet-20250514": ModelConfig(
        model_id="claude-4-sonnet-20250514",
        shortname="Sonnet",
        aliases=["sonnet", "sonnet4", "claude-sonnet", "claude"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=6,
            avg_response_length="medium",
            recommended_pairings=["gpt-4.1-mini", "claude-4-sonnet-20250514"],
            conversation_style="verbose",
        ),
    ),
    "claude-3-5-sonnet-20241022": ModelConfig(
        model_id="claude-3-5-sonnet-20241022",
        shortname="Sonnet3.5",
        aliases=["sonnet3.5", "claude-3.5", "sonnet3.7", "claude-3.7"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="medium",
            recommended_pairings=["o4-mini", "gpt-4.1-mini"],
            conversation_style="analytical",
        ),
        notes="Latest Sonnet model",
    ),
    "claude-3-5-haiku-20241022": ModelConfig(
        model_id="claude-3-5-haiku-20241022",
        shortname="Haiku",
        aliases=["haiku", "haiku3.5", "claude-haiku"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=3,
            avg_response_length="short",
            recommended_pairings=["gpt-4.1-nano", "claude-3-5-haiku-20241022"],
            conversation_style="concise",
        ),
    ),
    "claude-3-haiku-20240307": ModelConfig(
        model_id="claude-3-haiku-20240307",
        shortname="Haiku3",
        aliases=["haiku3", "claude-3-haiku"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=3,
            avg_response_length="short",
            recommended_pairings=["gpt-4o-mini", "claude-3-haiku-20240307"],
            conversation_style="concise",
        ),
        notes="Legacy Haiku model",
    ),
    # OpenAI Models
    "gpt-4.1": ModelConfig(
        model_id="gpt-4.1",
        shortname="GPT-4.1",
        aliases=["gpt4.1", "coding", "4.1"],
        provider="openai",
        context_window=1000000,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="medium",
            recommended_pairings=["claude-4-opus-20250514", "o3"],
            conversation_style="analytical",
        ),
        notes="Primary coding-focused model",
    ),
    "gpt-4.1-mini": ModelConfig(
        model_id="gpt-4.1-mini",
        shortname="GPT-Mini",
        aliases=["gpt4.1-mini", "coding-mini", "gpt-mini"],
        provider="openai",
        context_window=1000000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=5,
            avg_response_length="medium",
            recommended_pairings=["claude-4-sonnet-20250514", "gpt-4.1-mini"],
            conversation_style="verbose",
        ),
    ),
    "gpt-4.1-nano": ModelConfig(
        model_id="gpt-4.1-nano",
        shortname="GPT-Nano",
        aliases=["gpt4.1-nano", "coding-fast", "nano"],
        provider="openai",
        context_window=1000000,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=3,
            avg_response_length="short",
            recommended_pairings=["claude-3-5-haiku-20241022", "gpt-4.1-nano"],
            conversation_style="concise",
        ),
    ),
    "o3": ModelConfig(
        model_id="o3",
        shortname="O3",
        aliases=["reasoning-premium"],
        provider="openai",
        context_window=128000,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=9,
            avg_response_length="long",
            recommended_pairings=["claude-4-opus-20250514", "gpt-4.1"],
            conversation_style="analytical",
        ),
        notes="Premium reasoning model",
    ),
    "o3-mini": ModelConfig(
        model_id="o3-mini",
        shortname="O3-Mini",
        aliases=["reasoning-small"],
        provider="openai",
        context_window=128000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=6,
            avg_response_length="medium",
            recommended_pairings=["claude-3-7-sonnet-20250224", "o4-mini"],
            conversation_style="analytical",
        ),
        notes="Small reasoning model",
    ),
    "o4-mini": ModelConfig(
        model_id="o4-mini",
        shortname="O4",
        aliases=["reasoning", "o4"],
        provider="openai",
        context_window=128000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="medium",
            recommended_pairings=["claude-3-7-sonnet-20250224", "gpt-4.1-mini"],
            conversation_style="analytical",
        ),
        notes="Latest small reasoning model (recommended over o3-mini)",
    ),
    "o4-mini-high": ModelConfig(
        model_id="o4-mini-high",
        shortname="O4-High",
        aliases=["reasoning-high", "o4-high"],
        provider="openai",
        context_window=128000,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="long",
            recommended_pairings=["claude-4-opus-20250514", "o3"],
            conversation_style="analytical",
        ),
        notes="Enhanced reasoning variant",
    ),
    "gpt-4.5": ModelConfig(
        model_id="gpt-4.5",
        shortname="GPT-4.5",
        aliases=["gpt4.5", "4.5"],
        provider="openai",
        context_window=128000,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="medium",
            recommended_pairings=["claude-4-opus-20250514", "gpt-4.1"],
            conversation_style="analytical",
        ),
        deprecated=True,
        deprecation_date="2025-07",
        notes="Research preview - being deprecated July 2025",
    ),
    "gpt-4o": ModelConfig(
        model_id="gpt-4o",
        shortname="GPT-4o",
        aliases=["gpt4o", "4o", "multimodal", "gpt"],
        provider="openai",
        context_window=128000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=6,
            avg_response_length="medium",
            recommended_pairings=["claude-4-sonnet-20250514", "gpt-4o-mini"],
            conversation_style="verbose",
        ),
        notes="Multimodal model",
    ),
    "gpt-4o-mini": ModelConfig(
        model_id="gpt-4o-mini",
        shortname="GPT-4o-Mini",
        aliases=["gpt4o-mini", "4o-mini"],
        provider="openai",
        context_window=128000,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=4,
            avg_response_length="short",
            recommended_pairings=["claude-3-haiku-20240307", "gpt-4.1-nano"],
            conversation_style="concise",
        ),
        notes="Fast multimodal model",
    ),
    "gpt-image-1": ModelConfig(
        model_id="gpt-image-1",
        shortname="DALL-E",
        aliases=["image", "dalle"],
        provider="openai",
        context_window=0,  # Not applicable for image generation
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=0,
            avg_response_length="short",
            recommended_pairings=[],
            conversation_style="creative",
        ),
        notes="Latest image generation model - not for conversations",
    ),
    # Google Models
    "gemini-2.0-flash-exp": ModelConfig(
        model_id="gemini-2.0-flash-exp",
        shortname="Flash",
        aliases=["gemini-flash", "flash", "gemini"],
        provider="google",
        context_window=1048576,  # 1M tokens
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=5,
            avg_response_length="medium",
            recommended_pairings=["claude-3-5-haiku-20241022", "gpt-4o-mini"],
            conversation_style="concise",
        ),
        notes="Fast experimental model with 1M context",
    ),
    "gemini-2.0-flash-thinking-exp": ModelConfig(
        model_id="gemini-2.0-flash-thinking-exp",
        shortname="Thinking",
        aliases=["gemini-thinking", "thinking", "flash-thinking"],
        provider="google",
        context_window=32767,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="long",
            recommended_pairings=["o4-mini", "claude-4-sonnet-20250514"],
            conversation_style="analytical",
        ),
        notes="Reasoning model with visible thinking process",
    ),
    "gemini-exp-1206": ModelConfig(
        model_id="gemini-exp-1206",
        shortname="Gemini-Exp",
        aliases=["gemini-exp", "exp-1206"],
        provider="google",
        context_window=2097152,  # 2M tokens
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="long",
            recommended_pairings=["claude-4-opus-20250514", "gpt-4.1"],
            conversation_style="analytical",
        ),
        notes="Experimental model with 2M context window",
    ),
    "gemini-1.5-pro": ModelConfig(
        model_id="gemini-1.5-pro",
        shortname="Gemini-Pro",
        aliases=["gemini-pro", "1.5-pro"],
        provider="google",
        context_window=2097152,  # 2M tokens
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="long",
            recommended_pairings=["claude-4-opus-20250514", "gpt-4.1"],
            conversation_style="analytical",
        ),
        notes="Production model with 2M context",
    ),
    "gemini-1.5-flash": ModelConfig(
        model_id="gemini-1.5-flash",
        shortname="Flash-1.5",
        aliases=["flash-1.5"],
        provider="google",
        context_window=1048576,  # 1M tokens
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=4,
            avg_response_length="medium",
            recommended_pairings=["claude-3-5-haiku-20241022", "gpt-4o-mini"],
            conversation_style="concise",
        ),
        notes="Fast production model",
    ),
    "gemini-1.5-flash-8b": ModelConfig(
        model_id="gemini-1.5-flash-8b",
        shortname="Flash-8B",
        aliases=["flash-8b", "gemini-8b"],
        provider="google",
        context_window=1048576,  # 1M tokens
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=3,
            avg_response_length="short",
            recommended_pairings=["claude-3-5-haiku-20241022", "gpt-4o-mini"],
            conversation_style="concise",
        ),
        notes="Smallest and fastest Gemini model",
    ),
    # xAI Models
    "grok-beta": ModelConfig(
        model_id="grok-beta",
        shortname="Grok",
        aliases=["grok", "xai"],
        provider="xai",
        context_window=131072,  # 128K tokens
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="long",
            recommended_pairings=["claude-4-opus-20250514", "gpt-4.1"],
            conversation_style="analytical",
        ),
        notes="xAI's flagship reasoning model",
    ),
    "grok-2-1212": ModelConfig(
        model_id="grok-2-1212",
        shortname="Grok-2",
        aliases=["grok-2", "grok2"],
        provider="xai",
        context_window=131072,  # 128K tokens
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="long",
            recommended_pairings=["claude-4-sonnet-20250514", "gpt-4.1"],
            conversation_style="analytical",
        ),
        notes="Latest Grok model with improved capabilities",
    ),
    "grok-2-vision-1212": ModelConfig(
        model_id="grok-2-vision-1212",
        shortname="Grok-Vision",
        aliases=["grok-vision", "grok-2-vision"],
        provider="xai",
        context_window=131072,  # 128K tokens
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="long",
            recommended_pairings=["gpt-4o", "claude-4-sonnet-20250514"],
            conversation_style="analytical",
        ),
        notes="Grok with vision capabilities for multimodal tasks",
    ),
    # Local Models
    "local:test": ModelConfig(
        model_id="local:test",
        shortname="TestModel",
        aliases=["test", "local-test"],
        provider="local",
        context_window=8192,
        pricing_tier="free",
        characteristics=ModelCharacteristics(
            verbosity_level=5,
            avg_response_length="medium",
            recommended_pairings=["local:test", "gpt-4o-mini"],
            conversation_style="analytical",
        ),
        notes="Deterministic test model for offline development",
    ),
    "local:qwen": ModelConfig(
        model_id="local:qwen",
        shortname="Qwen-0.5B",
        aliases=["qwen", "qwen-tiny"],
        provider="ollama",
        context_window=32768,
        pricing_tier="free",
        characteristics=ModelCharacteristics(
            verbosity_level=4,
            avg_response_length="short",
            recommended_pairings=["local:phi", "local:test"],
            conversation_style="concise",
        ),
        notes="Qwen 0.5B via Ollama - requires Ollama running",
    ),
    "local:phi": ModelConfig(
        model_id="local:phi",
        shortname="Phi-3",
        aliases=["phi", "phi3"],
        provider="ollama",
        context_window=4096,
        pricing_tier="free",
        characteristics=ModelCharacteristics(
            verbosity_level=6,
            avg_response_length="medium",
            recommended_pairings=["local:qwen", "local:test"],
            conversation_style="analytical",
        ),
        notes="Phi-3 via Ollama",
    ),
    "local:mistral": ModelConfig(
        model_id="local:mistral",
        shortname="Mistral-7B",
        aliases=["mistral", "mistral7b"],
        provider="ollama",
        context_window=32768,
        pricing_tier="free",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="long",
            recommended_pairings=["claude-4-opus-20250514", "gpt-4.1"],
            conversation_style="verbose",
        ),
        notes="Mistral 7B via Ollama - requires 8GB+ RAM",
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
    return [config for config in MODELS.values() if config.provider == provider]


def get_model_shortcuts() -> Dict[str, str]:
    """Get simplified shortcuts for backward compatibility."""
    shortcuts = {}
    for model_id, config in MODELS.items():
        # Add the first alias as the primary shortcut
        if config.aliases:
            shortcuts[config.aliases[0]] = model_id
    return shortcuts


def resolve_model_id(model_or_alias: str) -> tuple[str, Optional[ModelConfig]]:
    """Resolve a model name or alias to its full model ID.
    
    Args:
        model_or_alias: Model ID or alias
        
    Returns:
        Tuple of (resolved_model_id, model_config)
        If model not found, returns (original_input, None)
    """
    config = get_model_config(model_or_alias)
    if config:
        return config.model_id, config
    else:
        return model_or_alias, None
