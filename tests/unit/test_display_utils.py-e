"""Tests for DisplayUtils."""

from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console
from rich.text import Text

from pidgin.ui.display_utils import NORD_COLORS, DisplayUtils, default_display


class TestDisplayUtils:
    """Test DisplayUtils class."""

    def test_init_with_console(self):
        """Test DisplayUtils initialization with provided console."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        assert display.console is console

    def test_init_without_console(self):
        """Test DisplayUtils initialization without console."""
        display = DisplayUtils()

        assert display.console is not None
        assert isinstance(display.console, Console)

    def test_init_with_none_console(self):
        """Test DisplayUtils initialization with None console."""
        display = DisplayUtils(None)

        assert display.console is not None
        assert isinstance(display.console, Console)


class TestCalculatePanelWidth:
    """Test _calculate_panel_width functionality."""

    def test_calculate_panel_width_string_content(self):
        """Test panel width calculation with string content."""
        display = DisplayUtils()

        # Short content
        width = display._calculate_panel_width(
            "Hello", "Test", min_width=30, max_width=60
        )
        assert width == 30  # Should use min_width

        # Long content
        long_content = "This is a very long line that should determine the width"
        width = display._calculate_panel_width(
            long_content, "Test", min_width=30, max_width=60
        )
        assert width == 60  # Should use max_width

        # Medium content
        medium_content = "Medium length content"
        width = display._calculate_panel_width(
            medium_content, "Test", min_width=20, max_width=80
        )
        expected = len(medium_content) + 6  # content + borders/padding
        assert width == expected

    def test_calculate_panel_width_text_object(self):
        """Test panel width calculation with Text object."""
        display = DisplayUtils()

        text = Text("Hello world")
        width = display._calculate_panel_width(text, "Test", min_width=30, max_width=60)
        assert width == 30  # Should use min_width

    def test_calculate_panel_width_multiline_content(self):
        """Test panel width calculation with multiline content."""
        display = DisplayUtils()

        multiline = (
            "Short line\nThis is a much longer line that should determine width\nShort"
        )
        width = display._calculate_panel_width(
            multiline, "Test", min_width=30, max_width=80
        )
        expected = len("This is a much longer line that should determine width") + 6
        assert width == expected

    def test_calculate_panel_width_title_consideration(self):
        """Test that title length is considered in width calculation."""
        display = DisplayUtils()

        # Title longer than content
        content = "Short"
        long_title = "This is a very long title"
        width = display._calculate_panel_width(
            content, long_title, min_width=20, max_width=80
        )
        expected = len(long_title) + 4 + 6  # title + padding + borders
        assert width == expected

    def test_calculate_panel_width_constraints(self):
        """Test that width constraints are respected."""
        display = DisplayUtils()

        # Test min_width constraint
        width = display._calculate_panel_width("Hi", "", min_width=50, max_width=80)
        assert width == 50

        # Test max_width constraint
        very_long_content = "x" * 100
        width = display._calculate_panel_width(
            very_long_content, "", min_width=20, max_width=50
        )
        assert width == 50


class TestErrorMethod:
    """Test error method functionality."""

    def test_error_with_panel(self):
        """Test error method with panel display."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.error("Test error message")

        # Should print blank line, panel, and blank line
        assert console.print.call_count == 3

        # Check the panel call
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]
        assert hasattr(panel, "renderable")  # Should be a Panel

    def test_error_with_context(self):
        """Test error method with context."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.error("Test error", context="Additional context")

        # Should still print 3 times (blank, panel, blank)
        assert console.print.call_count == 3

        # Panel should contain context
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]
        # Content should include context
        assert "Additional context" in str(panel.renderable)

    def test_error_with_custom_title(self):
        """Test error method with custom title."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.error("Test error", title="Custom Error")

        assert console.print.call_count == 3

        # Panel should have custom title
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]
        assert "Custom Error" in str(panel.title)

    def test_error_without_panel(self):
        """Test error method without panel."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.error("Test error", use_panel=False)

        # Should print once for the error message
        assert console.print.call_count == 1

        # Should contain [FAIL] and the message
        call_args = console.print.call_args_list[0]
        output = call_args[0][0]
        assert "[FAIL]" in output
        assert "Test error" in output

    def test_error_without_panel_with_context(self):
        """Test error method without panel with context."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.error("Test error", context="Context info", use_panel=False)

        # Should print twice (error + context)
        assert console.print.call_count == 2

        # First call should be error
        error_call = console.print.call_args_list[0]
        assert "[FAIL]" in error_call[0][0]

        # Second call should be context
        context_call = console.print.call_args_list[1]
        assert "Context info" in context_call[0][0]


