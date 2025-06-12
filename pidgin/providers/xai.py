import os
from typing import List
from ..types import Message
from .base import Provider

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
                "OpenAI client not available. Install with: "
                "pip install openai"
            )
        
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError(
                "XAI_API_KEY environment variable not set. "
                "Please set it to your xAI API key."
            )
        
        # xAI uses OpenAI-compatible API with custom base URL
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        self.model = model
    
    async def get_response(self, messages: List[Message]) -> str:
        # Convert to OpenAI format (xAI is OpenAI-compatible)
        openai_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        
        # Truncate conversation if it's too long
        # Keep the system message (if any) and recent messages
        if len(openai_messages) > 20:
            system_msgs = [m for m in openai_messages if m["role"] == "system"]
            other_msgs = [m for m in openai_messages if m["role"] != "system"]
            # Keep system messages and last 19 messages
            openai_messages = system_msgs + other_msgs[-19:]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                max_tokens=1000
            )
            
            # Extract text from response
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            else:
                return ""
        except Exception as e:
            raise Exception(f"xAI API error: {str(e)}")