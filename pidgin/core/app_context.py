"""Application context for dependency injection."""

from pathlib import Path
from typing import Dict, Optional

from ..config.config import Config
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

        # Load model registry
        self.models = self._load_models()

    def _load_models(self) -> Dict[str, ModelConfig]:
        """Load model configurations from all providers.

        Returns:
            Dictionary mapping model IDs to their configurations
        """
        models = {}

        # Import provider models - use lazy imports to avoid circular dependencies
        try:
            from ..providers.anthropic import ANTHROPIC_MODELS

            models.update(ANTHROPIC_MODELS)
        except ImportError:
            pass

        try:
            from ..providers.openai import OPENAI_MODELS

            models.update(OPENAI_MODELS)
        except ImportError:
            pass

        try:
            from ..providers.google import GOOGLE_MODELS

            models.update(GOOGLE_MODELS)
        except ImportError:
            pass

        try:
            from ..providers.xai import XAI_MODELS

            models.update(XAI_MODELS)
        except ImportError:
            pass

        try:
            from ..providers.local import LOCAL_MODELS

            models.update(LOCAL_MODELS)
        except ImportError:
            pass

        try:
            from ..providers.ollama import OLLAMA_MODELS

            models.update(OLLAMA_MODELS)
        except ImportError:
            pass

        try:
            from ..providers.silent import SILENT_MODELS

            models.update(SILENT_MODELS)
        except ImportError:
            pass

        return models

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
