import os
from anthropic import Anthropic
from typing import List, AsyncIterator
from ..types import Message
from .base import Provider


class AnthropicProvider(Provider):
    def __init__(self, model: str):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable not set. "
                "Please set it to your Anthropic API key."
            )
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    async def stream_response(self, messages: List[Message]) -> AsyncIterator[str]:
        # Convert to Anthropic format
        anthropic_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        
        try:
            # Anthropic's streaming uses a synchronous context manager
            with self.client.messages.stream(
                model=self.model,
                messages=anthropic_messages,
                max_tokens=1000
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            # Basic error handling - just don't crash
            raise Exception(f"Anthropic API error: {str(e)}")