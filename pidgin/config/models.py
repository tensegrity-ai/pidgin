"""Model configuration and metadata for Pidgin."""

import logging
from typing import Dict, List, Optional

from .model_loader import load_models as _load_from_json
from .model_types import ModelConfig

logger = logging.getLogger(__name__)


# Model configurations aggregated from all providers
_MODELS_CACHE: Optional[Dict[str, ModelConfig]] = None


def _load_models() -> Dict[str, ModelConfig]:
    """Load model configurations."""
    models = _load_from_json()
    if models:
        logger.debug(f"Loaded {len(models)} models")
    else:
        logger.warning("No models found")
    return models


def _get_models() -> Dict[str, ModelConfig]:
    """Get models dictionary, loading on first access."""
    global _MODELS_CACHE
    if _MODELS_CACHE is None:
        _MODELS_CACHE = _load_models()
    return _MODELS_CACHE


# Create a property-like access for backward compatibility
class ModelsDict:
    def __getitem__(self, key):
        return _get_models()[key]

    def __contains__(self, key):
        return key in _get_models()

    def __iter__(self):
        return iter(_get_models())

    def __len__(self):
        return len(_get_models())

    def items(self):
        return _get_models().items()

    def values(self):
        return _get_models().values()

    def keys(self):
        return _get_models().keys()

    def get(self, key, default=None):
        return _get_models().get(key, default)


MODELS = ModelsDict()


def get_model_config(model_or_alias: str) -> Optional[ModelConfig]:
    """Get model configuration by ID or alias."""
    models = _get_models()

    # Direct match
    if model_or_alias in models:
        return models[model_or_alias]

    # Search by alias
    for model_id, config in models.items():
        if model_or_alias in config.aliases:
            return config

    return None


def get_all_aliases() -> Dict[str, str]:
    """Get a mapping of all aliases to model IDs."""
    aliases = {}
    for model_id, config in _get_models().items():
        for alias in config.aliases:
            aliases[alias] = model_id
    return aliases


def get_models_by_provider(provider: str) -> List[ModelConfig]:
    """Get all models for a specific provider."""
    return [config for config in _get_models().values() if config.provider == provider]


def get_model_shortcuts() -> Dict[str, str]:
    """Get simplified shortcuts for backward compatibility."""
    shortcuts = {}
    for model_id, config in _get_models().items():
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
