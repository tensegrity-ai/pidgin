"""Common retry utilities for API providers."""

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Callable, Optional, TypeVar, Union

from .base import ResponseChunk

T = TypeVar("T")


async def retry_with_exponential_backoff(
    func: Callable[..., AsyncGenerator[ResponseChunk, None]],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retry_on: Optional[tuple[type[Exception], ...]] = None,
    fallback_func: Optional[Callable[..., AsyncGenerator[ResponseChunk, None]]] = None,
    **kwargs,
) -> AsyncGenerator[Union[ResponseChunk, str], None]:
    """
    Retry an async generator function with exponential backoff.

    Args:
        func: The async generator function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter to delays
        retry_on: Tuple of exception types to retry on (default: all exceptions)
        fallback_func: Optional fallback function to try after all retries fail
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Yields:
        Values from the wrapped function

    Raises:
        The last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            # Try to execute the function
            async for value in func(*args, **kwargs):
                yield value
            return  # Success!

        except Exception as e:
            last_exception = e

            # Check if we should retry this exception
            if retry_on and not isinstance(e, retry_on):
                raise

            # Check if this is the last attempt
            if attempt >= max_retries - 1:
                # Don't raise yet if we have a fallback
                if not fallback_func:
                    raise
                break  # Exit loop to try fallback

            # Calculate delay with exponential backoff
            delay = min(base_delay * (2**attempt), max_delay)

            # Add jitter if requested
            if jitter:
                delay = delay * (0.5 + 0.5 * time.time() % 1)

            # Notify about retry with user-friendly message
            error_msg = str(e)
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                friendly_msg = "Rate limit reached - waiting before retry"
            elif "timeout" in error_msg.lower():
                friendly_msg = "Request timed out - retrying"
            elif "overloaded" in error_msg.lower() or "503" in error_msg:
                friendly_msg = "API temporarily overloaded - waiting"
            else:
                friendly_msg = "Temporary error - retrying"

            yield f"\n[{friendly_msg} ({delay:.1f}s)...]\n"

            # Wait before retrying
            await asyncio.sleep(delay)

    # If we have a fallback function and all retries failed, try it
    if fallback_func and last_exception:
        try:
            yield "\n[Streaming failed, falling back to non-streaming mode...]\n"
            async for value in fallback_func(*args, **kwargs):
                yield value
            return  # Fallback succeeded!
        except Exception as fallback_error:
            # Log fallback failure but raise original error
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Fallback also failed: {fallback_error}")
            raise last_exception

    # This should never be reached, but just in case
    if last_exception:
        raise last_exception


def is_overloaded_error(error: Exception) -> bool:
    """Check if an error indicates the API is overloaded."""
    error_str = str(error).lower()
    return any(
        indicator in error_str
        for indicator in [
            "overloaded",
            "rate limit",
            "too many requests",
            "capacity",
            "429",
            "503",
            "throttl",
        ]
    )


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable."""
    error_str = str(error).lower()

    # Context limit errors are NOT retryable
    context_patterns = [
        "context_length",
        "context length",
        "context window",
        "max_tokens",
        "maximum context",
        "token limit",
        "too many tokens",
        "context_length_exceeded",
        "messages: array too long",
        "exceeds the maximum",
        "content too long",
    ]

    if any(pattern in error_str for pattern in context_patterns):
        return False

    # Always retry overloaded errors
    if is_overloaded_error(error):
        return True

    # Other retryable patterns
    retryable_patterns = [
        "timeout",
        "readtimeout",
        "read timeout",
        "connection",
        "network",
        "temporary",
        "unavailable",
        "gateway",
        "500",
        "502",
        "504",
        # Add streaming-related errors
        "incomplete read",
        "incompleteread",
        "chunked read",
        "chunkedencoding",
        "stream",
        "broken pipe",
        "connection reset",
        "connection aborted",
        "ssl error",
        "eof occurred",
    ]

    return any(pattern in error_str for pattern in retryable_patterns)
