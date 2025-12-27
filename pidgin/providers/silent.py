# pidgin/providers/silent.py
"""Silent provider for meditation mode."""

from collections.abc import AsyncGenerator
from typing import List, Optional

from ..core.types import Message
from .base import Provider, ResponseChunk


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
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        thinking_enabled: Optional[bool] = None,
        thinking_budget: Optional[int] = None,
    ) -> AsyncGenerator[ResponseChunk, None]:
        """Return empty response - pure silence.

        Args:
            messages: Conversation history (ignored)
            temperature: Temperature setting (ignored)
            thinking_enabled: Thinking mode (ignored)
            thinking_budget: Thinking budget (ignored)

        Yields:
            Empty ResponseChunk representing silence
        """
        # Return nothing - the sound of one hand clapping
        yield ResponseChunk("", "response")
