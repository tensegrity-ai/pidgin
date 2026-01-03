# pidgin/cli/helpers.py
"""Shared helper functions for CLI commands."""

from typing import Optional, Tuple

from ..config.models import get_model_config
from ..providers.builder import build_provider
from .constants import MODEL_GLYPHS, PROVIDER_COLORS


async def get_provider_for_model(model_id: str, temperature: Optional[float] = None):
    """Create a provider instance for the given model.

    This is a compatibility wrapper that delegates to the new provider builder.

    Args:
        model_id: Model identifier (e.g., 'gpt-4', 'claude', 'gemini-1.5-pro')
        temperature: Optional temperature override (not used here, temperature is passed to stream_response)

    Returns:
        Provider instance
    """
    return await build_provider(model_id, temperature)


def build_initial_prompt(custom_prompt: Optional[str] = None) -> Optional[str]:
    """Build the initial prompt for a conversation.

    Args:
        custom_prompt: Custom prompt text

    Returns:
        The initial prompt string, or None for cold start
    """
    return custom_prompt


def validate_model_id(model_id: str) -> Tuple[str, str]:
    """Validate and normalize a model identifier.

    Args:
        model_id: Model ID from user input

    Returns:
        Tuple of (validated_id, display_name)

    Raises:
        ValueError: If model ID is invalid
    """
    # Handle silent model
    if model_id == "silent":
        return "silent", "Silent"

    # Check if it's a known model
    config = get_model_config(model_id)
    if config:
        return model_id, config.display_name

    # Try provider:model format
    if ":" in model_id:
        provider, model_name = model_id.split(":", 1)
        if provider == "local":
            # For local models, check if Ollama is available
            if not check_ollama_available():
                raise ValueError("Ollama is not running. Start it with 'ollama serve'")
            return model_id, f"Local: {model_name}"

    raise ValueError(f"Unknown model: {model_id}")


def check_ollama_available() -> bool:
    """Check if Ollama is running and accessible."""
    import httpx

    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError):
        return False


def format_model_display(model_id: str) -> str:
    """Format model ID for display with emoji and color."""
    config = get_model_config(model_id)
    if not config:
        return model_id

    glyph = MODEL_GLYPHS.get(model_id, "●")
    color = PROVIDER_COLORS.get(config.provider, "white")

    return f"{glyph} [{color}]{config.display_name}[/{color}]"
