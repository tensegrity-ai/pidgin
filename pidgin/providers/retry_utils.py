"""Common retry utilities for API providers."""

import asyncio
import time
from typing import AsyncGenerator, Callable, Optional, TypeVar, Any
from functools import wraps

T = TypeVar('T')


async def retry_with_exponential_backoff(
    func: Callable[..., AsyncGenerator[str, None]],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retry_on: Optional[tuple[type[Exception], ...]] = None,
    **kwargs
) -> AsyncGenerator[str, None]:
    """
    Retry an async generator function with exponential backoff.
    
    Args:
        func: The async generator function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter to delays
        retry_on: Tuple of exception types to retry on (default: all exceptions)
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
                raise
                
            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)
            
            # Add jitter if requested
            if jitter:
                delay = delay * (0.5 + 0.5 * time.time() % 1)
                
            # Notify about retry
            yield f"\n[Retrying in {delay:.1f}s due to error: {str(e)[:50]}...]\n"
            
            # Wait before retrying
            await asyncio.sleep(delay)
    
    # This should never be reached, but just in case
    if last_exception:
        raise last_exception


def is_overloaded_error(error: Exception) -> bool:
    """Check if an error indicates the API is overloaded."""
    error_str = str(error).lower()
    return any(indicator in error_str for indicator in [
        "overloaded",
        "rate limit",
        "too many requests",
        "capacity",
        "429",
        "503",
        "throttl"
    ])


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable."""
    error_str = str(error).lower()
    
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
        "504"
    ]
    
    return any(pattern in error_str for pattern in retryable_patterns)