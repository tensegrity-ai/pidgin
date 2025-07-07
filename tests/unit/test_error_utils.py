"""Test provider error handling utilities."""

import pytest
from unittest.mock import Mock

from pidgin.providers.error_utils import (
    ProviderErrorHandler,
    create_anthropic_error_handler,
    create_openai_error_handler,
    create_google_error_handler,
)


class TestProviderErrorHandler:
    """Test suite for ProviderErrorHandler."""
    
    def test_initialization_base_only(self):
        """Test initialization with base errors only."""
        handler = ProviderErrorHandler("TestProvider")
        
        assert handler.provider_name == "TestProvider"
        assert "rate_limit" in handler.friendly_errors
        assert "authentication" in handler.friendly_errors
        assert "invalid_api_key" in handler.suppress_traceback_errors
    
    def test_initialization_with_custom(self):
        """Test initialization with custom errors."""
        custom_errors = {"custom_error": "Custom error message"}
        custom_suppress = ["custom_pattern"]
        
        handler = ProviderErrorHandler(
            "TestProvider",
            custom_errors=custom_errors,
            custom_suppress=custom_suppress
        )
        
        # Should have both base and custom
        assert "rate_limit" in handler.friendly_errors
        assert "custom_error" in handler.friendly_errors
        assert "invalid_api_key" in handler.suppress_traceback_errors
        assert "custom_pattern" in handler.suppress_traceback_errors
    
    def test_custom_overrides_base(self):
        """Test that custom errors override base errors."""
        custom_errors = {"rate_limit": "Custom rate limit message"}
        
        handler = ProviderErrorHandler("TestProvider", custom_errors=custom_errors)
        
        assert handler.friendly_errors["rate_limit"] == "Custom rate limit message"
    
    def test_get_friendly_error_exact_match(self):
        """Test getting friendly error with exact key match."""
        handler = ProviderErrorHandler("TestProvider")
        
        error = Exception("rate_limit error occurred")
        friendly = handler.get_friendly_error(error)
        
        assert friendly == "Rate limit reached. The system will automatically retry..."
    
    def test_get_friendly_error_underscore_to_space(self):
        """Test error matching with underscores converted to spaces."""
        handler = ProviderErrorHandler("TestProvider")
        
        error = Exception("rate limit exceeded")
        friendly = handler.get_friendly_error(error)
        
        assert friendly == "Rate limit reached. The system will automatically retry..."
    
    def test_get_friendly_error_message_content(self):
        """Test error matching on message content."""
        handler = ProviderErrorHandler("TestProvider")
        
        # Test that authentication errors are caught in the message
        error = Exception("Authentication failed for user")
        friendly = handler.get_friendly_error(error)
        assert friendly == "Authentication failed. Please verify your API key"
        
        # Test another pattern
        error2 = Exception("Rate limit exceeded")
        friendly2 = handler.get_friendly_error(error2)
        assert friendly2 == "Rate limit reached. The system will automatically retry..."
    
    def test_get_friendly_error_no_match(self):
        """Test fallback to original error when no match."""
        handler = ProviderErrorHandler("TestProvider")
        
        error = Exception("Unknown error type")
        friendly = handler.get_friendly_error(error)
        
        assert friendly == "Unknown error type"
    
    def test_should_suppress_traceback_match(self):
        """Test traceback suppression for matching errors."""
        handler = ProviderErrorHandler("TestProvider")
        
        # Test various matching patterns
        assert handler.should_suppress_traceback(Exception("invalid_api_key"))
        assert handler.should_suppress_traceback(Exception("Authentication failed"))
        assert handler.should_suppress_traceback(Exception("Quota exceeded"))
        assert handler.should_suppress_traceback(Exception("billing issue"))
    
    def test_should_suppress_traceback_message_content(self):
        """Test traceback suppression based on message content."""
        handler = ProviderErrorHandler("TestProvider")
        
        # Test various patterns that should be suppressed
        assert handler.should_suppress_traceback(Exception("Quota exceeded"))
        assert handler.should_suppress_traceback(Exception("Billing failed"))
        assert handler.should_suppress_traceback(Exception("Payment required"))
        assert handler.should_suppress_traceback(Exception("invalid_api_key error"))
    
    def test_should_suppress_traceback_no_match(self):
        """Test no suppression for non-matching errors."""
        handler = ProviderErrorHandler("TestProvider")
        
        assert not handler.should_suppress_traceback(Exception("Server error"))
        assert not handler.should_suppress_traceback(Exception("Unknown issue"))


class TestProviderSpecificHandlers:
    """Test provider-specific error handler factories."""
    
    def test_anthropic_handler(self):
        """Test Anthropic-specific error handler."""
        handler = create_anthropic_error_handler()
        
        assert handler.provider_name == "Anthropic"
        
        # Check Anthropic-specific errors
        error = Exception("credit_balance_too_low")
        assert "console.anthropic.com" in handler.get_friendly_error(error)
        
        # Check Anthropic-specific suppression
        assert handler.should_suppress_traceback(Exception("overloaded_error"))
        assert handler.should_suppress_traceback(Exception("permission_error"))
    
    def test_openai_handler(self):
        """Test OpenAI-specific error handler."""
        handler = create_openai_error_handler()
        
        assert handler.provider_name == "OpenAI"
        
        # Check OpenAI-specific errors
        error = Exception("insufficient_quota")
        assert "platform.openai.com" in handler.get_friendly_error(error)
        
        # Check OpenAI-specific suppression
        assert handler.should_suppress_traceback(Exception("insufficient_quota"))
    
    def test_google_handler(self):
        """Test Google-specific error handler."""
        handler = create_google_error_handler()
        
        assert handler.provider_name == "Google"
        
        # Check Google-specific errors
        error = Exception("quota_exceeded")
        assert "console.cloud.google.com" in handler.get_friendly_error(error)
        
        # Check Google-specific suppression
        assert handler.should_suppress_traceback(Exception("quota_exceeded"))
        assert handler.should_suppress_traceback(Exception("invalid_argument"))
    
    def test_all_handlers_have_base_errors(self):
        """Test that all handlers include base errors."""
        handlers = [
            create_anthropic_error_handler(),
            create_openai_error_handler(),
            create_google_error_handler(),
        ]
        
        for handler in handlers:
            # All should have base errors
            assert "rate_limit" in handler.friendly_errors
            assert "authentication" in handler.friendly_errors
            
            # All should have base suppression patterns
            assert "invalid_api_key" in handler.suppress_traceback_errors
            assert "billing" in handler.suppress_traceback_errors