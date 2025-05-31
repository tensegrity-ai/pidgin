from abc import ABC, abstractmethod
from typing import List
from ..types import Message


class Provider(ABC):
    @abstractmethod
    async def get_response(self, messages: List[Message]) -> str:
        """Get response from the model given conversation history"""
        pass