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
        return LocalProvider(model_name="test")
    elif model_config.provider == "ollama":
        ollama_model = model_config.api.ollama_model
        if not ollama_model:
            raise ValueError(
                f"Model {model_config.model_id} has provider 'ollama' "
                f"but no api.ollama_model set in models.json"
            )
        return OllamaProvider(ollama_model)
    elif model_config.provider == "silent":
        return SilentProvider(model=model_config.model_id)
    else:
        raise ValueError(f"Unknown provider: {model_config.provider}")
