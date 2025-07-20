"""Common error handling utilities for providers."""

from typing import Dict, List, Optional


class ProviderErrorHandler:
    """Base error handler with common error mapping functionality."""

    # Base friendly errors common to most providers
    BASE_FRIENDLY_ERRORS: Dict[str, str] = {
        "rate_limit": "Rate limit reached. The system will automatically retry with exponential backoff...",
        "429": "Too many requests. Waiting before retrying (this is normal for high-volume usage)...",
        "authentication": "Authentication failed. Please verify your API key is correct and has the necessary permissions",
        "authentication_error": "Authentication failed. Please verify your API key is correct and has the necessary permissions",
        "not_found": "Model not found. Please verify the model name is correct and you have access to it",
        "model_not_found": "Model not found. Please verify the model name is correct and you have access to it",
        "invalid_api_key": "Invalid API key. Please check your environment variable and ensure the key is active",
        "server_error": "API server error. The system will automatically retry (this is usually temporary)...",
        "timeout": "Request timed out. The system will automatically retry with a longer timeout...",
        "readtimeout": "Request timed out. The system will automatically retry with a longer timeout...",
        "read timeout": "Request timed out. The system will automatically retry with a longer timeout...",
        "connection": "Connection error. Please check your internet connection. Retrying...",
        "503": "Service temporarily unavailable. The API is experiencing high load. Retrying...",
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
    "credit_balance_too_low": "Anthropic API credit balance is too low.\n\nTo add credits:\n1. Visit console.anthropic.com\n2. Go to Billing → Add Credits\n3. Add at least $5 to continue",
    "overloaded_error": "Anthropic API is temporarily overloaded (this is common during peak hours).\n\nThe system will automatically retry with exponential backoff...",
    "permission_error": "Your API key doesn't have permission to use this model.\n\nPlease check:\n1. Your plan supports this model\n2. The model name is correct (e.g., 'claude-3-opus-20240229')",
    "rate_limit_error": "Anthropic rate limit reached.\n\nThis is normal for high-volume usage. The system will:\n1. Automatically retry with backoff\n2. Continue your conversation seamlessly",
}

OPENAI_ERRORS = {
    "insufficient_quota": "OpenAI API quota exceeded.\n\nTo resolve:\n1. Visit platform.openai.com\n2. Go to Settings → Billing\n3. Add payment method or increase spending limit",
    "billing": "OpenAI API billing issue detected.\n\nPlease:\n1. Visit platform.openai.com\n2. Go to Settings → Billing\n3. Update your payment method",
    "readtimeout": "OpenAI API request timed out (this can happen with long responses).\n\nThe system will automatically retry with a longer timeout...",
    "rate_limit_error": "OpenAI rate limit reached.\n\nYour current plan limits:\n- Requests per minute (RPM)\n- Tokens per minute (TPM)\n\nThe system will automatically retry with backoff...",
}

GOOGLE_ERRORS = {
    "quota_exceeded": "Google API quota exceeded.\n\nTo check your quota:\n1. Visit console.cloud.google.com\n2. Go to APIs & Services → Quotas\n3. Look for Gemini API quotas",
    "invalid_argument": "Invalid request parameters.\n\nPlease verify:\n1. Model name (e.g., 'gemini-1.5-pro-latest')\n2. Message format is correct\n3. No unsupported parameters",
    "resource_exhausted": "Google API rate limit reached (default: 60 requests/minute).\n\nThe system will automatically retry with exponential backoff...",
    "deadline_exceeded": "Google API request timed out.\n\nThis can happen with:\n- Large contexts\n- Complex requests\n\nRetrying with extended timeout...",
    "permission_denied": "Permission denied for Google API.\n\nPlease check:\n1. API key is valid\n2. Gemini API is enabled in your project\n3. Billing is set up if required",
    "unavailable": "Google API temporarily unavailable (503 error).\n\nThis is usually brief. The system will automatically retry...",
}

XAI_ERRORS = {
    "rate_limit": "xAI API rate limit reached.\n\nGrok models have usage limits. The system will:\n1. Automatically retry with backoff\n2. Continue your conversation when ready",
    "insufficient_quota": "xAI API quota exceeded.\n\nPlease check your usage and limits at x.ai",
    "authentication_error": "xAI authentication failed.\n\nPlease verify:\n1. Your XAI_API_KEY is correct\n2. Your account is active\n3. You have access to Grok models",
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


def create_xai_error_handler() -> ProviderErrorHandler:
    """Create error handler for xAI provider."""
    return ProviderErrorHandler(
        provider_name="xAI",
        custom_errors=XAI_ERRORS,
        custom_suppress=["rate_limit", "insufficient_quota"],
    )