class TestWarningMethod:
    """Test warning method functionality."""

    def test_warning_with_panel(self):
        """Test warning method with panel display."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.warning("Test warning message")

        # Should print blank line, panel, and blank line
        assert console.print.call_count == 3

        # Check the panel call
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]
        assert hasattr(panel, "renderable")  # Should be a Panel

    def test_warning_with_context(self):
        """Test warning method with context."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.warning("Test warning", context="Additional context")

        assert console.print.call_count == 3

        # Panel should contain context
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]
        assert "Additional context" in str(panel.renderable)

    def test_warning_without_panel(self):
        """Test warning method without panel."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.warning("Test warning", use_panel=False)

        # Should print once for the warning message
        assert console.print.call_count == 1

        # Should contain warning symbol and message
        call_args = console.print.call_args_list[0]
        output = call_args[0][0]
        assert "⚠" in output
        assert "Test warning" in output

    def test_warning_without_panel_with_context(self):
        """Test warning method without panel with context."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.warning("Test warning", context="Context info", use_panel=False)

        # Should print twice (warning + context)
        assert console.print.call_count == 2

        # First call should be warning
        warning_call = console.print.call_args_list[0]
        assert "⚠" in warning_call[0][0]

        # Second call should be context
        context_call = console.print.call_args_list[1]
        assert "Context info" in context_call[0][0]


