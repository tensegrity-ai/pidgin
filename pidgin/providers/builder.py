"""Provider builder - creates provider instances for models."""

from typing import Optional

from ..config.models import get_model_config
from .anthropic import AnthropicProvider
from .google import GoogleProvider
from .local import LocalProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider
from .silent import SilentProvider
from .xai import xAIProvider


async def build_provider(model_id: str, temperature: Optional[float] = None):
    """Create a provider instance for the given model.

    Args:
        model_id: Model identifier (e.g., 'gpt-4', 'claude', 'gemini-1.5-pro')
        temperature: Optional temperature override (not used here, temperature is passed to stream_response)

    Returns:
        Provider instance
    """
    model_config = get_model_config(model_id)
    if not model_config:
        raise ValueError(f"Unknown model: {model_id}")

    # Create appropriate provider (without temperature)
    # Use api.model_id which is the actual API model identifier
    api_model_id = model_config.api.model_id
    if model_config.provider == "openai":
        return OpenAIProvider(model=api_model_id)
    elif model_config.provider == "anthropic":
        return AnthropicProvider(model=api_model_id)
    elif model_config.provider == "google":
        return GoogleProvider(model=api_model_id)
    elif model_config.provider == "xai":
        return xAIProvider(model=api_model_id)
    elif model_config.provider == "local":
        if model_config.model_id == "local:test":
            return LocalProvider(model_name="test")
        else:
            # For other local models, use OllamaProvider
            model_name = model_config.model_id.split(":", 1)[1]
            # Map simple names to Ollama model names
            model_map = {"qwen": "qwen2.5:0.5b", "phi": "phi3", "mistral": "mistral"}
            ollama_model = model_map.get(model_name, model_name)
            return OllamaProvider(ollama_model)
    elif model_config.provider == "silent":
        return SilentProvider(model=model_config.model_id)
    else:
        raise ValueError(f"Unknown provider: {model_config.provider}")
