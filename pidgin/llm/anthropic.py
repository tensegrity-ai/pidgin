"""Anthropic (Claude) LLM implementation."""
import os
from typing import List, Union, AsyncIterator, Optional
import anthropic
from anthropic import AsyncAnthropic

from pidgin.llm.base import LLM, LLMConfig, Message, LLMResponse


class AnthropicLLM(LLM):
    """Anthropic Claude implementation."""
    
    MODELS = {
        "claude-3-opus-20240229": {"name": "Claude 3 Opus", "max_tokens": 4096},
        "claude-3-sonnet-20240229": {"name": "Claude 3 Sonnet", "max_tokens": 4096},
        "claude-3-haiku-20240307": {"name": "Claude 3 Haiku", "max_tokens": 4096},
        "claude-2.1": {"name": "Claude 2.1", "max_tokens": 4096},
        "claude-2.0": {"name": "Claude 2.0", "max_tokens": 4096},
    }
    
    def __init__(self, config: LLMConfig, api_key: Optional[str] = None):
        super().__init__(config, api_key)
        
        # Get API key
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")
        
        # Initialize client
        self.client = AsyncAnthropic(api_key=self.api_key)
        
        # Validate model
        if config.model not in self.MODELS:
            raise ValueError(f"Unknown Anthropic model: {config.model}")
    
    @property
    def provider(self) -> str:
        return "anthropic"
    
    async def generate(
        self,
        messages: List[Message],
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncIterator[str]]:
        """Generate response from Claude."""
        # Prepare messages
        prepared_messages = self.prepare_messages(messages)
        
        # Convert to Anthropic format
        anthropic_messages = []
        system_prompt = None
        
        for msg in prepared_messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Prepare parameters
        params = {
            "model": self.config.model,
            "messages": anthropic_messages,
            "max_tokens": self.config.max_tokens or self.MODELS[self.config.model]["max_tokens"],
            "temperature": self.config.temperature or 0.7,
        }
        
        if system_prompt:
            params["system"] = system_prompt
        
        if self.config.top_p is not None:
            params["top_p"] = self.config.top_p
        
        # Merge additional kwargs
        params.update(kwargs)
        
        if stream:
            return self._stream_response(params)
        else:
            return await self._generate_response(params)
    
    async def _generate_response(self, params: dict) -> LLMResponse:
        """Generate a complete response."""
        response = await self.client.messages.create(**params)
        
        # Extract content
        content = ""
        if response.content:
            content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
        
        # Build usage info
        usage = {
            "prompt_tokens": response.usage.input_tokens if hasattr(response.usage, 'input_tokens') else 0,
            "completion_tokens": response.usage.output_tokens if hasattr(response.usage, 'output_tokens') else 0,
            "total_tokens": 0
        }
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
        
        return LLMResponse(
            content=content,
            model=self.config.model,
            usage=usage,
            metadata={
                "stop_reason": response.stop_reason if hasattr(response, 'stop_reason') else None,
                "id": response.id if hasattr(response, 'id') else None
            }
        )
    
    async def _stream_response(self, params: dict) -> AsyncIterator[str]:
        """Stream response tokens."""
        async with self.client.messages.stream(**params) as stream:
            async for chunk in stream:
                if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text'):
                    yield chunk.delta.text
                elif hasattr(chunk, 'text'):
                    yield chunk.text
    
    async def validate_connection(self) -> bool:
        """Validate Anthropic API connection."""
        try:
            # Try a minimal API call
            response = await self.client.messages.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10
            )
            return bool(response.content)
        except Exception:
            return False
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count for Anthropic models."""
        # Anthropic uses a similar tokenization to GPT models
        # Rough estimate: ~4 characters per token
        return super().count_tokens(text)