class TestInfoMethod:
    """Test info method functionality."""

    def test_info_with_panel(self):
        """Test info method with panel display."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.info("Test info message")

        # Should print blank line, panel, and blank line
        assert console.print.call_count == 3

        # Check the panel call
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]
        assert hasattr(panel, "renderable")  # Should be a Panel

    def test_info_with_custom_title(self):
        """Test info method with custom title."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.info("Test info", title="Custom Info")

        assert console.print.call_count == 3

        # Panel should have custom title
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]
        assert "Custom Info" in str(panel.title)

    def test_info_without_panel(self):
        """Test info method without panel."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.info("Test info", use_panel=False)

        # Should print once for the info message
        assert console.print.call_count == 1

        # Should contain info symbol and message
        call_args = console.print.call_args_list[0]
        output = call_args[0][0]
        assert "◆" in output
        assert "Test info" in output


class TestSuccessMethod:
    """Test success method functionality."""

    def test_success_without_panel(self):
        """Test success method without panel (default)."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.success("Test success message")

        # Should print once for the success message
        assert console.print.call_count == 1

        # Should contain [OK] and message
        call_args = console.print.call_args_list[0]
        output = call_args[0][0]
        assert "[OK]" in output
        assert "Test success message" in output

    def test_success_with_panel(self):
        """Test success method with panel."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.success("Test success message", use_panel=True)

        # Should print blank line, panel, and blank line
        assert console.print.call_count == 3

        # Check the panel call
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]
        assert hasattr(panel, "renderable")  # Should be a Panel


class TestApiErrorMethod:
    """Test api_error method functionality."""

    def test_api_error_regular(self):
        """Test api_error method with regular error."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.api_error("Agent A", "OpenAI", "Connection timeout", retryable=True)

        # Should print blank line, panel, and blank line
        assert console.print.call_count == 3

        # Check the panel call
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]

        # Should contain agent, provider, error
        panel_str = str(panel.renderable)
        assert "Agent A" in panel_str
        assert "OpenAI" in panel_str
        assert "Connection timeout" in panel_str
        assert "Retrying automatically" in panel_str

    def test_api_error_not_retryable(self):
        """Test api_error method with non-retryable error."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.api_error("Agent B", "Anthropic", "Invalid API key", retryable=False)

        assert console.print.call_count == 3

        # Check the panel call
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]

        # Should contain non-retryable message
        panel_str = str(panel.renderable)
        assert "Cannot retry automatically" in panel_str

    def test_api_error_billing_with_url(self):
        """Test api_error method with billing error and URL."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.api_error(
            "Agent A",
            "OpenAI",
            "Insufficient quota",
            billing_url="https://platform.openai.com/billing",
        )

        assert console.print.call_count == 3

        # Check the panel call
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]

        # Should contain billing URL
        panel_str = str(panel.renderable)
        panel_title = str(panel.title)
        assert "https://platform.openai.com/billing" in panel_str
        assert "Billing Issue" in panel_title

    def test_api_error_billing_without_url(self):
        """Test api_error method with billing error but no URL."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.api_error("Agent A", "OpenAI", "Credit balance too low")

        assert console.print.call_count == 3

        # Should use regular error format since no billing URL provided
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]
        panel_str = str(panel.renderable)
        panel_title = str(panel.title)
        assert "API Error" in panel_title
        assert "Credit balance too low" in panel_str

    def test_api_error_billing_detection(self):
        """Test billing error detection with various keywords."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        billing_keywords = ["credit", "billing", "payment", "quota", "insufficient"]

        for keyword in billing_keywords:
            console.reset_mock()
            display.api_error(
                "Agent",
                "Provider",
                f"Error with {keyword}",
                billing_url="https://example.com",
            )

            panel_call = console.print.call_args_list[1]
            panel = panel_call[0][0]
            panel_title = str(panel.title)
            assert "Billing Issue" in panel_title


