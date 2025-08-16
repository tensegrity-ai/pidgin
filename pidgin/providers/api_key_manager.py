"""Simple API key management for all providers."""

import os
from typing import List

from ..core.constants import EnvVars, ProviderNames


class APIKeyError(Exception):
    """Raised when API key is missing or invalid."""


class APIKeyManager:
    """Simple manager for provider API keys."""

    # Map provider names to their environment variable names
    PROVIDER_ENV_VARS = {
        ProviderNames.ANTHROPIC: EnvVars.ANTHROPIC_API_KEY,
        ProviderNames.OPENAI: EnvVars.OPENAI_API_KEY,
        ProviderNames.GOOGLE: EnvVars.GOOGLE_API_KEY,
        ProviderNames.XAI: EnvVars.XAI_API_KEY,
        # Aliases for backward compatibility
        "gemini": EnvVars.GEMINI_API_KEY,  # Alias for google
        "grok": EnvVars.GROK_API_KEY,  # Alias for xai
    }

    # Providers that don't require API keys
    NO_KEY_PROVIDERS = {
        ProviderNames.LOCAL,
        ProviderNames.OLLAMA,
        ProviderNames.SILENT,
        "test",  # For local:test model
    }

    @staticmethod
    def get_api_key(provider: str) -> str:
        """Get API key from environment with helpful error messages.

        Args:
            provider: Provider name (e.g., 'anthropic', 'openai')

        Returns:
            API key string

        Raises:
            APIKeyError: If API key is missing
        """
        # Normalize provider name
        provider = provider.lower()

        # Skip providers that don't need keys
        if provider in APIKeyManager.NO_KEY_PROVIDERS:
            return ""

        # Get environment variable name
        env_var = APIKeyManager.PROVIDER_ENV_VARS.get(provider)
        if not env_var:
            # Fallback for unknown providers
            env_var = f"{provider.upper()}_API_KEY"

        # Get key from environment
        key = os.getenv(env_var)

        if not key:
            raise APIKeyError(
                f"Missing API key for {provider.upper()} provider\n\n"
                f"Please set the {env_var} environment variable:\n"
                f"  export {env_var}=your-api-key\n\n"
                f"For keychain integration:\n"
                "  https://github.com/anthropics/pidgin#api-keys"
            )

        return key

    @staticmethod
    def validate_required_providers(providers: List[str]) -> None:
        """Check all required providers have keys before starting experiment.

        Args:
            providers: List of provider names to validate

        Raises:
            APIKeyError: If any required API keys are missing
        """
        missing = []

        for provider in providers:
            if provider.lower() in APIKeyManager.NO_KEY_PROVIDERS:
                continue

            try:
                APIKeyManager.get_api_key(provider)
            except APIKeyError:
                missing.append(provider)

        if missing:
            env_vars = []
            for provider in missing:
                env_var = APIKeyManager.PROVIDER_ENV_VARS.get(
                    provider.lower(), f"{provider.upper()}_API_KEY"
                )
                env_vars.append(f"{provider}: {env_var}")

            raise APIKeyError(
                f"Missing API keys for {len(missing)} provider{'s' if len(missing) > 1 else ''}:\n\n"
                + "\n".join(
                    f"  • {provider.upper()}: Set {env_var}"
                    for provider, env_var in [
                        (
                            p,
                            APIKeyManager.PROVIDER_ENV_VARS.get(
                                p.lower(), f"{p.upper()}_API_KEY"
                            ),
                        )
                        for p in missing
                    ]
                )
                + "\n\n"
                "Export the required environment variables:\n"
                + "\n".join(
                    f"  export {env_var}=your-{provider}-api-key"
                    for provider, env_var in [
                        (
                            p,
                            APIKeyManager.PROVIDER_ENV_VARS.get(
                                p.lower(), f"{p.upper()}_API_KEY"
                            ),
                        )
                        for p in missing
                    ]
                )
                + "\n\n"
                "For keychain integration:\n"
                "  https://github.com/anthropics/pidgin#api-keys"
            )
