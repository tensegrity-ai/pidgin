# tests/fixtures/providers.py
"""Mock providers for testing."""

import pytest
from typing import List, AsyncGenerator, Optional
from unittest.mock import AsyncMock, Mock
from pidgin.providers.base import Provider
from pidgin.core.types import Message


class MockProvider(Provider):
    """Mock provider for testing."""
    
    def __init__(self, responses: List[str] = None):
        """Initialize with predefined responses."""
        self.responses = responses or ["Default response"]
        self.call_count = 0
        self.last_messages = None
        self.last_temperature = None
        
    async def stream_response(
        self, 
        messages: List[Message], 
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Stream predefined responses."""
        self.call_count += 1
        self.last_messages = messages
        self.last_temperature = temperature
        
        # Get response for this call
        response_idx = min(self.call_count - 1, len(self.responses) - 1)
        response = self.responses[response_idx]
        
        # Simulate streaming by yielding chunks
        words = response.split()
        for i, word in enumerate(words):
            if i > 0:
                yield " "
            yield word
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass


class ErrorProvider(Provider):
    """Provider that always errors."""
    
    def __init__(self, error_type=Exception, error_message="Test error"):
        self.error_type = error_type
        self.error_message = error_message
        
    async def stream_response(
        self, 
        messages: List[Message], 
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Always raise an error."""
        raise self.error_type(self.error_message)
        yield  # Never reached


class DelayedProvider(Provider):
    """Provider with configurable delays."""
    
    def __init__(self, response: str = "Delayed response", delay: float = 0.1):
        self.response = response
        self.delay = delay
        
    async def stream_response(
        self, 
        messages: List[Message], 
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response with delays."""
        import asyncio
        
        words = self.response.split()
        for i, word in enumerate(words):
            await asyncio.sleep(self.delay)
            if i > 0:
                yield " "
            yield word


@pytest.fixture
def mock_provider():
    """Create a basic mock provider."""
    return MockProvider()


@pytest.fixture
def mock_provider_with_responses():
    """Create a mock provider with custom responses."""
    def _create_provider(responses: List[str]):
        return MockProvider(responses)
    return _create_provider


@pytest.fixture
def error_provider():
    """Create an error-throwing provider."""
    return ErrorProvider()


@pytest.fixture
def delayed_provider():
    """Create a provider with delays."""
    return DelayedProvider()


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    client = Mock()
    client.messages = Mock()
    client.messages.create = AsyncMock()
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock()
    return client