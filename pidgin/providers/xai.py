import os
import logging
from typing import List, AsyncIterator, AsyncGenerator, Optional
from ..core.types import Message
from .base import Provider

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None


class xAIProvider(Provider):
    def __init__(self, model: str):
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI client not available. Install with: " "pip install openai"
            )

        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError(
                "XAI_API_KEY environment variable not set. "
                "Please set it to your xAI API key."
            )

        # xAI uses OpenAI-compatible API with custom base URL
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        self.model = model

    async def stream_response(
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        # Apply context management
        from .context_manager import ProviderContextManager
        context_mgr = ProviderContextManager()
        truncated_messages = context_mgr.prepare_context(
            messages,
            provider="xai",
            model=self.model
        )
        
        # Log if truncation occurred
        if len(truncated_messages) < len(messages):
            logger.info(
                f"Truncated from {len(messages)} to {len(truncated_messages)} messages "
                f"for {self.model}"
            )
        
        # Convert to OpenAI format (xAI is OpenAI-compatible)
        openai_messages = [{"role": m.role, "content": m.content} for m in truncated_messages]

        try:
            # Build parameters
            params = {
                "model": self.model,
                "messages": openai_messages,
                "max_tokens": 1000,
                "stream": True,
            }
            
            # Add temperature if specified (xAI/OpenAI allows 0-2)
            if temperature is not None:
                params["temperature"] = temperature
                
            stream = await self.client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"xAI API error: {str(e)}")
