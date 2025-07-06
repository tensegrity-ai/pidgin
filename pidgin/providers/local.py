"""Local model provider for test model only."""
import asyncio
from typing import List, Optional, AsyncGenerator
from .base import Provider
from ..core.types import Message

# Import model config classes from central location
from ..config.models import ModelConfig, ModelCharacteristics

# Local model definitions
LOCAL_MODELS = {
    "local:test": ModelConfig(
        model_id="local:test",
        shortname="TestModel",
        aliases=["test", "local-test"],
        provider="local",
        context_window=8192,
        pricing_tier="free",
        characteristics=ModelCharacteristics(
            verbosity_level=5,
            avg_response_length="medium",
            recommended_pairings=["local:test", "gpt-4o-mini"],
            conversation_style="analytical",
        ),
        notes="Deterministic test model for offline development",
    ),
}


class LocalProvider(Provider):
    """Provider for the local test model."""
    
    def __init__(self, model_name: str = "test"):
        self.model_name = model_name
        
    async def stream_response(
        self,
        messages: List[Message],
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from test model."""
        if self.model_name != "test":
            yield f"Error: LocalProvider only supports 'test' model. Got: {self.model_name}"
            return
            
        from ..local.test_model import LocalTestModel
        model = LocalTestModel()
        response = await model.generate(messages, temperature)
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.01)