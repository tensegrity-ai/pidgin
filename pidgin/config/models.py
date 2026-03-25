"""Model configuration and metadata for Pidgin."""

import logging
import re
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
    """Get model configuration by ID, alias, or family name.

    Resolution order:
    1. Exact model ID match
    2. Exact alias match
    3. Family name match (e.g., "opus" matches latest claude-opus-*)
    """
    models = _get_models()

    # Direct match
    if model_or_alias in models:
        return models[model_or_alias]

    # Search by alias
    for model_id, config in models.items():
        if model_or_alias in config.aliases:
            return config

    # Family name match: find the latest model containing the search term
    match = _resolve_family_name(model_or_alias, models)
    if match:
        return match

    return None


def _extract_version_after(model_id: str, family_name: str) -> float:
    """Extract a sortable version number from the part of model_id after the family name.

    This avoids false positives like "16k" in "gpt-3.5-turbo-16k".

    Examples:
        claude-opus-4.1, "opus"   -> 4.1
        gpt-4o, "gpt"             -> 4.0
        gpt-3.5-turbo-16k, "gpt"  -> 3.5
        o3-mini, "o"              -> 3.0
    """
    idx = model_id.lower().find(family_name.lower())
    if idx < 0:
        return 0.0
    # Look at what comes after the family name
    after = model_id[idx + len(family_name) :]
    # Strip leading separator
    after = after.lstrip("-.")
    # Extract the first version-like number
    m = re.match(r"(\d+(?:\.\d+)?)", after)
    if m:
        return float(m.group(1))
    return 0.0


def _resolve_family_name(
    name: str, models: Dict[str, ModelConfig]
) -> Optional[ModelConfig]:
    """Resolve a family name like 'opus' or 'sonnet' to the latest model.

    Matches model IDs that contain the name as a component (bounded by
    hyphens, start/end). Picks the highest-versioned match, preferring
    curated models and shorter IDs (base models over variants).
    """
    name_lower = name.lower()

    candidates: list[tuple[float, int, str, ModelConfig]] = []

    for model_id, config in models.items():
        mid_lower = model_id.lower()
        # Check if name appears as a component (between separators or at boundaries)
        if re.search(rf"(?:^|[-.:]){re.escape(name_lower)}(?:$|[-.:0-9])", mid_lower):
            version = _extract_version_after(model_id, name_lower)
            # Prefer: highest version, then shortest ID (base model over variant)
            candidates.append((version, len(model_id), model_id, config))

    if not candidates:
        return None

    # Sort: version desc, id length asc (shorter = base model)
    candidates.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    best = candidates[0]
    if len(candidates) > 1:
        logger.debug(
            f"Resolved '{name}' to '{best[2]}' " f"(from {len(candidates)} candidates)"
        )
    return best[3]


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
