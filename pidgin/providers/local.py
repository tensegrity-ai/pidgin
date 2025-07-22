"""Local model provider for test model only."""

import asyncio
from typing import AsyncGenerator, List, Optional

# Import model config classes from central location
from ..config.models import ModelConfig
from ..core.types import Message
from .base import Provider

# Local model definitions
LOCAL_MODELS = {
    "local:test": ModelConfig(
        model_id="local:test",
        display_name="Test",
        aliases=["test", "local-test"],
        provider="local",
        context_window=8192,
        notes="Deterministic test model for offline development",
    ),
}


class LocalProvider(Provider):
    """Provider for the local test model."""

    def __init__(self, model_name: str = "test"):
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
