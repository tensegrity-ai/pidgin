"""Base provider interface for AI model integrations."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Dict, List, Optional

from ..core.types import Message


class Provider(ABC):
    """Abstract base class for AI model providers.

    All provider implementations must inherit from this class and implement
    the required methods. Providers handle the communication with AI models
    and return streaming responses.

    Example:
        class MyProvider(Provider):
            async def stream_response(self, messages, temperature=None):
                # Implementation here
                async for chunk in self._call_api(messages):
                    yield chunk
    """

    def __init__(self):
        """Initialize provider with default settings."""
        self.allow_truncation = False  # Default: no truncation

    @abstractmethod
    async def stream_response(
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks from the model.

        This is the main method that provider implementations must define.
        It should yield response chunks as they arrive from the AI model.

        Args:
            messages: List of conversation messages in chronological order.
                     Each message has 'role' and 'content' attributes.
            temperature: Optional temperature setting (0.0-2.0).
                        Provider-specific limits may apply. Higher values
                        increase randomness in responses.

        Yields:
            str: Individual chunks of the response as they arrive.

        Raises:
            Exception: Provider-specific exceptions for API errors,
                      rate limits, or connection issues.

        Note:
            Implementations should handle retries and error recovery
            internally when appropriate.
        """
        yield  # type: ignore[misc]

    async def cleanup(self) -> None:
        """Clean up provider resources.

        Override this method to clean up any resources like:
        - HTTP client sessions
        - Open connections
        - Thread pools

        This method is called when the provider is no longer needed.
        The default implementation does nothing.
        """

    def get_last_usage(self) -> Optional[Dict[str, int]]:
        """Get token usage from the last API call.

        Returns:
            Optional dictionary with token counts:
            - prompt_tokens: Number of tokens in the prompt
            - completion_tokens: Number of tokens in the response
            - total_tokens: Sum of prompt and completion tokens

            Returns None if the provider doesn't support token counting
            or no calls have been made yet.

        Note:
            Not all providers support token counting. This is an optional
            method that providers can implement if their API provides
            usage information.
        """
        return None
