"""Standardized error handling for CLI commands."""

import sys
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class ErrorType(Enum):
    """Categories of errors for appropriate handling."""

    CONFIG = "Configuration Error"
    FILE_NOT_FOUND = "File Not Found"
    PERMISSION = "Permission Denied"
    API = "API Error"
    VALIDATION = "Validation Error"
    RUNTIME = "Runtime Error"
    SYSTEM = "System Error"
    USER_INTERRUPT = "User Interrupted"


class CLIError(Exception):
    """Base exception for CLI-specific errors."""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.RUNTIME,
        suggestion: Optional[str] = None,
        exit_code: int = 1,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.suggestion = suggestion
        self.exit_code = exit_code


class ConfigError(CLIError):
    """Configuration-related errors."""

    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(message, ErrorType.CONFIG, suggestion, exit_code=2)


class ValidationError(CLIError):
    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(message, ErrorType.VALIDATION, suggestion, exit_code=3)


class FileNotFoundError(CLIError):
    def __init__(self, path: Path, suggestion: Optional[str] = None):
        message = f"File not found: {path}"
        super().__init__(message, ErrorType.FILE_NOT_FOUND, suggestion, exit_code=4)


class APIError(CLIError):
    """API-related errors (rate limits, authentication, etc)."""

    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(message, ErrorType.API, suggestion, exit_code=5)


class CLIErrorHandler:
    """Centralized error handling for CLI commands."""

    def __init__(self, console: Optional[Console] = None, debug: bool = False):
        self.console = console or Console(stderr=True)
        self.debug = debug

    def handle_error(self, error: Exception) -> None:
        """Handle an error with appropriate formatting and exit code."""
        if isinstance(error, KeyboardInterrupt):
            self._handle_interrupt()
        elif isinstance(error, CLIError):
            self._handle_cli_error(error)
        else:
            self._handle_unexpected_error(error)

    def _handle_interrupt(self) -> None:
        """Handle keyboard interrupt gracefully."""
        self.console.print("\n[yellow]✗ Operation cancelled by user[/yellow]")
        sys.exit(130)  # Standard exit code for SIGINT

    def _handle_cli_error(self, error: CLIError) -> None:
        """Handle known CLI errors with formatting."""
        # Build error message
        error_text = Text()
        error_text.append(f"✗ {error.error_type.value}: ", style="bold red")
        error_text.append(str(error))

        # Add suggestion if provided
        if error.suggestion:
            error_text.append("\n\n", style="")
            error_text.append("💡 Suggestion: ", style="bold yellow")
            error_text.append(error.suggestion, style="yellow")

        # Display in a panel
        panel = Panel(
            error_text,
            title="[bold red]Error[/bold red]",
            border_style="red",
            expand=False,
        )
        self.console.print(panel)

        # Show traceback in debug mode
        if self.debug:
            self.console.print("\n[dim]Debug traceback:[/dim]")
            self.console.print_exception(show_locals=True)

        sys.exit(error.exit_code)

    def _handle_unexpected_error(self, error: Exception) -> None:
        """Handle unexpected errors with full traceback."""
        error_text = Text()
        error_text.append("✗ Unexpected error: ", style="bold red")
        error_text.append(str(error))

        panel = Panel(
            error_text,
            title="[bold red]Unexpected Error[/bold red]",
            border_style="red",
            expand=False,
        )
        self.console.print(panel)

        # Always show traceback for unexpected errors
        self.console.print("\n[dim]Full traceback:[/dim]")
        self.console.print_exception(show_locals=self.debug)

        sys.exit(1)

    def wrap_command(self, func: Callable) -> Callable:
        """Decorator to wrap CLI commands with error handling.

        Usage:
            @error_handler.wrap_command
            def my_command():
                ...
        """

        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.handle_error(e)

        return wrapper


# Global instance for convenience
default_handler = CLIErrorHandler()


def handle_cli_error(func: Callable) -> Callable:
    """Decorator for standardized CLI error handling.

    Usage:
        @handle_cli_error
        def my_command():
            ...
    """
    return default_handler.wrap_command(func)
