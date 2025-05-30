"""OpenAI (GPT) LLM implementation."""
import os
from typing import List, Union, AsyncIterator, Optional
from openai import AsyncOpenAI

from pidgin.llm.base import LLM, LLMConfig, Message, LLMResponse


class OpenAILLM(LLM):
    """OpenAI GPT implementation."""
    
    MODELS = {
        "gpt-4-turbo-preview": {"name": "GPT-4 Turbo", "max_tokens": 4096},
        "gpt-4": {"name": "GPT-4", "max_tokens": 8192},
        "gpt-4-32k": {"name": "GPT-4 32K", "max_tokens": 32768},
        "gpt-3.5-turbo": {"name": "GPT-3.5 Turbo", "max_tokens": 4096},
        "gpt-3.5-turbo-16k": {"name": "GPT-3.5 Turbo 16K", "max_tokens": 16384},
    }
    
    def __init__(self, config: LLMConfig, api_key: Optional[str] = None):
        super().__init__(config, api_key)
        
        # Get API key
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        # Initialize client
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        # Validate model
        if config.model not in self.MODELS:
            raise ValueError(f"Unknown OpenAI model: {config.model}")
    
    @property
    def provider(self) -> str:
        return "openai"
    
    async def generate(
        self,
        messages: List[Message],
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncIterator[str]]:
        """Generate response from GPT."""
        # Prepare messages
        prepared_messages = self.prepare_messages(messages)
        
        # Convert to OpenAI format
        openai_messages = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in prepared_messages
        ]
        
        # Prepare parameters
        params = {
            "model": self.config.model,
            "messages": openai_messages,
            "temperature": self.config.temperature or 0.7,
            "max_tokens": self.config.max_tokens or self.MODELS[self.config.model]["max_tokens"],
        }
        
        if self.config.top_p is not None:
            params["top_p"] = self.config.top_p
        if self.config.frequency_penalty is not None:
            params["frequency_penalty"] = self.config.frequency_penalty
        if self.config.presence_penalty is not None:
            params["presence_penalty"] = self.config.presence_penalty
        
        # Merge additional kwargs
        params.update(kwargs)
        
        if stream:
            return self._stream_response(params)
        else:
            return await self._generate_response(params)
    
    async def _generate_response(self, params: dict) -> LLMResponse:
        """Generate a complete response."""
        response = await self.client.chat.completions.create(**params)
        
        # Extract content
        content = response.choices[0].message.content if response.choices else ""
        
        # Build usage info
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }
        
        return LLMResponse(
            content=content,
            model=self.config.model,
            usage=usage,
            metadata={
                "finish_reason": response.choices[0].finish_reason if response.choices else None,
                "id": response.id,
                "created": response.created,
            }
        )
    
    async def _stream_response(self, params: dict) -> AsyncIterator[str]:
        """Stream response tokens."""
        params["stream"] = True
        stream = await self.client.chat.completions.create(**params)
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def validate_connection(self) -> bool:
        """Validate OpenAI API connection."""
        try:
            # Try a minimal API call
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use cheapest model for validation
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10
            )
            return bool(response.choices)
        except Exception:
            return False
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count for OpenAI models."""
        # OpenAI uses tiktoken, but for simplicity we'll estimate
        # More accurate counting would require tiktoken library
        return super().count_tokens(text)