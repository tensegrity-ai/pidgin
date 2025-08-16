"""Provider-specific capabilities and limits configuration."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ProviderCapabilities:
    """Capabilities and limits for a provider."""

    requests_per_minute: int = 60
    tokens_per_minute: int = 60000
    system_prompt_overhead: int = 100
    supports_streaming: bool = True
    supports_tool_use: bool = False
    supports_vision: bool = False


# Provider-specific capabilities
PROVIDER_CAPABILITIES: Dict[str, ProviderCapabilities] = {
    "anthropic": ProviderCapabilities(
        requests_per_minute=50,
        tokens_per_minute=40000,
        system_prompt_overhead=200,  # Anthropic uses larger system prompts
        supports_streaming=True,
        supports_tool_use=True,
        supports_vision=True,
    ),
    "openai": ProviderCapabilities(
        requests_per_minute=60,
        tokens_per_minute=90000,
        system_prompt_overhead=100,
        supports_streaming=True,
        supports_tool_use=True,
        supports_vision=True,
    ),
    "google": ProviderCapabilities(
        requests_per_minute=60,
        tokens_per_minute=60000,
        system_prompt_overhead=100,
        supports_streaming=True,
        supports_tool_use=True,
        supports_vision=True,
    ),
    "xai": ProviderCapabilities(
        requests_per_minute=60,
        tokens_per_minute=60000,
        system_prompt_overhead=100,
        supports_streaming=True,
        supports_tool_use=False,
        supports_vision=False,
    ),
    "local": ProviderCapabilities(
        requests_per_minute=999999,  # No practical limits for local models
        tokens_per_minute=999999,
        system_prompt_overhead=50,  # Local models often have minimal overhead
        supports_streaming=False,
        supports_tool_use=False,
        supports_vision=False,
    ),
}


def get_provider_capabilities(provider: str) -> ProviderCapabilities:
    """Get capabilities for a provider.

    Args:
        provider: Provider name (anthropic, openai, etc)

    Returns:
        ProviderCapabilities for the provider, or defaults if not found
    """
    return PROVIDER_CAPABILITIES.get(provider, ProviderCapabilities())
