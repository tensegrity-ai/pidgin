import os
import logging
from anthropic import AsyncAnthropic
from typing import List, AsyncIterator, AsyncGenerator, Optional, Dict
from ..core.types import Message
from .base import Provider
from .retry_utils import retry_with_exponential_backoff, is_overloaded_error

logger = logging.getLogger(__name__)


class AnthropicProvider(Provider):
    """Anthropic API provider with friendly error handling."""
    
    FRIENDLY_ERRORS: Dict[str, str] = {
        "credit_balance_too_low": "Anthropic API credit balance is too low. Please add credits at console.anthropic.com → Billing",
        "invalid_api_key": "Invalid Anthropic API key. Please check your ANTHROPIC_API_KEY environment variable",
        "authentication_error": "Authentication failed. Please verify your Anthropic API key",
        "rate_limit": "Rate limit reached. The system will automatically retry...",
        "not_found_error": "Model not found. Please check the model name is correct",
        "overloaded_error": "Anthropic API is temporarily overloaded. Retrying...",
        "permission_error": "Your API key doesn't have permission to use this model",
    }
    
    SUPPRESS_TRACEBACK_ERRORS = [
        "credit_balance_too_low",
        "invalid_api_key",
        "authentication_error",
        "permission_error",
        "quota",
        "billing",
        "payment"
    ]
    def __init__(self, model: str):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable not set. "
                "Please set it to your Anthropic API key."
            )
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
    
    def _get_friendly_error(self, error: Exception) -> str:
        """Convert technical API errors to user-friendly messages."""
        error_str = str(error).lower()
        error_type = getattr(error, '__class__.__name__', '').lower()
        
        # Check error message content
        for key, friendly_msg in self.FRIENDLY_ERRORS.items():
            if key.replace('_', ' ') in error_str or key in error_type:
                return friendly_msg
                
        # Fallback to original error
        return str(error)
    
    def _should_suppress_traceback(self, error: Exception) -> bool:
        """Check if we should suppress the full traceback for this error."""
        error_str = str(error).lower()
        error_type = getattr(error, '__class__.__name__', '').lower()
        
        return any(
            phrase in error_str or phrase in error_type 
            for phrase in self.SUPPRESS_TRACEBACK_ERRORS
        )

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
            # Use async streaming
            async with self.client.messages.stream(**api_params) as stream:
                async for text in stream.text_stream:
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
            # Get friendly error message
            friendly_error = self._get_friendly_error(e)
            
            # Log appropriately based on error type
            if self._should_suppress_traceback(e):
                logger.info(f"Expected API error: {friendly_error}")
            else:
                logger.error(f"Unexpected API error: {str(e)}", exc_info=True)
            
            # Create a clean exception with friendly message
            raise Exception(friendly_error) from None
