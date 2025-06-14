from abc import ABC, abstractmethod
from typing import List, AsyncIterator, AsyncGenerator
from ..types import Message


class Provider(ABC):
    @abstractmethod
    async def stream_response(
        self, messages: List[Message]
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks from the model"""
        yield  # type: ignore[misc]
        pass
