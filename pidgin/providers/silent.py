# pidgin/providers/silent.py
"""Silent provider for meditation mode."""

from typing import AsyncGenerator, List, Optional

# Import model config classes from central location
from ..config.models import ModelCharacteristics, ModelConfig
from ..core.types import Message
from .base import Provider

# Silent model definitions
SILENT_MODELS = {
    "silent": ModelConfig(
        model_id="silent",
        shortname="Silence",
        aliases=["void", "quiet", "meditation"],
        provider="silent",
        context_window=999999,  # Infinite patience
        pricing_tier="free",
        characteristics=ModelCharacteristics(
            verbosity_level=0,
            avg_response_length="short",  # Always empty
            recommended_pairings=["claude-4-opus-20250514", "gpt-4.1", "o1"],
            conversation_style="concise",  # The ultimate conciseness
        ),
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
