import os
import logging
from typing import List, AsyncIterator, AsyncGenerator, Optional, Dict
from ..core.types import Message
from .base import Provider

logger = logging.getLogger(__name__)

# Import model config classes from central location
from ..config.models import ModelConfig, ModelCharacteristics

# xAI model definitions
XAI_MODELS = {
    "grok-beta": ModelConfig(
        model_id="grok-beta",
        shortname="Grok",
        aliases=["grok", "xai"],
        provider="xai",
        context_window=131072,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="medium",
            recommended_pairings=["gpt-4o", "claude-4-sonnet-20250514"],
            conversation_style="analytical",
        ),
        notes="xAI's flagship model",
    ),
    "grok-2-1212": ModelConfig(
        model_id="grok-2-1212",
        shortname="Grok-2",
        aliases=["grok-2", "grok2"],
        provider="xai",
        context_window=131072,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="medium",
            recommended_pairings=["gpt-4.1", "claude-4-sonnet-20250514"],
            conversation_style="analytical",
        ),
        notes="Latest Grok model",
    ),
    "grok-2-vision-1212": ModelConfig(
        model_id="grok-2-vision-1212",
        shortname="Grok-Vision",
        aliases=["grok-vision", "grok-2-vision"],
        provider="xai",
        context_window=131072,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="medium",
            recommended_pairings=["gpt-4o", "gemini-1.5-pro"],
            conversation_style="analytical",
        ),
        notes="Multimodal Grok model",
    ),
}

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
        self._last_usage = None

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
                "stream_options": {"include_usage": True}  # Request usage data like OpenAI
            }
            
            # Add temperature if specified (xAI/OpenAI allows 0-2)
            if temperature is not None:
                params["temperature"] = temperature
                
            stream = await self.client.chat.completions.create(**params)

            async for chunk in stream:
                # Handle content chunks
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                
                # Check for usage data in the final chunk
                if hasattr(chunk, 'usage') and chunk.usage:
                    self._last_usage = {
                        'prompt_tokens': getattr(chunk.usage, 'prompt_tokens', 0),
                        'completion_tokens': getattr(chunk.usage, 'completion_tokens', 0),
                        'total_tokens': getattr(chunk.usage, 'total_tokens', 0)
                    }
                    logger.debug(f"xAI usage data captured: {self._last_usage}")
        except Exception as e:
            raise Exception(f"xAI API error: {str(e)}")
    
    def get_last_usage(self) -> Optional[Dict[str, int]]:
        """Get token usage from the last API call."""
        return self._last_usage
