"""Tests for core exceptions module."""

import pytest
from pidgin.core.exceptions import (
    PidginError,
    RateLimitError,
    ProviderError,
    ProviderTimeoutError,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseLockError,
    ExperimentError,
    ExperimentAlreadyExistsError,
    ExperimentNotFoundError,
)


class TestPidginError:
    """Test base PidginError exception."""
    
    def test_base_exception(self):
        """Test that PidginError is a proper exception."""
        with pytest.raises(PidginError):
            raise PidginError("Test error")
    
    def test_inheritance(self):
        """Test that PidginError inherits from Exception."""
        assert issubclass(PidginError, Exception)


class TestRateLimitError:
    """Test RateLimitError exception."""
    
    def test_default_message(self):
        """Test default error message generation."""
        error = RateLimitError("OpenAI", 5.5)
        assert str(error) == "Rate limit exceeded for OpenAI. Wait 5.5s"
        assert error.provider == "OpenAI"
        assert error.wait_time == 5.5
    
    def test_custom_message(self):
        """Test custom error message."""
        error = RateLimitError("Anthropic", 10.0, "Custom rate limit message")
        assert str(error) == "Custom rate limit message"
        assert error.provider == "Anthropic"
        assert error.wait_time == 10.0
    
    def test_inheritance(self):
        """Test that RateLimitError inherits from PidginError."""
        assert issubclass(RateLimitError, PidginError)


class TestProviderErrors:
    """Test provider-related exceptions."""
    
    def test_provider_error_base(self):
        """Test base ProviderError."""
        with pytest.raises(ProviderError):
            raise ProviderError("Provider failed")
        
        assert issubclass(ProviderError, PidginError)
    
    def test_provider_timeout_error_basic(self):
        """Test ProviderTimeoutError without agent_id."""
        error = ProviderTimeoutError("Google", 30.0)
        assert str(error) == "Provider Google timed out after 30.0s"
        assert error.provider == "Google"
        assert error.timeout == 30.0
        assert error.agent_id is None
    
    def test_provider_timeout_error_with_agent(self):
        """Test ProviderTimeoutError with agent_id."""
        error = ProviderTimeoutError("OpenAI", 15.0, "agent_a")
        assert str(error) == "Provider OpenAI timed out after 15.0s for agent agent_a"
        assert error.provider == "OpenAI"
        assert error.timeout == 15.0
        assert error.agent_id == "agent_a"
    
    def test_provider_timeout_inheritance(self):
        """Test that ProviderTimeoutError inherits correctly."""
        assert issubclass(ProviderTimeoutError, ProviderError)
        assert issubclass(ProviderTimeoutError, PidginError)


class TestDatabaseErrors:
    """Test database-related exceptions."""
    
    def test_database_error_base(self):
        """Test base DatabaseError."""
        with pytest.raises(DatabaseError):
            raise DatabaseError("Database operation failed")
        
        assert issubclass(DatabaseError, PidginError)
    
    def test_database_connection_error(self):
        """Test DatabaseConnectionError."""
        with pytest.raises(DatabaseConnectionError):
            raise DatabaseConnectionError("Cannot connect to database")
        
        assert issubclass(DatabaseConnectionError, DatabaseError)
    
    def test_database_lock_error(self):
        """Test DatabaseLockError."""
        with pytest.raises(DatabaseLockError):
            raise DatabaseLockError("Database is locked")
        
        assert issubclass(DatabaseLockError, DatabaseError)


class TestExperimentErrors:
    """Test experiment-related exceptions."""
    
    def test_experiment_error_base(self):
        """Test base ExperimentError."""
        with pytest.raises(ExperimentError):
            raise ExperimentError("Experiment operation failed")
        
        assert issubclass(ExperimentError, PidginError)
    
    def test_experiment_already_exists_error(self):
        """Test ExperimentAlreadyExistsError."""
        error = ExperimentAlreadyExistsError("my_experiment", "exp_123")
        assert str(error) == "Experiment 'my_experiment' already exists with ID: exp_123"
        assert error.name == "my_experiment"
        assert error.existing_id == "exp_123"
        
        assert issubclass(ExperimentAlreadyExistsError, ExperimentError)
    
    def test_experiment_not_found_error(self):
        """Test ExperimentNotFoundError."""
        error = ExperimentNotFoundError("exp_456")
        assert str(error) == "Experiment not found: exp_456"
        assert error.identifier == "exp_456"
        
        assert issubclass(ExperimentNotFoundError, ExperimentError)