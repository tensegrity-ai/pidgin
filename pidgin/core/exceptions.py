"""Custom exceptions for Pidgin core functionality."""


class PidginError(Exception):
    """Base exception for all Pidgin errors."""


class RateLimitError(PidginError):
    """Raised when rate limits are exceeded."""

    def __init__(self, provider: str, wait_time: float, message: str = None):
        self.provider = provider
        self.wait_time = wait_time
        if message is None:
            message = f"Rate limit exceeded for {provider}. Wait {wait_time:.1f}s"
        super().__init__(message)


class ProviderError(PidginError):
    """Base exception for provider-related errors."""


class ProviderTimeoutError(ProviderError):
    """Raised when a provider times out."""

    def __init__(self, provider: str, timeout: float, agent_id: str = None):
        self.provider = provider
        self.timeout = timeout
        self.agent_id = agent_id
        message = f"Provider {provider} timed out after {timeout}s"
        if agent_id:
            message += f" for agent {agent_id}"
        super().__init__(message)


class DatabaseError(PidginError):
    """Base exception for database-related errors."""


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""


class DatabaseLockError(DatabaseError):
    """Raised when database is locked by another process."""


class ExperimentError(PidginError):
    """Base exception for experiment-related errors."""


class ExperimentAlreadyExistsError(ExperimentError):
    """Raised when trying to create an experiment with a duplicate name."""

    def __init__(self, name: str, existing_id: str):
        self.name = name
        self.existing_id = existing_id
        super().__init__(f"Experiment '{name}' already exists with ID: {existing_id}")


class ExperimentNotFoundError(ExperimentError):
    """Raised when an experiment cannot be found."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Experiment not found: {identifier}")