class TestUtilityMethods:
    """Test utility methods."""

    def test_dim_method(self):
        """Test dim method."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.dim("Dimmed message")

        assert console.print.call_count == 1

        # Should use nord3 color
        call_args = console.print.call_args_list[0]
        output = call_args[0][0]
        assert NORD_COLORS["nord3"] in output
        assert "Dimmed message" in output

    def test_status_method_default(self):
        """Test status method with default style."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.status("Status message")

        assert console.print.call_count == 1

        # Should use default nord8 color and arrow
        call_args = console.print.call_args_list[0]
        output = call_args[0][0]
        assert NORD_COLORS["nord8"] in output
        assert "→" in output
        assert "Status message" in output

    def test_status_method_custom_style(self):
        """Test status method with custom style."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.status("Status message", style="nord14")

        assert console.print.call_count == 1

        # Should use nord14 color
        call_args = console.print.call_args_list[0]
        output = call_args[0][0]
        assert NORD_COLORS["nord14"] in output

    def test_status_method_invalid_style(self):
        """Test status method with invalid style."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.status("Status message", style="invalid")

        assert console.print.call_count == 1

        # Should fallback to default nord8
        call_args = console.print.call_args_list[0]
        output = call_args[0][0]
        assert NORD_COLORS["nord8"] in output

    def test_note_method(self):
        """Test note method (alias for dim)."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.note("Note message")

        assert console.print.call_count == 1

        # Should use nord3 color like dim
        call_args = console.print.call_args_list[0]
        output = call_args[0][0]
        assert NORD_COLORS["nord3"] in output
        assert "Note message" in output


class TestExperimentComplete:
    """Test experiment_complete method."""

    def test_experiment_complete_success(self):
        """Test experiment_complete with successful experiment."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.experiment_complete(
            name="Test Experiment",
            experiment_id="exp_123",
            completed=5,
            failed=0,
            total=5,
            duration_seconds=120.5,
            status="completed",
        )

        # Should print blank line and panel
        assert console.print.call_count == 2

        # Check the panel call
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]

        panel_str = str(panel.renderable)
        assert "Test Experiment" in panel_str
        assert "exp_123" in panel_str
        assert "5/5 completed" in panel_str
        assert "2m 0s" in panel_str  # Duration formatting

    def test_experiment_complete_with_failures(self):
        """Test experiment_complete with failed conversations."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.experiment_complete(
            name="Test Experiment",
            experiment_id="exp_123",
            completed=3,
            failed=2,
            total=5,
            duration_seconds=60.0,
            status="completed_with_failures",
        )

        assert console.print.call_count == 2

        # Check the panel call
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]

        panel_str = str(panel.renderable)
        assert "3/5 completed, 2 failed" in panel_str
        assert "1m 0s" in panel_str

    def test_experiment_complete_interrupted(self):
        """Test experiment_complete with interrupted experiment."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.experiment_complete(
            name="Test Experiment",
            experiment_id="exp_123",
            completed=2,
            failed=1,
            total=5,
            duration_seconds=30.5,
            status="interrupted",
        )

        assert console.print.call_count == 2

        # Check the panel call
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]

        panel_str = str(panel.renderable)
        panel_title = str(panel.title)
        assert "Interrupted" in panel_title
        assert "30.5s" in panel_str  # Short duration formatting

    def test_experiment_complete_with_directory(self):
        """Test experiment_complete with experiment directory."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.experiment_complete(
            name="Test Experiment",
            experiment_id="exp_123",
            completed=5,
            failed=0,
            total=5,
            duration_seconds=3665.0,  # > 1 hour
            status="completed",
            experiment_dir="/path/to/experiment",
        )

        assert console.print.call_count == 2

        # Check the panel call
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]

        panel_str = str(panel.renderable)
        assert "/path/to/experiment" in panel_str
        assert "1h 1m" in panel_str  # Hour formatting

    def test_experiment_complete_duration_formats(self):
        """Test various duration formats."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        # Test seconds
        display.experiment_complete("Test", "exp_1", 1, 0, 1, 45.7, "completed")
        panel_str = str(console.print.call_args_list[1][0][0].renderable)
        assert "45.7s" in panel_str

        console.reset_mock()

        # Test minutes
        display.experiment_complete("Test", "exp_2", 1, 0, 1, 150.0, "completed")
        panel_str = str(console.print.call_args_list[1][0][0].renderable)
        assert "2m 30s" in panel_str

        console.reset_mock()

        # Test hours
        display.experiment_complete("Test", "exp_3", 1, 0, 1, 7320.0, "completed")
        panel_str = str(console.print.call_args_list[1][0][0].renderable)
        assert "2h 2m" in panel_str


class TestApiKeyError:
    """Test api_key_error method."""

    def test_api_key_error_basic(self):
        """Test basic api_key_error functionality."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.api_key_error("API key is required")

        # Should print blank line, panel, and blank line
        assert console.print.call_count == 3

        # Check the panel call
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]

        panel_str = str(panel.renderable)
        panel_title = str(panel.title)
        assert "API Key Missing" in panel_title
        assert "Configuration Required" in panel_str

    def test_api_key_error_with_provider(self):
        """Test api_key_error with provider context."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        display.api_key_error("OpenAI API key missing", provider="OpenAI")

        assert console.print.call_count == 3

        # Provider doesn't directly appear in output but method accepts it
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]
        panel_str = str(panel.renderable)
        assert "OpenAI API key missing" in panel_str

    def test_api_key_error_multiline_message(self):
        """Test api_key_error with multiline message."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        message = """• Missing API key
export OPENAI_API_KEY=your_key_here
Visit https://platform.openai.com for more info"""

        display.api_key_error(message)

        assert console.print.call_count == 3

        # Check that different line types are handled
        panel_call = console.print.call_args_list[1]
        panel = panel_call[0][0]
        panel_str = str(panel.renderable)
        assert "Missing API key" in panel_str
        assert "export OPENAI_API_KEY" in panel_str
        assert "https://platform.openai.com" in panel_str


