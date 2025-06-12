from abc import ABC, abstractmethod
from typing import List, AsyncIterator
from ..types import Message


class Provider(ABC):
    @abstractmethod
    async def stream_response(self, messages: List[Message]) -> AsyncIterator[str]:
        """Stream response chunks from the model"""
        pass