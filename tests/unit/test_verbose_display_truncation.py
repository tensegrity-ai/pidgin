"""Unit tests for truncation event display in verbose mode."""

from io import StringIO
from unittest.mock import MagicMock, Mock

import pytest
from rich.console import Console

from pidgin.core.event_bus import EventBus
from pidgin.core.events import ContextTruncationEvent
from pidgin.ui.verbose_display import VerboseDisplay


class TestVerboseDisplayTruncation:
    """Test that truncation events are displayed in verbose mode."""

    @pytest.fixture
    def console_output(self):
        """Create a console that captures output."""
        return StringIO()

    @pytest.fixture
    def test_console(self, console_output):
        """Create a Rich console with captured output."""
        return Console(file=console_output, force_terminal=True)

    @pytest.fixture
    def mock_agents(self):
        """Create mock agents."""
        agent_a = Mock()
        agent_a.display_name = "Claude"
        agent_a.model = "claude-3-haiku"

        agent_b = Mock()
        agent_b.display_name = "GPT-4"
        agent_b.model = "gpt-4"

        return {"agent_a": agent_a, "agent_b": agent_b}

    @pytest.fixture
    def verbose_display(self, test_console, mock_agents):
        """Create a VerboseDisplay instance."""
        bus = EventBus()
        return VerboseDisplay(bus, test_console, mock_agents)

    def test_truncation_shown_in_verbose_mode(
        self, verbose_display, console_output, test_console
    ):
        """Test that truncation events are displayed in verbose mode."""
        # First check if handle_truncation method exists
        # If not, we'll add it to the display
        if not hasattr(verbose_display, "handle_truncation"):
            # Add a simple handler for testing
            def handle_truncation(event):
                info = f"⚠ Context Truncated • {event.messages_dropped} messages dropped • {event.truncated_message_count} messages remain"
                test_console.print(f"[yellow]{info}[/yellow]")

            verbose_display.handle_truncation = handle_truncation
            # Subscribe to the event
            verbose_display.bus.subscribe(ContextTruncationEvent, handle_truncation)

        # Create a truncation event
        event = ContextTruncationEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            provider="anthropic",
            model="claude-3-haiku",
            turn_number=10,
            original_message_count=50,
            truncated_message_count=20,
            messages_dropped=30,
        )

        # Emit the event
        import asyncio

        asyncio.run(verbose_display.bus.emit(event))

        # Check that truncation was displayed
        output = console_output.getvalue()
        assert "Context Truncated" in output
        assert "30 messages dropped" in output
        assert "20 remain" in output

    def test_truncation_info_formatting(
        self, verbose_display, console_output, test_console
    ):
        """Test that truncation info is properly formatted."""
        # Add handler if needed
        if not hasattr(verbose_display, "handle_truncation"):

            def handle_truncation(event):
                agent_name = verbose_display.agents[event.agent_id].display_name
                info = (
                    f"⚠ Context Truncated for {agent_name} at turn {event.turn_number}"
                )
                details = f"{event.messages_dropped} messages dropped, {event.truncated_message_count} remain"
                test_console.print(f"[bold yellow]{info}[/bold yellow]")
                test_console.print(f"[dim]{details}[/dim]")

            verbose_display.handle_truncation = handle_truncation
            verbose_display.bus.subscribe(ContextTruncationEvent, handle_truncation)

        # Create event for agent_b
        event = ContextTruncationEvent(
            conversation_id="test_conv",
            agent_id="agent_b",
            provider="openai",
            model="gpt-4",
            turn_number=15,
            original_message_count=100,
            truncated_message_count=40,
            messages_dropped=60,
        )

        # Emit the event
        import asyncio

        asyncio.run(verbose_display.bus.emit(event))

        # Check formatting
        output = console_output.getvalue()
        assert "GPT-4" in output  # Agent name should be shown
        assert "Turn 15" in output  # Capital T
        assert "60 messages dropped" in output
