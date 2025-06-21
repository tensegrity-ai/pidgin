# pidgin/providers/silent.py
"""Silent provider for meditation mode."""

from typing import List, Optional, AsyncGenerator
from ..core.types import Message
from .base import Provider


class SilentProvider(Provider):
    """A provider that returns only silence."""
    
    def __init__(self, model: str):
        """Initialize silent provider.
        
        Args:
            model: Model ID (ignored, always silent)
        """
        self.model = model
    
    async def stream_response(
        self, 
        messages: List[Message], 
        temperature: Optional[float] = None
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