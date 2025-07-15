"""Tests for logger module."""

import pytest
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from pidgin.io.logger import get_logger, setup_logging


class TestGetLogger:
    """Test get_logger function."""
    
    def test_get_logger_basic(self):
        """Test basic logger creation."""
        logger = get_logger("test")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "pidgin.test"
    
    def test_get_logger_different_names(self):
        """Test that different names create different loggers."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        assert logger1.name == "pidgin.module1"
        assert logger2.name == "pidgin.module2"
        assert logger1 is not logger2
    
    def test_get_logger_same_name_returns_same_instance(self):
        """Test that same name returns the same logger instance."""
        logger1 = get_logger("same_module")
        logger2 = get_logger("same_module")
        
        assert logger1 is logger2


class TestSetupLogging:
    """Test setup_logging function."""
    
    def setup_method(self):
        """Clean up logging state before each test."""
        # Clear any existing handlers
        pidgin_logger = logging.getLogger("pidgin")
        pidgin_logger.handlers.clear()
        pidgin_logger.setLevel(logging.NOTSET)
        pidgin_logger.propagate = True
    
    def test_setup_logging_default(self):
        """Test setup_logging with default parameters."""
        setup_logging()
        
        pidgin_logger = logging.getLogger("pidgin")
        
        assert pidgin_logger.level == logging.INFO
        assert len(pidgin_logger.handlers) == 1
        assert pidgin_logger.propagate is False
    
    def test_setup_logging_debug_level(self):
        """Test setup_logging with DEBUG level."""
        setup_logging(level="DEBUG")
        
        pidgin_logger = logging.getLogger("pidgin")
        
        assert pidgin_logger.level == logging.DEBUG
        assert pidgin_logger.handlers[0].level == logging.DEBUG
    
    def test_setup_logging_warning_level(self):
        """Test setup_logging with WARNING level."""
        setup_logging(level="WARNING")
        
        pidgin_logger = logging.getLogger("pidgin")
        
        assert pidgin_logger.level == logging.WARNING
        assert pidgin_logger.handlers[0].level == logging.WARNING
    
    def test_setup_logging_error_level(self):
        """Test setup_logging with ERROR level."""
        setup_logging(level="ERROR")
        
        pidgin_logger = logging.getLogger("pidgin")
        
        assert pidgin_logger.level == logging.ERROR
        assert pidgin_logger.handlers[0].level == logging.ERROR
    
    def test_setup_logging_case_insensitive(self):
        """Test setup_logging with lowercase level."""
        setup_logging(level="debug")
        
        pidgin_logger = logging.getLogger("pidgin")
        
        assert pidgin_logger.level == logging.DEBUG
    
    def test_setup_logging_with_file(self):
        """Test setup_logging with file handler."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            setup_logging(level="INFO", log_file=tmp_path)
            
            pidgin_logger = logging.getLogger("pidgin")
            
            # Should have console handler + file handler
            assert len(pidgin_logger.handlers) == 2
            
            # Check that one handler is a FileHandler
            file_handlers = [h for h in pidgin_logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) == 1
            
            # Test that logging to file works
            logger = get_logger("test_file")
            logger.info("Test message")
            
            # Read the file to verify message was written
            with open(tmp_path, 'r') as f:
                content = f.read()
                assert "Test message" in content
                assert "pidgin.test_file" in content
        
        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)
    
    def test_setup_logging_no_propagate(self):
        """Test that setup_logging sets propagate to False."""
        setup_logging()
        
        pidgin_logger = logging.getLogger("pidgin")
        
        assert pidgin_logger.propagate is False
    
    def test_setup_logging_rich_handler_configuration(self):
        """Test that RichHandler is configured correctly."""
        with patch('pidgin.io.logger.RichHandler') as mock_rich_handler:
            mock_handler = MagicMock()
            mock_rich_handler.return_value = mock_handler
            
            setup_logging()
            
            # Verify RichHandler was created with correct parameters
            mock_rich_handler.assert_called_once_with(
                rich_tracebacks=True,
                tracebacks_show_locals=False,
                tracebacks_suppress=[],
                show_time=False,
                show_path=False,
            )
            
            # Verify handler was added to logger
            pidgin_logger = logging.getLogger("pidgin")
            assert mock_handler in pidgin_logger.handlers
    
    def test_setup_logging_file_formatter(self):
        """Test that file handler has correct formatter."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            setup_logging(level="INFO", log_file=tmp_path)
            
            pidgin_logger = logging.getLogger("pidgin")
            
            # Find the file handler
            file_handlers = [h for h in pidgin_logger.handlers if isinstance(h, logging.FileHandler)]
            file_handler = file_handlers[0]
            
            # Check formatter format
            formatter = file_handler.formatter
            assert formatter._fmt == '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)


class TestModuleInitialization:
    """Test module initialization behavior."""
    
    def test_module_initializes_logging_on_import(self):
        """Test that importing the module sets up logging."""
        # This test verifies the module-level setup_logging() call
        # Since the module is already imported, we check the current state
        
        pidgin_logger = logging.getLogger("pidgin")
        
        # Should have at least one handler (from module initialization)
        assert len(pidgin_logger.handlers) >= 1
        assert pidgin_logger.propagate is False