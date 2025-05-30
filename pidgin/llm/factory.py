"""Factory for creating LLM instances."""
from typing import Dict, Type, Optional, Union
from pidgin.llm.base import LLM, LLMConfig
from pidgin.llm.anthropic import AnthropicLLM
from pidgin.llm.openai import OpenAILLM
from pidgin.llm.google import GoogleLLM
from pidgin.llm.models import (
    resolve_model_name, 
    get_model_provider,
    MODEL_PROVIDERS,
    parse_model_spec as parse_model_spec_impl
)
from pidgin.config.archetypes import Archetype


# Provider mapping
PROVIDERS: Dict[str, Type[LLM]] = {
    "anthropic": AnthropicLLM,
    "openai": OpenAILLM,
    "google": GoogleLLM,
}


def create_llm(
    model: str,
    archetype: Union[str, Archetype] = Archetype.ANALYTICAL,
    api_key: Optional[str] = None,
    **kwargs
) -> LLM:
    """
    Create an LLM instance.
    
    Args:
        model: Model name or alias
        archetype: Archetype name or enum
        api_key: Optional API key (will use env var if not provided)
        **kwargs: Additional configuration options
    
    Returns:
        LLM instance
    """
    # Resolve model name using centralized logic
    resolved_model = resolve_model_name(model)
    
    # Get provider
    provider = get_model_provider(resolved_model)
    if not provider:
        raise ValueError(f"Unknown model: {model} (resolved to: {resolved_model})")
    
    # Get provider class
    provider_class = PROVIDERS.get(provider)
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider}")
    
    # Convert archetype string to enum if needed
    if isinstance(archetype, str):
        try:
            archetype = Archetype(archetype.lower())
        except ValueError:
            raise ValueError(f"Unknown archetype: {archetype}")
    
    # Create config
    config = LLMConfig(
        model=resolved_model,
        archetype=archetype,
        **kwargs
    )
    
    # Create and return LLM instance
    return provider_class(config, api_key=api_key)


def get_available_models() -> Dict[str, Dict[str, str]]:
    """Get all available models grouped by provider."""
    models = {}
    
    for model, provider in MODEL_PROVIDERS.items():
        if provider not in models:
            models[provider] = {}
        
        # Get model info from provider class
        provider_class = PROVIDERS[provider]
        if hasattr(provider_class, 'MODELS') and model in provider_class.MODELS:
            models[provider][model] = provider_class.MODELS[model]['name']
        else:
            models[provider][model] = model
    
    return models


def parse_model_spec(spec: str) -> tuple[str, Union[str, Archetype]]:
    """
    Parse a model specification string.
    
    Format: "model:archetype" or just "model"
    
    Returns:
        Tuple of (resolved_model, archetype)
    """
    # Use centralized parsing logic
    return parse_model_spec_impl(spec)