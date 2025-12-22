"""Application context for dependency injection."""

from pathlib import Path
from typing import Optional

from ..config.config import Config
from ..config.model_loader import load_models
from ..config.model_types import ModelConfig
from ..providers.token_tracker import GlobalTokenTracker


class AppContext:
    """Application-wide context holding all shared dependencies.

    This class serves as a dependency injection container, eliminating
    the need for global state throughout the application.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize application context with all dependencies.

        Args:
            config_path: Optional path to configuration file
        """
        # Initialize configuration
        self.config = Config(config_path)

        # Initialize token tracker with config
        self.token_tracker = GlobalTokenTracker(self.config)

        # Load model registry from JSON (single source of truth)
        self.models = load_models()

    def get_model_config(self, model_or_alias: str) -> Optional[ModelConfig]:
        """Get model configuration by ID or alias.

        Args:
            model_or_alias: Model ID or alias

        Returns:
            Model configuration if found, None otherwise
        """
        # Direct match
        if model_or_alias in self.models:
            return self.models[model_or_alias]

        # Search by alias
        for model_id, config in self.models.items():
            if model_or_alias in config.aliases:
                return config

        return None
