"""Local model provider for test model only."""

import asyncio
from collections.abc import AsyncGenerator
from typing import List, Optional

from ..core.types import Message
from .base import Provider


class LocalProvider(Provider):
    """Provider for the local test model."""

    def __init__(self, model_name: str = "test"):
        super().__init__()
        self.model_name = model_name

    async def stream_response(
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from test model."""
        if self.model_name != "test":
            yield f"Error: LocalProvider only supports 'test' model. Got: {self.model_name}"
            return

        from .test_model import LocalTestModel

        model = LocalTestModel()
        response = await model.generate(messages, temperature)
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.01)
