"""Model configuration and aliases for Pidgin."""
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class ModelInfo:
    """Information about a model."""
    full_id: str
    name: str
    provider: str
    is_default: bool = False


# Model shortcuts/aliases mapping
MODEL_ALIASES = {
    # Claude shortcuts
    "claude": "claude-opus-4-20250514",  # Latest Claude
    "claude-opus": "claude-opus-4-20250514",
    "claude-opus-4": "claude-opus-4-20250514",
    "claude-sonnet": "claude-sonnet-4-20250514",
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    "claude-3.5-sonnet": "claude-3.5-sonnet-20241022",  # Previous generation
    "claude-3-opus": "claude-3-opus-20240229",  # Legacy
    "claude-3-sonnet": "claude-3-sonnet-20240229",
    "claude-3-haiku": "claude-3-haiku-20240307",
    
    # OpenAI shortcuts - Current generation
    "gpt": "gpt-4o",  # Default to 4o as most commonly used
    "gpt4o": "gpt-4o",
    "gpt-4o": "gpt-4o",
    "4o": "gpt-4o",
    "o3": "o3",  # New reasoning model
    "o3-mini": "o3-mini",
    "o1": "o1",  # Previous reasoning model
    "o1-preview": "o1-preview", 
    "o1-mini": "o1-mini",
    "gpt4": "gpt-4",  # Original GPT-4
    "gpt-4": "gpt-4",
    "gpt4-turbo": "gpt-4-turbo",
    "gpt-4-turbo": "gpt-4-turbo",
    "gpt-3.5": "gpt-3.5-turbo",  # Still useful for testing
    "gpt3.5": "gpt-3.5-turbo",
    
    # Google shortcuts
    "gemini": "gemini-pro",  # Latest Gemini
    "gemini-pro": "gemini-pro",
    "gemini-ultra": "gemini-ultra",  # When available
    "gemini-vision": "gemini-pro-vision",
    
    # Common alternatives
    "opus": "claude-opus-4-20250514",
    "sonnet": "claude-sonnet-4-20250514",
    "haiku": "claude-3-haiku-20240307",
}

# Model to provider mapping (includes both shortcuts and full IDs)
MODEL_PROVIDERS = {
    # Anthropic models
    "claude-opus-4-20250514": "anthropic",
    "claude-sonnet-4-20250514": "anthropic",
    "claude-3.5-sonnet-20241022": "anthropic",
    "claude-3-opus-20240229": "anthropic",
    "claude-3-sonnet-20240229": "anthropic",
    "claude-3-haiku-20240307": "anthropic",
    "claude-2.1": "anthropic",
    "claude-2.0": "anthropic",
    
    # OpenAI models
    "gpt-4o": "openai",
    "o3": "openai",
    "o3-mini": "openai",
    "o1": "openai",
    "o1-preview": "openai",
    "o1-mini": "openai",
    "gpt-4-turbo": "openai",
    "gpt-4": "openai",
    "gpt-4-32k": "openai",
    "gpt-3.5-turbo": "openai",
    "gpt-3.5-turbo-16k": "openai",
    
    # Google models
    "gemini-pro": "google",
    "gemini-pro-vision": "google",
    "gemini-ultra": "google",
}

# Provider display names
PROVIDER_NAMES = {
    "anthropic": "Claude (Anthropic)",
    "openai": "GPT (OpenAI)",
    "google": "Gemini (Google)",
}

# Default model
DEFAULT_MODEL = "claude-opus-4-20250514"


def resolve_model_name(model: str) -> str:
    """
    Resolve a model name or alias to its full identifier.
    
    Args:
        model: Model name, alias, or full identifier
        
    Returns:
        Full model identifier
    """
    # Convert to lowercase for case-insensitive matching
    model_lower = model.lower()
    
    # Check if it's an alias
    if model_lower in MODEL_ALIASES:
        return MODEL_ALIASES[model_lower]
    
    # Return as-is (could be a full identifier or future model)
    return model


def get_model_provider(model: str) -> Optional[str]:
    """
    Get the provider for a model.
    
    Args:
        model: Model name, alias, or full identifier
        
    Returns:
        Provider name or None if unknown
    """
    # Resolve any alias first
    full_model = resolve_model_name(model)
    
    return MODEL_PROVIDERS.get(full_model)


def get_provider_models(provider: str) -> List[Tuple[str, str]]:
    """
    Get all models for a provider.
    
    Args:
        provider: Provider name (anthropic, openai, google)
        
    Returns:
        List of (model_id, model_name) tuples
    """
    models = []
    
    # Get all models for this provider
    for model_id, model_provider in MODEL_PROVIDERS.items():
        if model_provider == provider:
            # Find a friendly name from aliases or use the ID
            friendly_name = model_id
            for alias, full_id in MODEL_ALIASES.items():
                if full_id == model_id and len(alias) < len(friendly_name):
                    friendly_name = alias
            
            models.append((model_id, friendly_name))
    
    return sorted(models)


def get_model_shortcuts() -> Dict[str, Dict[str, str]]:
    """
    Get all model shortcuts organized by provider.
    
    Returns:
        Dict of provider -> {shortcut: full_model_id}
    """
    shortcuts_by_provider = {
        "anthropic": {},
        "openai": {},
        "google": {},
    }
    
    for shortcut, full_id in MODEL_ALIASES.items():
        provider = MODEL_PROVIDERS.get(full_id)
        if provider and provider in shortcuts_by_provider:
            shortcuts_by_provider[provider][shortcut] = full_id
    
    return shortcuts_by_provider


def parse_model_spec(spec: str) -> Tuple[str, str]:
    """
    Parse a model specification string.
    
    Format: "model:archetype" or just "model"
    
    Args:
        spec: Model specification
        
    Returns:
        Tuple of (resolved_model, archetype)
    """
    parts = spec.split(":", 1)
    model = parts[0]
    
    # Resolve model name
    resolved_model = resolve_model_name(model)
    
    # Get archetype or default
    if len(parts) > 1:
        archetype = parts[1]
    else:
        archetype = "analytical"  # default
    
    return resolved_model, archetype