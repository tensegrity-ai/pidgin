"""Logging configuration for Pidgin."""

import logging

from rich.logging import RichHandler


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"pidgin.{name}")


def setup_logging(level: str = "INFO", log_file: str = None):
    """Configure logging for Pidgin.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to write logs to
    """
    # Configure root logger for pidgin
    logger = logging.getLogger("pidgin")
    logger.setLevel(getattr(logging, level.upper()))

    # Rich console handler for beautiful output
    console_handler = RichHandler(
        rich_tracebacks=True,  # Beautiful tracebacks
        tracebacks_show_locals=False,  # Don't show local variables (too noisy)
        tracebacks_suppress=[],  # Show all frames for now
        show_time=False,  # Don't show timestamps (cleaner)
        show_path=False,  # Don't show file paths (cleaner)
    )
    console_handler.setLevel(getattr(logging, level.upper()))
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)

    # Don't propagate to root logger
    logger.propagate = False


# Initialize Rich logging when this module is imported
# This ensures all loggers use Rich formatting
setup_logging()
