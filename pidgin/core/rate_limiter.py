"""Streaming-aware rate limiter for API providers."""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict

from ..config.config import Config
from ..config.provider_capabilities import get_provider_capabilities
from ..io.logger import get_logger
from .constants import RateLimits, SystemDefaults

logger = get_logger("rate_limiter")


@dataclass
class RequestRecord:
    """Record of a request at a point in time."""

    timestamp: float
    tokens: int
    provider: str
    duration: float = 0.0  # How long the request took (streaming duration)


class StreamingRateLimiter:
    """Rate limiter that accounts for streaming duration.

    Key insight: Long streaming responses naturally provide pacing.
    We only need to add artificial delays when streaming doesn't
    provide enough spacing between requests.
    """

    def __init__(self, config: Config):
        """Initialize the rate limiter.

        Args:
            config: Application configuration
        """
        self.config = config
        self.rate_limits = self._load_limits()

        # Track request history per provider
        self.request_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=SystemDefaults.MAX_EVENT_HISTORY)
        )

        # Track last request time per provider for pacing
        self.last_request_time: Dict[str, float] = {}

        # Thread safety
        self.lock = Lock()

        # Track backoff state
        self.backoff_until: Dict[str, float] = {}

    def _load_limits(self) -> Dict[str, Dict[str, int]]:
        """Load rate limits from provider capabilities."""
        limits = {}

        # Load from provider capabilities
        for provider in ["anthropic", "openai", "google", "xai", "local"]:
            capabilities = get_provider_capabilities(provider)
            limits[provider] = {
                "requests_per_minute": capabilities.requests_per_minute,
                "tokens_per_minute": capabilities.tokens_per_minute,
            }

        # Override with config if provided
        custom_limits = self.config.get("rate_limiting.custom_limits", {})

        for provider, custom in custom_limits.items():
            if provider not in limits:
                limits[provider] = {}
            limits[provider].update(custom)

        return limits

    def _normalize_provider(self, provider: str) -> str:
        """Normalize provider name."""
        return provider.lower().replace("provider", "").strip()

    async def acquire(self, provider: str, estimated_tokens: int) -> float:
        """Wait if needed before making a request.

        Args:
            provider: Provider name (anthropic, openai, etc)
            estimated_tokens: Estimated tokens for the request

        Returns:
            How long we waited (for telemetry)
        """
        provider = self._normalize_provider(provider)

        # Check if rate limiting is enabled
        if not self.config.get("rate_limiting.enabled", True):
            return 0.0

        # Skip rate limiting for local models
        if provider == "local" or provider.startswith("local"):
            return 0.0

        start_time = time.time()

        # Check backoff state
        if provider in self.backoff_until:
            remaining_backoff = self.backoff_until[provider] - start_time
            if remaining_backoff > 0:
                logger.info(
                    f"In backoff for {provider}, waiting {remaining_backoff:.1f}s"
                )
                await asyncio.sleep(remaining_backoff)
                del self.backoff_until[provider]

        # Get provider limits
        # Get provider limits or use defaults from capabilities
        if provider not in self.rate_limits:
            capabilities = get_provider_capabilities(provider)
            limits = {
                "requests_per_minute": capabilities.requests_per_minute,
                "tokens_per_minute": capabilities.tokens_per_minute,
            }
        else:
            limits = self.rate_limits[provider]
        request_limit = limits["requests_per_minute"]
        token_limit = limits["tokens_per_minute"]

        # Calculate required intervals
        request_interval = 60.0 / request_limit  # seconds between requests
        token_interval = (
            estimated_tokens / token_limit
        ) * 60.0  # seconds this request "costs"

        # Get required wait time based on both limits
        wait_time = 0.0

        with self.lock:
            # Check request rate
            if provider in self.last_request_time:
                elapsed = start_time - self.last_request_time[provider]
                if elapsed < request_interval:
                    wait_time = max(wait_time, request_interval - elapsed)

            # Check token rate using sliding window
            current_tokens = self._get_current_token_rate(provider)
            if (
                current_tokens + estimated_tokens
                > token_limit * RateLimits.SAFETY_MARGIN
            ):
                # Calculate how long to wait for tokens to "expire"
                token_wait = self._calculate_token_wait(
                    provider, estimated_tokens, token_limit
                )
                wait_time = max(wait_time, token_wait)

        # Wait if necessary
        if wait_time > 0:
            # Use display utilities if available (for CLI), otherwise fall back to logger
            try:
                from rich.console import Console

                console = Console()

                # Create compact rate limit display similar to turn counter
                nord3 = "#4c566a"  # Muted gray color
                separator_width = min(console.width - 4, 60)

                # Build the rate limit info
                rate_info = f"⏱ Rate limit pacing for {provider}: {wait_time:.1f}s"
                timing_info = f"[{nord3}][dim]Request interval: {request_interval:.1f}s | Token cost: {token_interval:.1f}s[/dim][/{nord3}]"

                # Calculate padding for centering
                plain_rate_info = (
                    f"⏱ Rate limit pacing for {provider}: {wait_time:.1f}s"
                )
                padding = max(0, (separator_width - len(plain_rate_info)) // 2)
                centered_rate_info = " " * padding + rate_info

                plain_timing_info = f"Request interval: {request_interval:.1f}s | Token cost: {token_interval:.1f}s"
                timing_padding = max(0, (separator_width - len(plain_timing_info)) // 2)
                centered_timing_info = " " * timing_padding + timing_info

                # Print compact display
                console.print(f"\n[{nord3}]{'─' * separator_width}[/{nord3}]")
                console.print(f"[{nord3}]{centered_rate_info}[/{nord3}]")
                console.print(centered_timing_info)
                console.print(f"[{nord3}]{'─' * separator_width}[/{nord3}]\n")

            except ImportError:
                # Fallback for non-CLI contexts
                logger.info(
                    f"Rate limit pacing for {provider}: waiting {wait_time:.1f}s "
                    f"(request interval: {request_interval:.1f}s, token cost: {token_interval:.1f}s)"
                )
            await asyncio.sleep(wait_time)

        # Record this request
        with self.lock:
            self.last_request_time[provider] = time.time()
            self.request_history[provider].append(
                RequestRecord(
                    timestamp=time.time(), tokens=estimated_tokens, provider=provider
                )
            )

        return time.time() - start_time

    def record_request_complete(
        self, provider: str, actual_tokens: int, duration: float
    ):
        """Record that a request completed with actual token count and duration.

        Args:
            provider: Provider name
            actual_tokens: Actual tokens used (vs estimated)
            duration: How long the request took (streaming duration)
        """
        provider = self._normalize_provider(provider)

        with self.lock:
            # Update the most recent request with actual data
            if self.request_history.get(provider):
                last_request = self.request_history[provider][-1]
                last_request.tokens = actual_tokens
                last_request.duration = duration

        logger.debug(
            f"Request complete for {provider}: {actual_tokens} tokens, "
            f"{duration:.1f}s duration"
        )

    def record_error(self, provider: str, error_type: str):
        """Record an API error for backoff calculation.

        Args:
            provider: Provider name
            error_type: Type of error (rate_limit, overloaded, etc)
        """
        provider = self._normalize_provider(provider)

        if error_type in ["rate_limit", "429", "overloaded"]:
            # Set exponential backoff
            backoff = min(
                60.0,
                2.0
                * len(
                    [
                        r
                        for r in self.request_history.get(provider, [])
                        if r.timestamp > time.time() - 60
                    ]
                ),
            )
            self.backoff_until[provider] = time.time() + backoff

            logger.warning(
                f"Rate limit error for {provider}, backing off for {backoff:.1f}s"
            )

    def _get_current_token_rate(self, provider: str) -> int:
        """Get current token usage rate (tokens per minute).

        Args:
            provider: Provider name

        Returns:
            Current tokens per minute
        """
        cutoff = time.time() - 60  # 1 minute window

        recent_requests = [
            r for r in self.request_history.get(provider, []) if r.timestamp >= cutoff
        ]

        return sum(r.tokens for r in recent_requests)

    def _calculate_token_wait(
        self, provider: str, new_tokens: int, limit: int
    ) -> float:
        """Calculate wait time needed for token rate compliance.

        Args:
            provider: Provider name
            new_tokens: Tokens for new request
            limit: Token per minute limit

        Returns:
            Seconds to wait
        """
        # Get requests in sliding window ordered by time
        cutoff = time.time() - 60
        recent = sorted(
            [
                r
                for r in self.request_history.get(provider, [])
                if r.timestamp >= cutoff
            ],
            key=lambda r: r.timestamp,
        )

        if not recent:
            return 0.0

        # Calculate when we'll have token budget
        current_tokens = sum(r.tokens for r in recent)
        if current_tokens + new_tokens <= limit * RateLimits.SAFETY_MARGIN:
            return 0.0

        # Find how long until oldest requests expire
        tokens_to_free = (current_tokens + new_tokens) - (
            limit * RateLimits.SAFETY_MARGIN
        )
        freed_tokens = 0

        for req in recent:
            freed_tokens += req.tokens
            if freed_tokens >= tokens_to_free:
                # Wait until this request expires from window
                return max(0.0, req.timestamp + 60 - time.time())

        return 0.0

    def get_status(self, provider: str) -> Dict[str, Any]:
        """Get current status for a provider.

        Args:
            provider: Provider name

        Returns:
            Status dictionary
        """
        provider = self._normalize_provider(provider)
        # Get provider limits or use defaults from capabilities
        if provider not in self.rate_limits:
            capabilities = get_provider_capabilities(provider)
            limits = {
                "requests_per_minute": capabilities.requests_per_minute,
                "tokens_per_minute": capabilities.tokens_per_minute,
            }
        else:
            limits = self.rate_limits[provider]

        with self.lock:
            current_tokens = self._get_current_token_rate(provider)
            recent_requests = len(
                [
                    r
                    for r in self.request_history.get(provider, [])
                    if r.timestamp >= time.time() - 60
                ]
            )

        return {
            "provider": provider,
            "current_tokens_per_minute": current_tokens,
            "token_limit": limits["tokens_per_minute"],
            "token_usage_percent": (current_tokens / limits["tokens_per_minute"]) * 100,
            "recent_requests": recent_requests,
            "request_limit": limits["requests_per_minute"],
            "in_backoff": provider in self.backoff_until,
            "backoff_until": self.backoff_until.get(provider, 0),
        }
