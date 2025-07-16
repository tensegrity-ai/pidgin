"""Common error handling utilities for providers."""

from typing import Dict, List, Optional


class ProviderErrorHandler:
    """Base error handler with common error mapping functionality."""

    # Base friendly errors common to most providers
    BASE_FRIENDLY_ERRORS: Dict[str, str] = {
        "rate_limit": "Rate limit reached. The system will automatically retry...",
        "authentication": "Authentication failed. Please verify your API key",
        "authentication_error": "Authentication failed. Please verify your API key",
        "not_found": "Model not found. Please verify the model name is correct",
        "model_not_found": "Model not found. Please verify the model name is correct",
        "invalid_api_key": "Invalid API key. Please check your environment variable",
        "server_error": "API server error. The system will automatically retry...",
        "timeout": "Request timed out. The system will automatically retry...",
        "readtimeout": "Request timed out. The system will automatically retry...",
        "read timeout": "Request timed out. The system will automatically retry...",
    }

    # Base errors that should suppress traceback
    BASE_SUPPRESS_TRACEBACK: List[str] = [
        "invalid_api_key",
        "authentication",
        "authentication_error",
        "quota",
        "billing",
        "payment",
        "credit",
        "insufficient",
        "timeout",
        "readtimeout",
        "read timeout",
    ]

    def __init__(
        self,
        provider_name: str,
        custom_errors: Optional[Dict[str, str]] = None,
        custom_suppress: Optional[List[str]] = None,
    ):
        """Initialize error handler with provider-specific customizations.

        Args:
            provider_name: Name of the provider (for error messages)
            custom_errors: Provider-specific error mappings to add/override
            custom_suppress: Provider-specific traceback suppression patterns
        """
        self.provider_name = provider_name

        # Merge base and custom error mappings
        self.friendly_errors = self.BASE_FRIENDLY_ERRORS.copy()
        if custom_errors:
            self.friendly_errors.update(custom_errors)

        # Merge base and custom suppression patterns
        self.suppress_traceback_errors = self.BASE_SUPPRESS_TRACEBACK.copy()
        if custom_suppress:
            self.suppress_traceback_errors.extend(custom_suppress)

    def get_friendly_error(self, error: Exception) -> str:
        """Convert technical API errors to user-friendly messages.

        Args:
            error: The exception to convert

        Returns:
            User-friendly error message
        """
        error_str = str(error).lower()
        error_type = getattr(error, "__class__.__name__", "").lower()

        # Check error message content and type
        # First check for exact matches in error type
        if error_type in self.friendly_errors:
            return self.friendly_errors[error_type]

        # Then check for patterns in error string
        for key, friendly_msg in self.friendly_errors.items():
            # Check if key (with underscores replaced) is in error string
            if key.replace("_", " ") in error_str:
                return friendly_msg
            # Check if key is in error type name
            if key in error_type:
                return friendly_msg
            # Check if key is directly in error string
            if key in error_str:
                return friendly_msg
            # Special handling for timeout errors - check for "timed out"
            if key == "timeout" and "timed out" in error_str:
                return friendly_msg
            # Special handling for resource exhausted - it's a rate limit
            if key == "resource_exhausted" and "resource exhausted" in error_str:
                return friendly_msg

        # Fallback to original error
        return str(error)

    def should_suppress_traceback(self, error: Exception) -> bool:
        """Check if we should suppress the full traceback for this error.

        Args:
            error: The exception to check

        Returns:
            True if traceback should be suppressed
        """
        error_str = str(error).lower()
        error_type = getattr(error, "__class__.__name__", "").lower()

        return any(
            phrase in error_str or phrase in error_type
            for phrase in self.suppress_traceback_errors
        )


# Provider-specific error configurations
ANTHROPIC_ERRORS = {
    "credit_balance_too_low": "Anthropic API credit balance is too low. Please add credits at console.anthropic.com → Billing",
    "overloaded_error": "Anthropic API is temporarily overloaded. Retrying...",
    "permission_error": "Your API key doesn't have permission to use this model",
}

OPENAI_ERRORS = {
    "insufficient_quota": "OpenAI API quota exceeded. Please check your billing at platform.openai.com",
    "billing": "OpenAI API billing issue. Please update payment method at platform.openai.com",
    "readtimeout": "OpenAI API request timed out. The system will automatically retry...",
}

GOOGLE_ERRORS = {
    "quota_exceeded": "Google API quota exceeded. Please check your usage at console.cloud.google.com",
    "invalid_argument": "Invalid request parameters. Please check the model name and message format",
    "resource_exhausted": "Google API rate limit reached. The system will automatically retry...",
    "deadline_exceeded": "Google API request timed out. The system will automatically retry...",
    "permission_denied": "Permission denied. Please check your API key permissions",
    "unavailable": "Google API temporarily unavailable. The system will automatically retry...",
}


def create_anthropic_error_handler() -> ProviderErrorHandler:
    """Create error handler for Anthropic provider."""
    return ProviderErrorHandler(
        provider_name="Anthropic",
        custom_errors=ANTHROPIC_ERRORS,
        custom_suppress=["overloaded_error", "permission_error"],
    )


def create_openai_error_handler() -> ProviderErrorHandler:
    """Create error handler for OpenAI provider."""
    return ProviderErrorHandler(
        provider_name="OpenAI",
        custom_errors=OPENAI_ERRORS,
        custom_suppress=["insufficient_quota", "readtimeout"],
    )


def create_google_error_handler() -> ProviderErrorHandler:
    """Create error handler for Google provider."""
    return ProviderErrorHandler(
        provider_name="Google",
        custom_errors=GOOGLE_ERRORS,
        custom_suppress=[
            "quota_exceeded",
            "invalid_argument",
            "resource_exhausted",
            "deadline_exceeded",
            "permission_denied",
            "unavailable",
        ],
    )
