# pidgin/cli/model_selector.py
"""Interactive model selection for CLI."""

from typing import Dict, List, Optional, Tuple

from rich.console import Console

from ..config.models import MODELS, ModelConfig
from ..ui.display_utils import DisplayUtils
from .constants import MODEL_GLYPHS, NORD_BLUE
from .helpers import check_ollama_available, validate_model_id


class ModelSelector:
    """Handle interactive model selection and validation."""

    def __init__(self):
        self.console = Console()
        self.display = DisplayUtils(self.console)

    def select_model(self, prompt: str) -> Optional[str]:
        """Interactive model selection.

        Args:
            prompt: The prompt text to display to the user

        Returns:
            Selected model ID or None if cancelled
        """
        self.display.info(prompt, use_panel=False)

        providers = self.get_available_models()

        # Show available models
        idx = 1
        model_map = {}

        for provider in ["openai", "anthropic", "google", "xai", "local"]:
            if provider not in providers:
                continue

            # Show provider section
            self.display.dim(f"\n{provider.title()}:")

            for model_id, config in providers[provider]:
                glyph = MODEL_GLYPHS.get(model_id, "●")
                self.display.dim(f"  {idx}. {glyph} {config.display_name}")
                model_map[str(idx)] = model_id
                idx += 1

        self.display.dim("\nOther:")
        self.display.dim(f"  {idx}. ▸ Custom local model (requires Ollama)")

        try:
            selection = self.console.input(
                f"\n[{NORD_BLUE}]Enter selection (1-{idx}) "
                f"or model name: [/{NORD_BLUE}]"
            )
        except (KeyboardInterrupt, EOFError):
            return None

        if selection in model_map:
            return model_map[selection]
        elif selection == str(idx):
            # Custom local model
            return self.prompt_for_custom_model()
        else:
            # Try as direct model ID
            try:
                validated_id, display_name = validate_model_id(selection)
                return validated_id
            except ValueError:
                self.display.error("Invalid selection", use_panel=False)
                return None

    def validate_models(self, agent_a: str, agent_b: str) -> None:
        """Validate both model IDs.

        Args:
            agent_a: First agent model ID
            agent_b: Second agent model ID

        Raises:
            ValueError: If either model is invalid
        """
        # Validate each model
        validate_model_id(agent_a)
        validate_model_id(agent_b)

    def get_available_models(self) -> Dict[str, List[Tuple[str, ModelConfig]]]:
        """Get models grouped by provider.

        Returns:
            Dictionary mapping provider names to lists of (model_id, config) tuples
        """
        providers: Dict[str, List[Tuple[str, ModelConfig]]] = {}
        for model_id, config in MODELS.items():
            if model_id == "silent":  # Skip silent model in normal selection
                continue
            if config.provider not in providers:
                providers[config.provider] = []
            providers[config.provider].append((model_id, config))
        return providers

    def prompt_for_custom_model(self) -> Optional[str]:
        """Prompt for custom local model.

        Returns:
            Model ID in format "local:modelname" or None if cancelled
        """
        if not check_ollama_available():
            self.display.error(
                "Ollama is not running. Start it with 'ollama serve'", use_panel=False
            )
            return None

        try:
            model_name = self.console.input(
                f"[{NORD_BLUE}]Enter local model name: [/{NORD_BLUE}]"
            )
        except (KeyboardInterrupt, EOFError):
            return None

        return f"local:{model_name}"
