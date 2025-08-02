"""Tests for DisplayManager."""

from unittest.mock import MagicMock, patch

import pytest

from pidgin.cli.display_manager import DisplayManager


class TestDisplayManager:
    """Test DisplayManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = MagicMock()
        self.manager = DisplayManager(console=self.console)
        # Mock the display attribute
        self.manager.display = MagicMock()

    def test_validate_display_flags_valid(self):
        """Test validating display flags with valid combinations."""
        # No flags
        assert self.manager.validate_display_flags(False, False) is True
        
        # Only quiet
        assert self.manager.validate_display_flags(True, False) is True
        
        # Only tail
        assert self.manager.validate_display_flags(False, True) is True

    def test_validate_display_flags_invalid(self):
        """Test validating display flags with invalid combinations."""
        # Both flags set
        assert self.manager.validate_display_flags(True, True) is False
        
        # Verify error message
        self.console.print.assert_called_with(
            "[#bf616a]Error: Can only use one of --quiet or --tail[/#bf616a]"
        )

    def test_determine_display_mode_default(self):
        """Test determining display mode with default settings."""
        mode, quiet, notify = self.manager.determine_display_mode(False, False)
        
        assert mode == "chat"
        assert quiet is False
        assert notify is False

    def test_determine_display_mode_quiet(self):
        """Test determining display mode with quiet flag."""
        mode, quiet, notify = self.manager.determine_display_mode(True, False)
        
        assert mode == "quiet"
        assert quiet is True
        assert notify is True

    def test_determine_display_mode_tail(self):
        """Test determining display mode with tail flag."""
        mode, quiet, notify = self.manager.determine_display_mode(False, True)
        
        assert mode == "tail"
        assert quiet is False
        assert notify is False

    def test_determine_display_mode_parallel_forces_quiet(self):
        """Test that parallel execution forces quiet mode."""
        mode, quiet, notify = self.manager.determine_display_mode(False, False, max_parallel=4)
        
        assert mode == "quiet"
        assert quiet is True
        assert notify is True
        
        # Verify warning was shown
        self.manager.display.warning.assert_called_with(
            "Parallel execution (max_parallel=4) requires quiet mode",
            use_panel=False,
        )

    def test_determine_display_mode_already_quiet_with_parallel(self):
        """Test parallel execution when already in quiet mode."""
        mode, quiet, notify = self.manager.determine_display_mode(True, False, max_parallel=4)
        
        assert mode == "quiet"
        assert quiet is True
        assert notify is True
        
        # No warning should be shown
        self.manager.display.warning.assert_not_called()

    def test_determine_experiment_display_mode_chat(self):
        """Test determining experiment display mode for chat."""
        mode = self.manager.determine_experiment_display_mode("chat", 1, False)
        assert mode == "chat"

    def test_determine_experiment_display_mode_quiet(self):
        """Test determining experiment display mode for quiet."""
        mode = self.manager.determine_experiment_display_mode("quiet", 1, True)
        assert mode == "none"

    def test_determine_experiment_display_mode_parallel(self):
        """Test determining experiment display mode for parallel execution."""
        mode = self.manager.determine_experiment_display_mode("chat", 4, False)
        assert mode == "none"
        
        # Warning should be shown for incompatible mode
        self.manager.display.warning.assert_called_with(
            "--chat is not supported with parallel execution",
            use_panel=False,
        )

    def test_determine_experiment_display_mode_tail_with_parallel(self):
        """Test tail mode with parallel execution."""
        mode = self.manager.determine_experiment_display_mode("tail", 4, False)
        assert mode == "none"
        
        # Warning should be shown
        self.manager.display.warning.assert_called_with(
            "--tail is not supported with parallel execution",
            use_panel=False,
        )

    def test_handle_meditation_mode_disabled(self):
        """Test meditation mode when disabled."""
        agent_a, agent_b = self.manager.handle_meditation_mode(False, "claude", "gpt")
        
        assert agent_a == "claude"
        assert agent_b == "gpt"
        
        # No message should be printed
        self.console.print.assert_not_called()

    def test_handle_meditation_mode_with_agents(self):
        """Test meditation mode with agents already specified."""
        agent_a, agent_b = self.manager.handle_meditation_mode(True, "gpt", "gemini")
        
        assert agent_a == "gpt"
        assert agent_b == "gemini"
        
        # Message should be printed
        self.console.print.assert_called_with(
            "\n[#88c0d0]◆ Meditation mode: gpt → silence[/#88c0d0]"
        )

    def test_handle_meditation_mode_defaults(self):
        """Test meditation mode with default agents."""
        agent_a, agent_b = self.manager.handle_meditation_mode(True, None, None)
        
        assert agent_a == "claude"
        assert agent_b == "silent"
        
        # Message should be printed
        self.console.print.assert_called_with(
            "\n[#88c0d0]◆ Meditation mode: claude → silence[/#88c0d0]"
        )

    def test_handle_meditation_mode_partial_defaults(self):
        """Test meditation mode with partial defaults."""
        # Only agent_a provided
        agent_a, agent_b = self.manager.handle_meditation_mode(True, "gpt", None)
        assert agent_a == "gpt"
        assert agent_b == "silent"
        
        # Only agent_b provided
        agent_a, agent_b = self.manager.handle_meditation_mode(True, None, "custom")
        assert agent_a == "claude"
        assert agent_b == "custom"

    def test_handle_model_selection_error_keyboard_interrupt(self):
        """Test handling keyboard interrupt during model selection."""
        error = KeyboardInterrupt()
        self.manager.handle_model_selection_error(error, "KeyboardInterrupt")
        
        # Verify newline was called (first call)
        assert self.console.print.call_count >= 1
        # Check if first call was empty (for newline)
        if self.console.print.call_args_list[0] == ((),):
            # First call was newline
            pass
        
        # Verify warning
        self.manager.display.warning.assert_called_with(
            "Model selection cancelled",
            context=(
                "Use -a and -b flags to specify models.\n"
                "Example: pidgin run -a claude -b gpt"
            ),
            use_panel=False,
        )

    def test_handle_model_selection_error_eof(self):
        """Test handling EOF error during model selection."""
        error = EOFError()
        self.manager.handle_model_selection_error(error, "EOFError")
        
        # Verify newline was called
        assert self.console.print.call_count >= 1
        
        # Should show same warning as keyboard interrupt
        self.manager.display.warning.assert_called_with(
            "Model selection cancelled",
            context=(
                "Use -a and -b flags to specify models.\n"
                "Example: pidgin run -a claude -b gpt"
            ),
            use_panel=False,
        )

    def test_handle_model_selection_error_general_exception(self):
        """Test handling general exception during model selection."""
        error = ValueError("Invalid model")
        self.manager.handle_model_selection_error(error, "Exception")
        
        # Verify newline was called
        assert self.console.print.call_count >= 1
        
        # Verify error
        self.manager.display.error.assert_called_with(
            "Error during model selection: Invalid model",
            context=(
                "Use -a and -b flags to specify models directly.\n"
                "Example: pidgin run -a claude -b gpt"
            ),
            use_panel=False,
        )