import os
import asyncio
import time
from openai import AsyncOpenAI
from typing import List, AsyncIterator, AsyncGenerator
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

    async def stream_response(
        self, messages: List[Message]
    ) -> AsyncGenerator[str, None]:
        # Convert to OpenAI format
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        # Truncate conversation if it's too long
        # Keep the system message (if any) and recent messages
        if len(openai_messages) > 20:
            system_msgs = [m for m in openai_messages if m["role"] == "system"]
            other_msgs = [m for m in openai_messages if m["role"] != "system"]
            # Keep system messages and last 19 messages
            openai_messages = system_msgs + other_msgs[-19:]

        # Retry logic for overloaded/rate limit errors
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=openai_messages,
                    max_tokens=1000,
                    stream=True,
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return  # Success!

            except Exception as e:
                error_str = str(e)

                # Check if it's a rate limit or overloaded error
                if any(
                    err in error_str.lower()
                    for err in ["rate_limit", "rate limit", "overloaded", "429"]
                ):
                    if attempt < max_retries - 1:
                        # Calculate exponential backoff with jitter
                        delay = base_delay * (2**attempt) + (0.1 * time.time() % 1)
                        # Use yield to send retry message
                        yield f"\n[Retrying in {delay:.1f}s due to rate limit...]\n"
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Max retries exhausted
                        raise Exception(
                            f"OpenAI API rate limited after {max_retries} retries: {error_str}"
                        )
                else:
                    # Non-retryable error
                    raise Exception(f"OpenAI API error: {error_str}")