class TestDefaultDisplay:
    """Test default display instance and convenience functions."""

    def test_default_display_instance(self):
        """Test that default_display is properly initialized."""
        assert default_display is not None
        assert isinstance(default_display, DisplayUtils)
        assert default_display.console is not None

    def test_convenience_functions_exist(self):
        """Test that convenience functions are properly exported."""
        from pidgin.ui.display_utils import (
            api_error,
            api_key_error,
            dim,
            error,
            info,
            note,
            status,
            success,
            warning,
        )

        # All should be callable
        assert callable(error)
        assert callable(warning)
        assert callable(info)
        assert callable(success)
        assert callable(api_error)
        assert callable(api_key_error)
        assert callable(dim)
        assert callable(status)
        assert callable(note)

    def test_convenience_functions_work(self):
        """Test that convenience functions actually work by calling them."""
        # Test that convenience functions actually call the underlying methods
        from pidgin.ui.display_utils import default_display, error, info

        # Use a mock console to verify the calls work
        console = MagicMock(spec=Console)
        old_console = default_display.console
        default_display.console = console

        try:
            error("Test error")
            info("Test info")
            # Just verify that the console was called (functions work)
            assert console.print.call_count > 0
        finally:
            # Restore original console
            default_display.console = old_console


class TestNordColors:
    """Test NORD_COLORS constant."""

    def test_nord_colors_exist(self):
        """Test that NORD_COLORS contains expected colors."""
        expected_colors = [
            "nord0",
            "nord3",
            "nord4",
            "nord7",
            "nord8",
            "nord11",
            "nord12",
            "nord13",
            "nord14",
            "nord15",
        ]

        for color in expected_colors:
            assert color in NORD_COLORS
            assert NORD_COLORS[color].startswith("#")
            assert len(NORD_COLORS[color]) == 7  # Hex color format

    def test_nord_colors_are_valid_hex(self):
        """Test that NORD_COLORS are valid hex colors."""
        import re

        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")

        for color_name, color_value in NORD_COLORS.items():
            assert hex_pattern.match(
                color_value
            ), f"{color_name} has invalid hex value: {color_value}"


class TestIntegrationScenarios:
    """Test integration scenarios."""

    def test_multiple_message_types(self):
        """Test displaying multiple message types in sequence."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        # Display various message types
        display.info("Starting process")
        display.warning("Potential issue detected")
        display.error("Critical error occurred")
        display.success("Process completed")

        # Should have made multiple print calls
        assert (
            console.print.call_count > 4
        )  # Each message type calls print multiple times

        # Reset and test plain text mode
        console.reset_mock()
        display.info("Info", use_panel=False)
        display.warning("Warning", use_panel=False)
        display.error("Error", use_panel=False)
        display.success("Success", use_panel=False)

        # Should have made 4 print calls (one for each message)
        assert console.print.call_count == 4

    def test_panel_width_consistency(self):
        """Test that panel width calculation is consistent."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        # Test with various content lengths
        short_msg = "Short"
        medium_msg = "This is a medium length message"
        long_msg = "This is a very long message that should trigger different width calculations"

        display.info(short_msg)
        display.warning(medium_msg)
        display.error(long_msg)

        # All should have used panels
        assert (
            console.print.call_count == 9
        )  # 3 messages × 3 calls each (blank, panel, blank)

    def test_error_handling_edge_cases(self):
        """Test error handling with edge cases."""
        console = MagicMock(spec=Console)
        display = DisplayUtils(console)

        # Test with empty strings
        display.error("")
        display.warning("")
        display.info("")

        # Should still work
        assert console.print.call_count == 9

        # Test with None values (should not crash)
        try:
            display.error(None)
        except (TypeError, AttributeError):
            # Expected to fail with None
            pass
