# pidgin/providers/silent.py
"""Silent provider for meditation mode."""

from collections.abc import AsyncGenerator
from typing import List, Optional

# Import model config classes from central location
from ..config.model_types import ModelConfig
from ..core.types import Message
from .base import Provider

# Silent model definitions
SILENT_MODELS = {
    "silent": ModelConfig(
        model_id="silent",
        display_name="Silence",
        aliases=["void", "quiet", "meditation"],
        provider="silent",
        context_window=999999,  # Infinite patience
        notes="A special model that returns only silence for meditation mode",
    ),
}


class SilentProvider(Provider):
    """A provider that returns only silence."""

    def __init__(self, model: str):
        """Initialize silent provider.

        Args:
            model: Model ID (ignored, always silent)
        """
        super().__init__()
        self.model = model

    async def stream_response(
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Return empty response - pure silence.

        Args:
            messages: Conversation history (ignored)
            temperature: Temperature setting (ignored)

        Yields:
            Empty string representing silence
        """
        # Return nothing - the sound of one hand clapping
        yield ""
