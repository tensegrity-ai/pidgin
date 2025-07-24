"""Test streaming error handling and recovery."""

import asyncio
import pytest

from pidgin.providers.retry_utils import is_retryable_error, retry_with_exponential_backoff


class TestStreamingErrors:
    """Test streaming error classification and retry logic."""

    def test_incomplete_read_is_retryable(self):
        """Test that incomplete read errors are classified as retryable."""
        errors = [
            Exception("IncompleteRead: 0 bytes read"),
            Exception("incomplete chunked read"),
            Exception("ChunkedEncodingError: Connection broken"),
            Exception("Connection reset by peer"),
            Exception("Broken pipe"),
            Exception("SSL error occurred"),
            Exception("EOF occurred in violation of protocol"),
        ]
        
        for error in errors:
            assert is_retryable_error(error), f"Expected {error} to be retryable"

    def test_context_errors_not_retryable(self):
        """Test that context limit errors are NOT retryable."""
        errors = [
            Exception("context_length_exceeded"),
            Exception("Maximum context length reached"),
            Exception("Too many tokens in context window"),
            Exception("messages: array too long"),
        ]
        
        for error in errors:
            assert not is_retryable_error(error), f"Expected {error} to NOT be retryable"

    @pytest.mark.asyncio
    async def test_retry_with_streaming_error(self):
        """Test that streaming errors trigger retries."""
        attempt_count = 0
        
        async def failing_stream():
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:
                raise Exception("IncompleteRead: Connection lost")
            
            # Succeed on third attempt
            yield "Success!"
            yield " After retry!"
        
        chunks = []
        async for chunk in retry_with_exponential_backoff(
            failing_stream,
            max_retries=3,
            base_delay=0.1,  # Short delay for testing
        ):
            chunks.append(chunk)
        
        # Should have retried twice before succeeding
        assert attempt_count == 3
        # Should have success message
        assert any("Success!" in chunk for chunk in chunks)
        # Should have retry messages
        assert any("retrying" in chunk for chunk in chunks)

    @pytest.mark.asyncio
    async def test_fallback_on_streaming_failure(self):
        """Test fallback to non-streaming on repeated failures."""
        
        async def always_failing_stream():
            raise Exception("IncompleteRead: Persistent failure")
            yield  # Make it a generator (unreachable)
        
        async def fallback_non_stream():
            yield "Fallback successful!"
        
        chunks = []
        async for chunk in retry_with_exponential_backoff(
            always_failing_stream,
            max_retries=2,
            base_delay=0.1,
            fallback_func=fallback_non_stream,
        ):
            chunks.append(chunk)
        
        # Should have fallback message
        assert any("falling back to non-streaming" in chunk for chunk in chunks)
        assert any("Fallback successful!" in chunk for chunk in chunks)

    @pytest.mark.asyncio
    async def test_timeout_is_retryable(self):
        """Test that timeout errors are retryable."""
        attempt_count = 0
        
        async def timeout_stream():
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 2:
                raise asyncio.TimeoutError("Request timed out")
            
            yield "Success after timeout!"
        
        chunks = []
        async for chunk in retry_with_exponential_backoff(
            timeout_stream,
            max_retries=3,
            base_delay=0.1,
        ):
            chunks.append(chunk)
        
        assert attempt_count == 2
        assert any("Success after timeout!" in chunk for chunk in chunks)