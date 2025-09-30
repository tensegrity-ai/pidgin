"""JSON-based model loader with user override support."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ..io.directories import get_data_dir
from .model_types import ModelConfig

logger = logging.getLogger(__name__)

# Supported schema versions for compatibility
SUPPORTED_SCHEMA_VERSIONS = ["1.0.0", "1.1.0"]


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
                logger.warning(f"Failed to load user models from {user_models_path}: {e}")
                json_path = None
        
        # Fall back to package data
        if json_path is None and package_models_path.exists():
            try:
                json_path = package_models_path
                data = self._load_json_file(package_models_path)
                logger.debug(f"Loaded package model data from {package_models_path}")
            except Exception as e:
                logger.error(f"Failed to load package models from {package_models_path}: {e}")
                # Fall back to empty data rather than crashing
                data = self._get_fallback_data()
        elif json_path is None:
            # No JSON files found, use fallback
            logger.warning("No models.json found, using minimal fallback data")
            data = self._get_fallback_data()
        
        # Validate and potentially migrate schema
        data = self._validate_and_migrate(data)
        
        # Convert to ModelConfig objects
        self._models_cache = self._convert_to_model_configs(data)

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
        with open(path, 'r') as f:
            return json.load(f)

    def _validate_and_migrate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate schema version and migrate if needed.
        
        Args:
            data: Raw JSON data
            
        Returns:
            Validated/migrated data
            
        Raises:
            ValueError: If schema version is unsupported
        """
        schema_version = data.get("schema_version", "0.0.0")
        
        if schema_version in SUPPORTED_SCHEMA_VERSIONS:
            return data
        
        # Check if we can migrate from an older version
        if self._can_migrate(schema_version):
            logger.info(f"Migrating schema from {schema_version}")
            return self._migrate_schema(data, schema_version)
        
        raise ValueError(
            f"Unsupported schema version: {schema_version}. "
            f"Supported versions: {SUPPORTED_SCHEMA_VERSIONS}"
        )

    def _can_migrate(self, version: str) -> bool:
        """Check if we can migrate from a given schema version.
        
        Args:
            version: Schema version to check
            
        Returns:
            True if migration is possible
        """
        # Add migration logic for specific versions here
        # For now, we don't support any migrations
        return False

    def _migrate_schema(self, data: Dict[str, Any], from_version: str) -> Dict[str, Any]:
        """Migrate data from an older schema version.
        
        Args:
            data: Data to migrate
            from_version: Current schema version
            
        Returns:
            Migrated data
        """
        # Implement migration logic here when needed
        raise NotImplementedError(f"Migration from {from_version} not implemented")

    def _convert_to_model_configs(self, data: Dict[str, Any]) -> Dict[str, ModelConfig]:
        """Convert JSON data to ModelConfig objects.
        
        Args:
            data: Validated JSON data
            
        Returns:
            Dictionary of model_id to ModelConfig
        """
        models = {}
        models_data = data.get("models", {})
        
        for model_id, config in models_data.items():
            try:
                # Map JSON fields to ModelConfig fields
                model_config = ModelConfig(
                    model_id=model_id,
                    display_name=config.get("display_name", model_id),
                    aliases=config.get("aliases", []),  # Read aliases directly from model config
                    provider=config["provider"],
                    context_window=config.get("context_window", 4096),
                    created_at=config.get("created_at"),
                    deprecated=config.get("deprecated", False),
                    notes=config.get("notes"),
                    input_cost_per_million=config.get("pricing", {}).get("input"),
                    output_cost_per_million=config.get("pricing", {}).get("output"),
                    supports_caching=config.get("supports_caching", False),
                    cache_read_cost_per_million=config.get("pricing", {}).get("cache_read"),
                    cache_write_cost_per_million=config.get("pricing", {}).get("cache_write"),
                    pricing_updated=config.get("pricing_updated"),
                    curated=config.get("curated", False),
                    stable=config.get("stable", False),
                )
                
                models[model_id] = model_config
            except KeyError as e:
                logger.warning(f"Skipping model {model_id}: missing required field {e}")
            except Exception as e:
                logger.warning(f"Skipping model {model_id}: {e}")
        
        return models

    def _get_fallback_data(self) -> Dict[str, Any]:
        """Get minimal fallback data when no JSON files are available.
        
        Returns:
            Minimal valid data structure
        """
        return {
            "schema_version": "1.0.0",
            "generated_at": "2025-01-01T00:00:00Z",
            "models": {
                # Minimal set of models for backward compatibility
                "local:test": {
                    "provider": "local",
                    "display_name": "Local Test",
                    "context_window": 100000,
                    "notes": "Test model for development"
                },
                "silent:none": {
                    "provider": "silent",
                    "display_name": "Silent",
                    "context_window": 100000,
                    "notes": "Silent model that returns empty responses"
                }
            },
            "aliases": {
                "test": "local:test",
                "silent": "silent:none",
                "none": "silent:none"
            }
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