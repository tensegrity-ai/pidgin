import os
from openai import AsyncOpenAI
from typing import List
from ..types import Message
from .base import Provider


class OpenAIProvider(Provider):
    def __init__(self, model: str):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set. "
                "Please set it to your OpenAI API key."
            )
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def get_response(self, messages: List[Message]) -> str:
        # Convert to OpenAI format
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
            raise Exception(f"OpenAI API error: {str(e)}")