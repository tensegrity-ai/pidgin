import os
from anthropic import Anthropic
from typing import List, AsyncIterator, AsyncGenerator, Optional
from ..core.types import Message
from .base import Provider
from .retry_utils import retry_with_exponential_backoff, is_overloaded_error


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

    async def stream_response(
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
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
            "max_tokens": 1000,
        }
        
        # Add temperature if specified (Anthropic caps at 1.0)
        if temperature is not None:
            api_params["temperature"] = min(temperature, 1.0)

        # Add system parameter if we have system messages
        if system_messages:
            api_params["system"] = "\n\n".join(system_messages)

        # Validate we have at least one conversation message
        if not conversation_messages:
            raise ValueError(
                "Anthropic API requires at least one user or assistant message. "
                "Only system messages were provided."
            )

        # Define inner function for retry wrapper
        async def _make_api_call():
            with self.client.messages.stream(**api_params) as stream:
                for text in stream.text_stream:
                    yield text
        
        # Use retry wrapper with exponential backoff
        try:
            async for chunk in retry_with_exponential_backoff(
                _make_api_call,
                max_retries=3,
                base_delay=1.0,
                retry_on=(Exception,)  # Retry on all exceptions for now
            ):
                yield chunk
        except Exception as e:
            # Re-raise with Anthropic-specific error message
            raise Exception(f"Anthropic API error: {str(e)}")
