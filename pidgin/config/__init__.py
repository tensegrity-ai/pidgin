"""Configuration and model definitions for pidgin."""

from .config import Config, get_config, load_config
from .models import ModelConfig, ModelCharacteristics, get_model_config, get_models_by_provider
from .system_prompts import get_system_prompts, get_awareness_info
from .dimensional_prompts import DimensionalPromptGenerator

__all__ = [
    # From config
    'Config',
    'get_config',
    'load_config',
    
    # From models
    'ModelConfig',
    'ModelCharacteristics',
    'get_model_config',
    'get_models_by_provider',
    
    # From system_prompts
    'get_system_prompts',
    'get_awareness_info',
    
    # From dimensional_prompts
    'DimensionalPromptGenerator',
]