"""Logging configuration for Pidgin."""
import logging
import sys


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
    
    # Console handler with clean format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(console_handler)
    
    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(file_handler)
    
    # Don't propagate to root logger
    logger.propagate = False