"""Configuration and model definitions for pidgin."""

from .config import Config
from .models import (
    ModelConfig,
    get_model_config,
    get_models_by_provider,
)
from .system_prompts import get_awareness_info, get_system_prompts

__all__ = [
    # From config
    "Config",
    # From models
    "ModelConfig",
    "get_model_config",
    "get_models_by_provider",
    # From system_prompts
    "get_system_prompts",
    "get_awareness_info",
]
