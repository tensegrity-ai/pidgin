"""JSON-based model loader with user override support."""

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
        user_models_path = get_data_dir() / "models.json"
        package_models_path = Path(__file__).parent.parent / "data" / "models.json"

        data = None

        # Try user override first (full replacement)
        if user_models_path.exists():
            try:
                data = self._load_json_file(user_models_path)
                logger.info(f"Loaded user model data from {user_models_path}")
            except Exception as e:
                logger.warning(
                    f"Failed to load user models from {user_models_path}: {e}"
                )

        # Fall back to package data
        if data is None and package_models_path.exists():
            try:
                data = self._load_json_file(package_models_path)
                logger.debug(f"Loaded package model data from {package_models_path}")
            except Exception as e:
                logger.error(
                    f"Failed to load package models from {package_models_path}: {e}"
                )
                data = self._get_fallback_data()
        elif data is None:
            logger.warning("No models.json found, using minimal fallback data")
            data = self._get_fallback_data()

        # Convert to ModelConfig objects
        self._models_cache = self._convert_to_model_configs(data)

        # Build aliases cache from inline aliases in each model
        self._aliases_cache = {}
        for model_id, model_config in self._models_cache.items():
            for alias in model_config.aliases:
                self._aliases_cache[alias] = model_id

        self._raw_data_cache = data

    def _load_json_file(self, path: Path) -> Dict[str, Any]:
        """Load and parse a JSON file."""
        with open(path, "r") as f:
            return json.load(f)

    def _convert_to_model_configs(self, data: Dict[str, Any]) -> Dict[str, ModelConfig]:
        """Convert JSON data to ModelConfig objects."""
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

    def _get_fallback_data(self) -> Dict[str, Any]:
        """Get minimal fallback data when no JSON files are available."""
        return {
            "schema_version": "2.0.0",
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
                    },
                    "limits": {"max_context_tokens": 100000},
                    "metadata": {"stable": True, "notes": "Test model for development"},
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
                    },
                    "limits": {"max_context_tokens": 100000},
                    "metadata": {"stable": True, "notes": "Returns empty responses"},
                },
            },
        }


# Global singleton instance
_loader = ModelLoader()


def load_models() -> Dict[str, ModelConfig]:
    """Load all model configurations."""
    return _loader.load_models()


def get_aliases() -> Dict[str, str]:
    """Get all alias to model_id mappings."""
    return _loader.get_aliases()


def resolve_alias(name: str) -> Optional[str]:
    """Resolve an alias or model name to its model_id."""
    return _loader.resolve_alias(name)


def get_model_config(model_or_alias: str) -> Optional[ModelConfig]:
    """Get model configuration by ID or alias."""
    model_id = resolve_alias(model_or_alias)
    if model_id:
        models = load_models()
        return models.get(model_id)
    return None
