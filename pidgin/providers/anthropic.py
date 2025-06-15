import os
import asyncio
import time
from anthropic import Anthropic
from typing import List, AsyncIterator, AsyncGenerator
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

    async def stream_response(
        self, messages: List[Message]
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

        # Add system parameter if we have system messages
        if system_messages:
            api_params["system"] = "\n\n".join(system_messages)

        # Validate we have at least one conversation message
        if not conversation_messages:
            raise ValueError(
                "Anthropic API requires at least one user or assistant message. "
                "Only system messages were provided."
            )

        # Retry logic for overloaded errors
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Make the API call
                with self.client.messages.stream(**api_params) as stream:
                    for text in stream.text_stream:
                        yield text
                return  # Success!

            except Exception as e:
                error_str = str(e)

                # Check if it's an overloaded error
                if "overloaded_error" in error_str or "Overloaded" in error_str:
                    if attempt < max_retries - 1:
                        # Calculate exponential backoff with jitter
                        delay = base_delay * (2**attempt) + (0.1 * time.time() % 1)
                        # Use yield to send retry message
                        yield f"\n[Retrying in {delay:.1f}s due to overload...]\n"
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Max retries exhausted
                        raise Exception(
                            f"Anthropic API overloaded after {max_retries} retries: {error_str}"
                        )
                else:
                    # Non-retryable error
                    raise Exception(f"Anthropic API error: {error_str}")
