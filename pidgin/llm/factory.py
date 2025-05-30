"""Factory for creating LLM instances."""
from typing import Dict, Type, Optional, Union
from pidgin.llm.base import LLM, LLMConfig
from pidgin.llm.anthropic import AnthropicLLM
from pidgin.llm.openai import OpenAILLM
from pidgin.llm.google import GoogleLLM
from pidgin.config.archetypes import Archetype


# Provider mapping
PROVIDERS: Dict[str, Type[LLM]] = {
    "anthropic": AnthropicLLM,
    "openai": OpenAILLM,
    "google": GoogleLLM,
}

# Model to provider mapping
MODEL_PROVIDERS = {
    # Anthropic models
    "claude-3-opus-20240229": "anthropic",
    "claude-3-sonnet-20240229": "anthropic",
    "claude-3-haiku-20240307": "anthropic",
    "claude-2.1": "anthropic",
    "claude-2.0": "anthropic",
    
    # OpenAI models
    "gpt-4-turbo-preview": "openai",
    "gpt-4": "openai",
    "gpt-4-32k": "openai",
    "gpt-3.5-turbo": "openai",
    "gpt-3.5-turbo-16k": "openai",
    
    # Google models
    "gemini-pro": "google",
    "gemini-pro-vision": "google",
}

# Shorthand aliases
MODEL_ALIASES = {
    "claude": "claude-3-opus-20240229",
    "claude-opus": "claude-3-opus-20240229",
    "claude-sonnet": "claude-3-sonnet-20240229",
    "claude-haiku": "claude-3-haiku-20240307",
    "gpt4": "gpt-4",
    "gpt-4": "gpt-4",
    "gpt": "gpt-3.5-turbo",
    "gpt3": "gpt-3.5-turbo",
    "gemini": "gemini-pro",
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
    # Resolve model alias
    model = MODEL_ALIASES.get(model.lower(), model)
    
    # Get provider
    provider = MODEL_PROVIDERS.get(model)
    if not provider:
        raise ValueError(f"Unknown model: {model}")
    
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
        model=model,
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
        Tuple of (model, archetype)
    """
    parts = spec.split(":", 1)
    model = parts[0]
    
    if len(parts) > 1:
        archetype = parts[1]
    else:
        archetype = Archetype.ANALYTICAL
    
    return model, archetype