"""JSON-based model loader with user override support.

Supports both v1 and v2 schema formats with automatic migration.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ..io.directories import get_data_dir
from .model_types import (
    ApiConfig,
    Capabilities,
    Cost,
    Limits,
    Metadata,
    ModelConfig,
    Parameters,
    ParameterSpec,
    RateLimits,
)

logger = logging.getLogger(__name__)

# Supported schema versions for compatibility
SUPPORTED_SCHEMA_VERSIONS = ["1.0.0", "1.1.0", "2.0.0"]


class ModelLoader:
    """Loads model configurations from JSON files with user override support."""

    def __init__(self):
        """Initialize the model loader."""
        self._models_cache: Optional[Dict[str, ModelConfig]] = None
        self._aliases_cache: Optional[Dict[str, str]] = None
        self._raw_data_cache: Optional[Dict[str, Any]] = None

    def load_models(self) -> Dict[str, ModelConfig]:
        """Load models from JSON, with user override support.

        Returns:
            Dictionary mapping model_id to ModelConfig objects
        """
        if self._models_cache is None:
            self._load_data()
        return self._models_cache

    def get_aliases(self) -> Dict[str, str]:
        """Get alias to model_id mappings.

        Returns:
            Dictionary mapping alias to model_id
        """
        if self._aliases_cache is None:
            self._load_data()
        return self._aliases_cache

    def resolve_alias(self, name: str) -> Optional[str]:
        """Resolve an alias to a model ID (case-insensitive).

        Args:
            name: Alias or model ID to resolve

        Returns:
            Resolved model_id or None if not found
        """
        if self._aliases_cache is None:
            self._load_data()

        # Case-insensitive alias lookup
        name_lower = name.lower()
        for alias, model_id in self._aliases_cache.items():
            if alias.lower() == name_lower:
                return model_id

        # Check if it's a direct model ID (case-insensitive)
        for model_id in self._models_cache.keys():
            if model_id.lower() == name_lower:
                return model_id

        return None

    def _load_data(self) -> None:
        """Load and cache model data from JSON files."""
        # Determine which file to load
        user_models_path = get_data_dir() / "models.json"
        package_models_path = Path(__file__).parent.parent / "data" / "models.json"

        json_path = None

        # Try user override first (full replacement)
        if user_models_path.exists():
            try:
                json_path = user_models_path
                data = self._load_json_file(user_models_path)
                logger.info(f"Loaded user model data from {user_models_path}")
            except Exception as e:
                logger.warning(
                    f"Failed to load user models from {user_models_path}: {e}"
                )
                json_path = None

        # Fall back to package data
        if json_path is None and package_models_path.exists():
            try:
                json_path = package_models_path
                data = self._load_json_file(package_models_path)
                logger.debug(f"Loaded package model data from {package_models_path}")
            except Exception as e:
                logger.error(
                    f"Failed to load package models from {package_models_path}: {e}"
                )
                # Fall back to empty data rather than crashing
                data = self._get_fallback_data()
        elif json_path is None:
            # No JSON files found, use fallback
            logger.warning("No models.json found, using minimal fallback data")
            data = self._get_fallback_data()

        # Validate schema version
        schema_version = data.get("schema_version", "1.0.0")
        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(
                f"Unsupported schema version: {schema_version}. "
                f"Supported versions: {SUPPORTED_SCHEMA_VERSIONS}"
            )

        # Convert to ModelConfig objects based on schema version
        if schema_version.startswith("2."):
            self._models_cache = self._convert_v2_to_model_configs(data)
        else:
            self._models_cache = self._convert_v1_to_model_configs(data)

        # Build aliases cache from inline aliases in each model
        self._aliases_cache = {}
        for model_id, model_config in self._models_cache.items():
            for alias in model_config.aliases:
                self._aliases_cache[alias] = model_id

        self._raw_data_cache = data

    def _load_json_file(self, path: Path) -> Dict[str, Any]:
        """Load and parse a JSON file.

        Args:
            path: Path to the JSON file

        Returns:
            Parsed JSON data

        Raises:
            Exception: If file cannot be read or parsed
        """
        with open(path, "r") as f:
            return json.load(f)

    def _convert_v1_to_model_configs(
        self, data: Dict[str, Any]
    ) -> Dict[str, ModelConfig]:
        """Convert v1 JSON data to ModelConfig objects.

        Args:
            data: Validated v1 JSON data

        Returns:
            Dictionary of model_id to ModelConfig
        """
        models = {}
        models_data = data.get("models", {})

        for model_id, config in models_data.items():
            try:
                # Extract pricing
                pricing = config.get("pricing", {})
                cost = None
                if (
                    pricing.get("input") is not None
                    or pricing.get("output") is not None
                ):
                    input_cost = pricing.get("input", 0)
                    output_cost = pricing.get("output", 0)
                    # Only create Cost if there's actual pricing
                    if input_cost > 0 or output_cost > 0:
                        cost = Cost(
                            input_per_1m_tokens=input_cost,
                            output_per_1m_tokens=output_cost,
                            cache_read_per_1m_tokens=pricing.get("cache_read"),
                            cache_write_per_1m_tokens=pricing.get("cache_write"),
                            last_updated=config.get("pricing_updated"),
                        )

                # Determine provider
                provider = config["provider"]

                # Build capabilities with reasonable defaults based on provider
                # This is the v1 -> v2 migration logic
                capabilities = self._infer_capabilities_from_v1(provider, config)

                # Build limits
                context_window = config.get("context_window", 4096)
                limits = Limits(
                    max_context_tokens=context_window,
                    max_output_tokens=None,  # v1 didn't track this separately
                    max_thinking_tokens=None,
                )

                # Build parameters with provider defaults
                parameters = self._infer_parameters_from_provider(provider)

                # Build API config
                api = ApiConfig(
                    model_id=config.get("api_id", model_id),
                    ollama_model=config.get("ollama_model"),
                )

                # Build metadata
                metadata = Metadata(
                    status="deprecated" if config.get("deprecated") else "available",
                    curated=config.get("curated", False),
                    stable=config.get("stable", False),
                    release_date=config.get("created_at"),
                    deprecation_date=config.get("deprecation_date"),
                    notes=config.get("notes"),
                    size=config.get("size"),
                )

                # Build rate limits from provider defaults
                rate_limits = self._infer_rate_limits_from_provider(provider)

                model_config = ModelConfig(
                    model_id=model_id,
                    provider=provider,
                    display_name=config.get("display_name", model_id),
                    aliases=config.get("aliases", []),
                    api=api,
                    capabilities=capabilities,
                    limits=limits,
                    parameters=parameters,
                    cost=cost,
                    metadata=metadata,
                    rate_limits=rate_limits,
                )

                models[model_id] = model_config
            except KeyError as e:
                logger.warning(f"Skipping model {model_id}: missing required field {e}")
            except Exception as e:
                logger.warning(f"Skipping model {model_id}: {e}")

        return models

    def _convert_v2_to_model_configs(
        self, data: Dict[str, Any]
    ) -> Dict[str, ModelConfig]:
        """Convert v2 JSON data to ModelConfig objects.

        Args:
            data: Validated v2 JSON data

        Returns:
            Dictionary of model_id to ModelConfig
        """
        models = {}
        models_data = data.get("models", {})

        for model_id, config in models_data.items():
            try:
                # API config
                api_data = config.get("api", {})
                api = ApiConfig(
                    model_id=api_data.get("model_id", model_id),
                    ollama_model=api_data.get("ollama_model"),
                    api_version=api_data.get("api_version"),
                )

                # Capabilities
                caps_data = config.get("capabilities", {})
                capabilities = Capabilities(
                    streaming=caps_data.get("streaming", True),
                    vision=caps_data.get("vision", False),
                    tool_calling=caps_data.get("tool_calling", False),
                    system_messages=caps_data.get("system_messages", True),
                    extended_thinking=caps_data.get("extended_thinking", False),
                    json_mode=caps_data.get("json_mode", False),
                    prompt_caching=caps_data.get("prompt_caching", False),
                )

                # Limits
                limits_data = config.get("limits", {})
                limits = Limits(
                    max_context_tokens=limits_data.get("max_context_tokens"),
                    max_output_tokens=limits_data.get("max_output_tokens"),
                    max_thinking_tokens=limits_data.get("max_thinking_tokens"),
                )

                # Parameters
                params_data = config.get("parameters", {})
                parameters = Parameters(
                    temperature=self._parse_parameter_spec(
                        params_data.get("temperature", {})
                    ),
                    top_p=self._parse_parameter_spec(params_data.get("top_p", {})),
                    top_k=self._parse_parameter_spec(params_data.get("top_k", {})),
                )

                # Cost
                cost = None
                cost_data = config.get("cost")
                if cost_data:
                    cost = Cost(
                        input_per_1m_tokens=cost_data["input_per_1m_tokens"],
                        output_per_1m_tokens=cost_data["output_per_1m_tokens"],
                        currency=cost_data.get("currency", "USD"),
                        last_updated=cost_data.get("last_updated"),
                        cache_read_per_1m_tokens=cost_data.get(
                            "cache_read_per_1m_tokens"
                        ),
                        cache_write_per_1m_tokens=cost_data.get(
                            "cache_write_per_1m_tokens"
                        ),
                    )

                # Metadata
                meta_data = config.get("metadata", {})
                metadata = Metadata(
                    status=meta_data.get("status", "available"),
                    curated=meta_data.get("curated", False),
                    stable=meta_data.get("stable", False),
                    release_date=meta_data.get("release_date"),
                    deprecation_date=meta_data.get("deprecation_date"),
                    description=meta_data.get("description"),
                    notes=meta_data.get("notes"),
                    size=meta_data.get("size"),
                )

                # Rate limits
                rate_limits = None
                rl_data = config.get("rate_limits")
                if rl_data:
                    rate_limits = RateLimits(
                        requests_per_minute=rl_data["requests_per_minute"],
                        tokens_per_minute=rl_data["tokens_per_minute"],
                    )

                model_config = ModelConfig(
                    model_id=model_id,
                    provider=config["provider"],
                    display_name=config.get("display_name", model_id),
                    aliases=config.get("aliases", []),
                    api=api,
                    capabilities=capabilities,
                    limits=limits,
                    parameters=parameters,
                    cost=cost,
                    metadata=metadata,
                    rate_limits=rate_limits,
                )

                models[model_id] = model_config
            except KeyError as e:
                logger.warning(f"Skipping model {model_id}: missing required field {e}")
            except Exception as e:
                logger.warning(f"Skipping model {model_id}: {e}")

        return models

    def _parse_parameter_spec(self, data: Dict[str, Any]) -> ParameterSpec:
        """Parse a parameter specification from JSON data."""
        if not data:
            return ParameterSpec(supported=False)

        return ParameterSpec(
            supported=data.get("supported", False),
            range=data.get("range"),
            default=data.get("default"),
        )

    def _infer_capabilities_from_v1(
        self, provider: str, config: Dict[str, Any]
    ) -> Capabilities:
        """Infer capabilities for v1 models based on provider.

        This provides reasonable defaults during migration from v1 to v2.
        """
        # Check for explicit capability flags in v1 data
        supports_vision = config.get("supports_vision", False)
        supports_tools = config.get("supports_tools", False)
        supports_caching = config.get("supports_caching", False)

        # Provider-based defaults (used if not explicitly set)
        if provider == "anthropic":
            return Capabilities(
                streaming=True,
                vision=supports_vision or True,  # Most Claude models have vision
                tool_calling=supports_tools or True,
                system_messages=True,
                extended_thinking=False,  # Needs explicit opt-in
                json_mode=False,
                prompt_caching=supports_caching or True,
            )
        elif provider == "openai":
            model_id = config.get("model_id", "")
            is_o_series = (
                model_id.startswith("o1")
                or model_id.startswith("o3")
                or model_id.startswith("o4")
            )
            return Capabilities(
                streaming=not is_o_series,  # o-series don't stream
                vision=supports_vision or True,  # Most GPT-4+ have vision
                tool_calling=supports_tools or True,
                system_messages=True,
                extended_thinking=is_o_series,
                json_mode=True,
                prompt_caching=False,
            )
        elif provider == "google":
            return Capabilities(
                streaming=True,
                vision=supports_vision or True,
                tool_calling=supports_tools or True,
                system_messages=True,
                extended_thinking=False,
                json_mode=True,
                prompt_caching=False,
            )
        elif provider == "xai":
            return Capabilities(
                streaming=True,
                vision=supports_vision,
                tool_calling=supports_tools,
                system_messages=True,
                extended_thinking=False,
                json_mode=False,
                prompt_caching=False,
            )
        elif provider in ("ollama", "local"):
            return Capabilities(
                streaming=True,
                vision=False,
                tool_calling=False,
                system_messages=True,
                extended_thinking=False,
                json_mode=False,
                prompt_caching=False,
            )
        else:  # silent or unknown
            return Capabilities(
                streaming=False,
                vision=False,
                tool_calling=False,
                system_messages=True,
                extended_thinking=False,
                json_mode=False,
                prompt_caching=False,
            )

    def _infer_parameters_from_provider(self, provider: str) -> Parameters:
        """Infer parameter support based on provider."""
        if provider == "anthropic":
            return Parameters(
                temperature=ParameterSpec(
                    supported=True, range=[0.0, 1.0], default=1.0
                ),
                top_p=ParameterSpec(supported=True, range=[0.0, 1.0], default=None),
                top_k=ParameterSpec(supported=True, range=[0, 500], default=None),
            )
        elif provider == "openai":
            return Parameters(
                temperature=ParameterSpec(
                    supported=True, range=[0.0, 2.0], default=1.0
                ),
                top_p=ParameterSpec(supported=True, range=[0.0, 1.0], default=None),
                top_k=ParameterSpec(supported=False),
            )
        elif provider == "google":
            return Parameters(
                temperature=ParameterSpec(
                    supported=True, range=[0.0, 2.0], default=1.0
                ),
                top_p=ParameterSpec(supported=True, range=[0.0, 1.0], default=None),
                top_k=ParameterSpec(supported=True, range=[1, 40], default=None),
            )
        elif provider == "xai":
            return Parameters(
                temperature=ParameterSpec(
                    supported=True, range=[0.0, 2.0], default=1.0
                ),
                top_p=ParameterSpec(supported=True, range=[0.0, 1.0], default=None),
                top_k=ParameterSpec(supported=False),
            )
        elif provider == "ollama":
            return Parameters(
                temperature=ParameterSpec(
                    supported=True, range=[0.0, 2.0], default=0.8
                ),
                top_p=ParameterSpec(supported=True, range=[0.0, 1.0], default=None),
                top_k=ParameterSpec(supported=True, range=[1, 100], default=None),
            )
        else:  # local, silent, unknown
            return Parameters(
                temperature=ParameterSpec(supported=False),
                top_p=ParameterSpec(supported=False),
                top_k=ParameterSpec(supported=False),
            )

    def _infer_rate_limits_from_provider(self, provider: str) -> Optional[RateLimits]:
        """Infer rate limits based on provider."""
        limits_map = {
            "anthropic": RateLimits(requests_per_minute=50, tokens_per_minute=40000),
            "openai": RateLimits(requests_per_minute=60, tokens_per_minute=90000),
            "google": RateLimits(requests_per_minute=60, tokens_per_minute=60000),
            "xai": RateLimits(requests_per_minute=60, tokens_per_minute=60000),
        }
        return limits_map.get(provider)

    def _get_fallback_data(self) -> Dict[str, Any]:
        """Get minimal fallback data when no JSON files are available.

        Returns:
            Minimal valid data structure
        """
        return {
            "schema_version": "2.0.0",
            "generated_at": "2025-01-01T00:00:00Z",
            "models": {
                "local:test": {
                    "provider": "local",
                    "display_name": "Local Test",
                    "aliases": ["test"],
                    "api": {"model_id": "local:test"},
                    "capabilities": {
                        "streaming": True,
                        "vision": False,
                        "tool_calling": False,
                        "system_messages": True,
                        "extended_thinking": False,
                        "json_mode": False,
                        "prompt_caching": False,
                    },
                    "limits": {
                        "max_context_tokens": 100000,
                        "max_output_tokens": None,
                        "max_thinking_tokens": None,
                    },
                    "parameters": {
                        "temperature": {"supported": False},
                        "top_p": {"supported": False},
                        "top_k": {"supported": False},
                    },
                    "cost": None,
                    "metadata": {
                        "status": "available",
                        "curated": False,
                        "stable": True,
                        "notes": "Test model for development",
                    },
                    "rate_limits": None,
                },
                "silent:none": {
                    "provider": "silent",
                    "display_name": "Silent",
                    "aliases": ["silent", "none"],
                    "api": {"model_id": "silent:none"},
                    "capabilities": {
                        "streaming": False,
                        "vision": False,
                        "tool_calling": False,
                        "system_messages": True,
                        "extended_thinking": False,
                        "json_mode": False,
                        "prompt_caching": False,
                    },
                    "limits": {
                        "max_context_tokens": 100000,
                        "max_output_tokens": None,
                        "max_thinking_tokens": None,
                    },
                    "parameters": {
                        "temperature": {"supported": False},
                        "top_p": {"supported": False},
                        "top_k": {"supported": False},
                    },
                    "cost": None,
                    "metadata": {
                        "status": "available",
                        "curated": False,
                        "stable": True,
                        "notes": "Silent model that returns empty responses",
                    },
                    "rate_limits": None,
                },
            },
        }


# Global singleton instance
_loader = ModelLoader()


# Public API functions for backward compatibility
def load_models() -> Dict[str, ModelConfig]:
    """Load all model configurations.

    Returns:
        Dictionary mapping model_id to ModelConfig
    """
    return _loader.load_models()


def get_aliases() -> Dict[str, str]:
    """Get all alias to model_id mappings.

    Returns:
        Dictionary mapping alias to model_id
    """
    return _loader.get_aliases()


def resolve_alias(name: str) -> Optional[str]:
    """Resolve an alias or model name to its model_id.

    Args:
        name: Alias or model ID to resolve

    Returns:
        Resolved model_id or None if not found
    """
    return _loader.resolve_alias(name)


def get_model_config(model_or_alias: str) -> Optional[ModelConfig]:
    """Get model configuration by ID or alias.

    Args:
        model_or_alias: Model ID or alias

    Returns:
        ModelConfig or None if not found
    """
    model_id = resolve_alias(model_or_alias)
    if model_id:
        models = load_models()
        return models.get(model_id)
    return None
