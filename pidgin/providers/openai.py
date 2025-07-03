import os
import logging
import time
import asyncio
from openai import AsyncOpenAI
from typing import List, AsyncIterator, AsyncGenerator, Optional, Dict
from ..core.types import Message
from .base import Provider
from .retry_utils import retry_with_exponential_backoff, is_retryable_error

logger = logging.getLogger(__name__)


class OpenAIProvider(Provider):
    """OpenAI API provider with friendly error handling."""
    
    FRIENDLY_ERRORS: Dict[str, str] = {
        "insufficient_quota": "OpenAI API quota exceeded. Please check your billing at platform.openai.com",
        "invalid_api_key": "Invalid OpenAI API key. Please check your OPENAI_API_KEY environment variable",
        "model_not_found": "Model not found. Please verify the model name is correct",
        "rate_limit": "Rate limit reached. The system will automatically retry...",
        "billing": "OpenAI API billing issue. Please update payment method at platform.openai.com",
        "authentication": "Authentication failed. Please verify your OpenAI API key",
    }
    
    SUPPRESS_TRACEBACK_ERRORS = [
        "insufficient_quota",
        "invalid_api_key", 
        "billing",
        "payment",
        "quota",
        "authentication"
    ]
    def __init__(self, model: str):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set. "
                "Please set it to your OpenAI API key."
            )
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    def _get_friendly_error(self, error: Exception) -> str:
        """Convert technical API errors to user-friendly messages."""
        error_str = str(error).lower()
        
        # Check error message content
        for key, friendly_msg in self.FRIENDLY_ERRORS.items():
            if key.replace('_', ' ') in error_str:
                return friendly_msg
                
        # Fallback to original error
        return str(error)
    
    def _should_suppress_traceback(self, error: Exception) -> bool:
        """Check if we should suppress the full traceback for this error."""
        error_str = str(error).lower()
        
        return any(
            phrase in error_str
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
            provider="openai",
            model=self.model
        )
        
        # Log if truncation occurred
        if len(truncated_messages) < len(messages):
            logger.info(
                f"Truncated from {len(messages)} to {len(truncated_messages)} messages "
                f"for {self.model}"
            )
        
        # Convert to OpenAI format
        openai_messages = [{"role": m.role, "content": m.content} for m in truncated_messages]

        # Initialize usage tracking
        self._last_usage = None
        
        # Retry logic for overloaded/rate limit errors
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Build parameters
                params = {
                    "model": self.model,
                    "messages": openai_messages,
                    "max_tokens": 1000,
                    "stream": True,
                    "stream_options": {"include_usage": True}  # Request usage data
                }
                
                # Add temperature if specified (OpenAI allows 0-2)
                if temperature is not None:
                    params["temperature"] = temperature
                
                stream = await self.client.chat.completions.create(**params)

                async for chunk in stream:
                    # Handle content chunks
                    if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                    
                    # Check for usage data in the final chunk
                    if hasattr(chunk, 'usage') and chunk.usage:
                        self._last_usage = {
                            'prompt_tokens': getattr(chunk.usage, 'prompt_tokens', 0),
                            'completion_tokens': getattr(chunk.usage, 'completion_tokens', 0),
                            'total_tokens': getattr(chunk.usage, 'total_tokens', 0)
                        }
                        logger.debug(f"OpenAI usage data captured: {self._last_usage}")
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
                        # Log rate limit without traceback
                        logger.info(f"OpenAI rate limit hit, retrying in {delay:.1f}s")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Max retries exhausted
                        friendly_error = self._get_friendly_error(e)
                        if self._should_suppress_traceback(e):
                            logger.info(f"Expected API error: {friendly_error}")
                        else:
                            logger.error(f"API error after retries: {str(e)}", exc_info=True)
                        raise Exception(friendly_error) from None
                else:
                    # Non-retryable error
                    friendly_error = self._get_friendly_error(e)
                    if self._should_suppress_traceback(e):
                        logger.info(f"Expected API error: {friendly_error}")
                    else:
                        logger.error(f"Unexpected API error: {str(e)}", exc_info=True)
                    raise Exception(friendly_error) from None
    
    def get_last_usage(self) -> Optional[Dict[str, int]]:
        """Get token usage from the last API call."""
        return self._last_usage
