from abc import ABC, abstractmethod
from typing import List, AsyncIterator, AsyncGenerator, Optional
from ..core.types import Message


class Provider(ABC):
    @abstractmethod
    async def stream_response(
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks from the model
        
        Args:
            messages: Conversation messages
            temperature: Optional temperature setting (0.0-2.0)
                        Provider-specific limits may apply
        """
        yield  # type: ignore[misc]
        pass
