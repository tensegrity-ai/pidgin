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


# Import model configurations from providers
def _load_models() -> Dict[str, ModelConfig]:
    """Load model configurations from all providers."""
    models = {}
    
    # Import provider models - use lazy imports to avoid circular dependencies
    try:
        from ..providers.anthropic import ANTHROPIC_MODELS
        models.update(ANTHROPIC_MODELS)
    except ImportError:
        pass
    
    try:
        from ..providers.openai import OPENAI_MODELS
        models.update(OPENAI_MODELS)
    except ImportError:
        pass
    
    try:
        from ..providers.google import GOOGLE_MODELS
        models.update(GOOGLE_MODELS)
    except ImportError:
        pass
    
    try:
        from ..providers.xai import XAI_MODELS
        models.update(XAI_MODELS)
    except ImportError:
        pass
    
    try:
        from ..providers.local import LOCAL_MODELS
        models.update(LOCAL_MODELS)
    except ImportError:
        pass
    
    try:
        from ..providers.ollama import OLLAMA_MODELS
        models.update(OLLAMA_MODELS)
    except ImportError:
        pass
    
    try:
        from ..providers.silent import SILENT_MODELS
        models.update(SILENT_MODELS)
    except ImportError:
        pass
    
    return models

# Model configurations aggregated from all providers
MODELS: Dict[str, ModelConfig] = _load_models()


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
