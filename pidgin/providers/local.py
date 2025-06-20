"""Local model provider for offline inference."""
import asyncio
import json
import hashlib
from pathlib import Path
from typing import List, Optional, AsyncGenerator
from .base import Provider
from ..core.types import Message


class LocalProvider(Provider):
    """Provider that uses local inference instead of API calls."""
    
    def __init__(self, model_name: str = "test"):
        """Initialize local provider.
        
        Args:
            model_name: Name of local model (e.g., "test", "qwen-0.5b")
        """
        self.model_name = model_name
        self._model = None
        
    async def stream_response(
        self,
        messages: List[Message],
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from local model.
        
        Maintains exact same interface as API providers.
        """
        # For phase 1, only support test model
        if self.model_name != "test":
            raise ValueError(
                f"Model '{self.model_name}' not yet supported. "
                "Currently only 'test' model is available."
            )
            
        # Lazy load the test model
        if self._model is None:
            from ..local.test_model import TestModel
            self._model = TestModel()
            
        # Generate response
        response = await self._model.generate(messages, temperature)
        
        # Simulate streaming by splitting into words
        words = response.split()
        for i, word in enumerate(words):
            if i > 0:
                yield " "
            yield word
            # Small delay to simulate inference time
            await asyncio.sleep(0.01)