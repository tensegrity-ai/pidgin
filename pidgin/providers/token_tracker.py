"""Global token usage tracking for rate limit management."""

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, Optional, Tuple

from ..config.config import Config
from ..io.logger import get_logger

logger = get_logger("token_tracker")


@dataclass
class TokenUsage:
    """Record of token usage at a point in time."""

    timestamp: float
    tokens: int
    model: str


class GlobalTokenTracker:
    """Tracks token usage across all conversations for rate limit management.

    Maintains a sliding window of token usage per provider to ensure
    we stay within rate limits.
    """

    # Default rate limits - conservative estimates for stable operation
    DEFAULT_RATE_LIMITS = {
        "anthropic": {
            "requests_per_minute": 50,  # Haiku tier
            "tokens_per_minute": 40000,  # Conservative for Haiku
        },
        "openai": {
            "requests_per_minute": 60,  # GPT-4 tier
            "tokens_per_minute": 90000,  # GPT-4 tier
        },
        "google": {
            "requests_per_minute": 60,  # Gemini estimates
            "tokens_per_minute": 60000,  # Conservative estimate
        },
        "xai": {
            "requests_per_minute": 60,  # Grok estimates
            "tokens_per_minute": 60000,  # Conservative estimate
        },
    }

    def __init__(self, config: Config):
        """Initialize token tracker with configuration.

        Args:
            config: Application configuration
        """
        self.config_obj = config
        self.config = config.get("providers.rate_limiting", {})
        self._load_limits()

        # Thread-safe usage history per provider
        self.usage_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.lock = Lock()

        # Track backoff state per provider
        self.backoff_until: Dict[str, float] = {}
        self.consecutive_errors: Dict[str, int] = defaultdict(int)

    def _load_limits(self):
        """Load rate limits from config with defaults."""
        self.rate_limits = self.DEFAULT_RATE_LIMITS.copy()

        # Override with config if provided
        overrides = self.config_obj.get("providers.overrides", {})
        for provider, settings in overrides.items():
            if provider not in self.rate_limits:
                self.rate_limits[provider] = {}
            if "tokens_per_minute" in settings:
                self.rate_limits[provider]["tokens_per_minute"] = settings[
                    "tokens_per_minute"
                ]
            if "requests_per_minute" in settings:
                self.rate_limits[provider]["requests_per_minute"] = settings[
                    "requests_per_minute"
                ]

    def record_usage(
        self, provider: str, tokens: int, model: str, timestamp: Optional[float] = None
    ):
        """Record token usage for a provider.

        Args:
            provider: Provider name (anthropic, openai, etc)
            tokens: Number of tokens used
            model: Specific model used
            timestamp: Optional timestamp (defaults to now)
        """
        if not self.config.get("enabled", True):
            return

        provider_key = provider.lower().replace("provider", "")
        timestamp = timestamp or time.time()

        with self.lock:
            usage = TokenUsage(timestamp, tokens, model)
            self.usage_history[provider_key].append(usage)

            # Reset error count on successful usage
            self.consecutive_errors[provider_key] = 0

        logger.debug(
            f"Recorded {tokens} tokens for {provider_key}/{model} at {timestamp:.2f}"
        )

    def get_current_rate(self, provider: str) -> float:
        """Get current token usage rate (tokens per minute).

        Args:
            provider: Provider name

        Returns:
            Current tokens per minute rate
        """
        provider_key = provider.lower().replace("provider", "")
        window_minutes = self.config.get("sliding_window_minutes", 1.0)
        window_seconds = window_minutes * 60

        current_time = time.time()
        cutoff_time = current_time - window_seconds

        with self.lock:
            history = self.usage_history.get(provider_key, deque())

            # Sum tokens within the window
            recent_tokens = sum(
                usage.tokens for usage in history if usage.timestamp >= cutoff_time
            )

        # Convert to per-minute rate
        rate = recent_tokens / window_minutes
        return rate

    def can_make_request(
        self, provider: str, estimated_tokens: int, model: Optional[str] = None
    ) -> Tuple[bool, Optional[float]]:
        """Check if we can make a request without exceeding rate limits.

        Args:
            provider: Provider name
            estimated_tokens: Estimated tokens for the request
            model: Optional specific model

        Returns:
            Tuple of (can_proceed, wait_seconds_if_not)
        """
        if not self.config.get("enabled", True):
            return True, None

        provider_key = provider.lower().replace("provider", "")

        # Check if we're in backoff
        if provider_key in self.backoff_until:
            wait_time = self.backoff_until[provider_key] - time.time()
            if wait_time > 0:
                return False, wait_time
            else:
                # Backoff expired
                del self.backoff_until[provider_key]

        # Get rate limit with safety margin
        safety_margin = self.config.get("safety_margin", 0.9)
        provider_limits = self.rate_limits.get(
            provider_key, {"tokens_per_minute": 60000}
        )
        token_limit = provider_limits.get("tokens_per_minute", 60000)
        safe_limit = token_limit * safety_margin

        # Check current rate + estimated tokens
        current_rate = self.get_current_rate(provider)
        buffer_multiplier = self.config.get("token_estimation_multiplier", 1.1)
        projected_tokens = estimated_tokens * buffer_multiplier

        if current_rate + projected_tokens <= safe_limit:
            return True, None

        # Calculate wait time needed
        excess_tokens = (current_rate + projected_tokens) - safe_limit
        wait_minutes = excess_tokens / token_limit
        wait_seconds = wait_minutes * 60

        logger.info(
            f"Rate limit approaching for {provider_key}: "
            f"{current_rate:.0f} + {projected_tokens:.0f} tokens/min > {safe_limit:.0f}"
        )

        return False, wait_seconds

    def record_error(self, provider: str, error_type: str):
        """Record an API error for backoff calculation.

        Args:
            provider: Provider name
            error_type: Type of error (rate_limit, overloaded, etc)
        """
        provider_key = provider.lower().replace("provider", "")

        with self.lock:
            self.consecutive_errors[provider_key] += 1

        if error_type in ["rate_limit", "429", "overloaded"]:
            backoff_delay = self.get_backoff_delay(provider)
            self.backoff_until[provider_key] = time.time() + backoff_delay

            logger.warning(
                f"Setting backoff for {provider_key}: "
                f"{backoff_delay:.1f}s (error #{self.consecutive_errors[provider_key]})"
            )

    def get_backoff_delay(self, provider: str) -> float:
        """Calculate exponential backoff delay based on consecutive errors.

        Args:
            provider: Provider name

        Returns:
            Backoff delay in seconds
        """
        provider_key = provider.lower().replace("provider", "")
        error_count = self.consecutive_errors.get(provider_key, 0)

        base_delay = self.config.get("backoff_base_delay", 1.0)
        max_delay = self.config.get("backoff_max_delay", 60.0)

        # Exponential backoff: base * 2^(errors-1)
        delay = base_delay * (2 ** max(0, error_count - 1))

        # Cap at maximum
        return min(delay, max_delay)

    def get_usage_stats(self, provider: str) -> Dict[str, Any]:
        """Get usage statistics for a provider.

        Args:
            provider: Provider name

        Returns:
            Dictionary of usage statistics
        """
        provider_key = provider.lower().replace("provider", "")
        current_rate = self.get_current_rate(provider)
        provider_limits = self.rate_limits.get(
            provider_key, {"tokens_per_minute": 60000}
        )
        rate_limit = provider_limits.get("tokens_per_minute", 60000)

        return {
            "current_rate": current_rate,
            "rate_limit": rate_limit,
            "usage_percentage": (
                (current_rate / rate_limit * 100) if rate_limit > 0 else 0
            ),
            "consecutive_errors": self.consecutive_errors.get(provider_key, 0),
            "in_backoff": provider_key in self.backoff_until,
            "backoff_until": self.backoff_until.get(provider_key, 0),
        }
