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
        # Extract system messages and conversation messages
        system_messages = []
        conversation_messages = []
        
        for m in messages:
            if m.role == "system":
                system_messages.append(m.content)
            else:
                conversation_messages.append({"role": m.role, "content": m.content})
        
        # Build API call parameters
        api_params = {
            "model": self.model,
            "messages": conversation_messages,
            "max_tokens": 1000
        }
        
        # Add system parameter if we have system messages
        if system_messages:
            api_params["system"] = "\n\n".join(system_messages)
        
        # Validate we have at least one conversation message
        if not conversation_messages:
            raise ValueError(
                "Anthropic API requires at least one user or assistant message. "
                "Only system messages were provided."
            )
        
        try:
            # Make the API call
            with self.client.messages.stream(**api_params) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            # Better error for debugging
            raise Exception(f"Anthropic API error: {str(e)}")