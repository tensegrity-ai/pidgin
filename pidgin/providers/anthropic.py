import os
from anthropic import Anthropic
from typing import List
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
    
    async def get_response(self, messages: List[Message]) -> str:
        # Convert to Anthropic format
        anthropic_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        
        try:
            response = self.client.messages.create(
                model=self.model,
                messages=anthropic_messages,
                max_tokens=1000
            )
            # Handle both text and tool use responses
            if response.content:
                if hasattr(response.content[0], 'text'):
                    return response.content[0].text
                else:
                    # If it's not a text response, return a string representation
                    return str(response.content[0])
            else:
                return ""
        except Exception as e:
            # Basic error handling - just don't crash
            raise Exception(f"Anthropic API error: {str(e)}")