import os
import logging
from anthropic import AsyncAnthropic
from typing import List, AsyncIterator, AsyncGenerator, Optional, Dict
from ..core.types import Message
from .base import Provider
from .retry_utils import retry_with_exponential_backoff, is_overloaded_error
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

# Import model config classes from central location
from ..config.models import ModelConfig, ModelCharacteristics

# Anthropic model definitions
ANTHROPIC_MODELS = {
    "claude-4-opus-20250514": ModelConfig(
        model_id="claude-4-opus-20250514",
        shortname="Opus",
        aliases=["opus", "opus4", "claude-opus"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="long",
            recommended_pairings=["gpt-4.1", "o3"],
            conversation_style="analytical",
        ),
    ),
    "claude-4-sonnet-20250514": ModelConfig(
        model_id="claude-4-sonnet-20250514",
        shortname="Sonnet",
        aliases=["sonnet", "sonnet4", "claude-sonnet", "claude"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=6,
            avg_response_length="medium",
            recommended_pairings=["gpt-4.1-mini", "claude-4-sonnet-20250514"],
            conversation_style="verbose",
        ),
    ),
    "claude-3-5-sonnet-20241022": ModelConfig(
        model_id="claude-3-5-sonnet-20241022",
        shortname="Sonnet3.5",
        aliases=["sonnet3.5", "claude-3.5", "sonnet3.7", "claude-3.7"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="medium",
            recommended_pairings=["o4-mini", "gpt-4.1-mini"],
            conversation_style="analytical",
        ),
        notes="Latest Sonnet model",
    ),
    "claude-3-5-haiku-20241022": ModelConfig(
        model_id="claude-3-5-haiku-20241022",
        shortname="Haiku",
        aliases=["haiku", "haiku3.5", "claude-haiku"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=3,
            avg_response_length="short",
            recommended_pairings=["gpt-4.1-nano", "claude-3-5-haiku-20241022"],
            conversation_style="concise",
        ),
    ),
    "claude-3-haiku-20240307": ModelConfig(
        model_id="claude-3-haiku-20240307",
        shortname="Haiku3",
        aliases=["haiku3", "claude-3-haiku"],
        provider="anthropic",
        context_window=200000,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=3,
            avg_response_length="short",
            recommended_pairings=["gpt-4o-mini", "claude-3-haiku-20240307"],
            conversation_style="concise",
        ),
        notes="Legacy Haiku model",
    ),
}


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
        # Apply context management
        from .context_manager import ProviderContextManager
        context_mgr = ProviderContextManager()
        truncated_messages = context_mgr.prepare_context(
            messages,
            provider="anthropic",
            model=self.model
        )
        
        # Log if truncation occurred
        if len(truncated_messages) < len(messages):
            logger.info(
                f"Truncated from {len(messages)} to {len(truncated_messages)} messages "
                f"for {self.model}"
            )
        
        # Extract system messages and conversation messages
        system_messages = []
        conversation_messages = []

        for m in truncated_messages:
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
                # Capture usage data after stream completes
                final_message = await stream.get_final_message()
                if hasattr(final_message, 'usage'):
                    self._last_usage = {
                        'input_tokens': getattr(final_message.usage, 'input_tokens', 0),
                        'output_tokens': getattr(final_message.usage, 'output_tokens', 0),
                        'total_tokens': 0  # Will be calculated
                    }
                    self._last_usage['total_tokens'] = (
                        self._last_usage['input_tokens'] + 
                        self._last_usage['output_tokens']
                    )
        
        # Initialize usage tracking
        self._last_usage = None
        
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
    
    def get_last_usage(self) -> Optional[Dict[str, int]]:
        """Get token usage from the last API call."""
        return self._last_usage
