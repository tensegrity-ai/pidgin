# tests/unit/test_retry_utils.py
"""Test retry utilities."""

import asyncio

import pytest

from pidgin.providers.retry_utils import (
    is_overloaded_error,
    is_retryable_error,
    retry_with_exponential_backoff,
)


class TestRetryWithExponentialBackoff:
    """Test retry_with_exponential_backoff function."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Test successful execution on first attempt."""

        async def successful_generator():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"

        result = []
        async for chunk in retry_with_exponential_backoff(successful_generator):
            result.append(chunk)

        assert result == ["chunk1", "chunk2", "chunk3"]

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry on failure with eventual success."""
        attempt_count = 0

        async def failing_then_success_generator():
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < 3:
                raise ConnectionError("Network error")

            yield "success"

        result = []
        async for chunk in retry_with_exponential_backoff(
            failing_then_success_generator,
            max_retries=3,
            base_delay=0.01,  # Short delay for testing
        ):
            # Filter out retry messages
            if not chunk.startswith("\n[Retrying"):
                result.append(chunk)

        assert "success" in result
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that exception is raised after max retries."""
        attempt_count = 0

        async def always_failing_generator():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Always fails")
            yield  # Never reached

        with pytest.raises(ValueError, match="Always fails"):
            result = []
            async for chunk in retry_with_exponential_backoff(
                always_failing_generator, max_retries=2, base_delay=0.01
            ):
                if not chunk.startswith("\n[Retrying"):
                    result.append(chunk)

        # Should have tried twice
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_specific_exceptions(self):
        """Test retry only on specific exception types."""
        attempt_count = 0

        async def specific_error_generator():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Specific error")
            yield  # Never reached

        # Should not retry ValueError when only retrying ConnectionError
        with pytest.raises(ValueError):
            async for _ in retry_with_exponential_backoff(
                specific_error_generator,
                retry_on=(ConnectionError,),
                max_retries=3,
                base_delay=0.01,
            ):
                pass

        # Should only try once (no retries)
        assert attempt_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, monkeypatch):
        """Test exponential backoff delay calculation."""
        sleep_delays = []

        async def mock_sleep(delay):
            sleep_delays.append(delay)

        monkeypatch.setattr(asyncio, "sleep", mock_sleep)

        attempt_count = 0

        async def failing_generator():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 4:
                raise ConnectionError("Test error")
            yield "done"

        async for _ in retry_with_exponential_backoff(
            failing_generator,
            max_retries=4,
            base_delay=1.0,
            max_delay=10.0,
            jitter=False,
        ):
            pass

        # Check delays: 1, 2, 4 seconds (exponential)
        assert len(sleep_delays) == 3
        assert sleep_delays[0] == 1.0
        assert sleep_delays[1] == 2.0
        assert sleep_delays[2] == 4.0

    @pytest.mark.asyncio
    async def test_max_delay_cap(self, monkeypatch):
        """Test that delays are capped at max_delay."""
        sleep_delays = []

        async def mock_sleep(delay):
            sleep_delays.append(delay)

        monkeypatch.setattr(asyncio, "sleep", mock_sleep)

        attempt_count = 0

        async def failing_generator():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 6:
                raise ConnectionError("Test error")
            yield "done"

        async for _ in retry_with_exponential_backoff(
            failing_generator,
            max_retries=6,
            base_delay=1.0,
            max_delay=5.0,
            jitter=False,
        ):
            pass

        # Check that delays don't exceed max_delay
        assert all(delay <= 5.0 for delay in sleep_delays)
        # Later delays should be capped at 5.0
        assert sleep_delays[-1] == 5.0


class TestIsOverloadedError:
    """Test is_overloaded_error function."""

    def test_overloaded_keywords(self):
        """Test detection of overloaded error keywords."""
        assert is_overloaded_error(Exception("Server is overloaded"))
        assert is_overloaded_error(Exception("Rate limit exceeded"))
        assert is_overloaded_error(Exception("Too many requests"))
        assert is_overloaded_error(Exception("At capacity"))
        assert is_overloaded_error(Exception("HTTP 429"))
        assert is_overloaded_error(Exception("503 Service Unavailable"))
        assert is_overloaded_error(Exception("Request was throttled"))

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        assert is_overloaded_error(Exception("SERVER OVERLOADED"))
        assert is_overloaded_error(Exception("Rate Limit Exceeded"))

    def test_non_overloaded_errors(self):
        """Test non-overloaded errors."""
        assert not is_overloaded_error(Exception("Authentication failed"))
        assert not is_overloaded_error(Exception("Invalid request"))
        assert not is_overloaded_error(Exception("404 Not Found"))


class TestIsRetryableError:
    """Test is_retryable_error function."""

    def test_overloaded_errors_are_retryable(self):
        """Test that all overloaded errors are retryable."""
        assert is_retryable_error(Exception("Server overloaded"))
        assert is_retryable_error(Exception("Rate limit"))

    def test_timeout_errors(self):
        """Test timeout error detection."""
        assert is_retryable_error(Exception("Request timeout"))
        assert is_retryable_error(Exception("Read timeout"))

    def test_connection_errors(self):
        """Test connection error detection."""
        assert is_retryable_error(Exception("Connection refused"))
        assert is_retryable_error(Exception("Network error"))

    def test_server_errors(self):
        """Test server error detection."""
        assert is_retryable_error(Exception("500 Internal Server Error"))
        assert is_retryable_error(Exception("502 Bad Gateway"))
        assert is_retryable_error(Exception("504 Gateway Timeout"))
        assert is_retryable_error(Exception("Service temporarily unavailable"))

    def test_non_retryable_errors(self):
        """Test non-retryable errors."""
        assert not is_retryable_error(Exception("401 Unauthorized"))
        assert not is_retryable_error(Exception("400 Bad Request"))
        assert not is_retryable_error(Exception("404 Not Found"))
        assert not is_retryable_error(Exception("Invalid API key"))
