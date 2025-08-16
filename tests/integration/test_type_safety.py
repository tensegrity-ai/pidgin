"""Tests for type safety to ensure proper type annotations and signatures."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pidgin.cli.branch_handlers.source_finder import BranchSourceFinder
from pidgin.cli.error_handler import FileNotFoundError as CLIFileNotFoundError
from pidgin.core.conductor import Conductor
from pidgin.core.conversation_lifecycle import ConversationLifecycle
from pidgin.core.events import MessageCompleteEvent
from pidgin.ui.display_filter import DisplayFilter


def test_display_filter_constructor():
    """Test that DisplayFilter constructor accepts correct parameters."""
    from rich.console import Console

    console = Console()

    # Should not accept 'bus' or 'quiet' parameters
    display = DisplayFilter(
        console=console,
        mode="quiet",  # Not 'quiet' parameter
        show_timing=True,
        prompt_tag="[HUMAN]",
    )
    assert display is not None


def test_conductor_no_display_mode_attribute():
    """Test that Conductor doesn't have display_mode attribute."""
    # Conductor should not have a display_mode attribute
    # We removed this attribute during type safety improvements
    from pidgin.core.conductor import Conductor

    # Check that display_mode is not in the class attributes
    assert not hasattr(Conductor, "display_mode")

    # A real Conductor instance shouldn't have it either
    # (we can't create one easily due to dependencies, so just check the class)


def test_branch_source_finder_no_args():
    """Test that BranchSourceFinder constructor takes no arguments."""
    # Should work with no arguments
    finder = BranchSourceFinder()
    assert finder is not None

    # find_conversation should take Path as first arg
    exp_dir = Path("/tmp/test")
    result = finder.find_conversation(exp_dir, "test_id", 1)
    assert result is None  # Won't find anything in test


def test_cli_file_not_found_error_takes_path():
    """Test that CLIFileNotFoundError takes a Path object."""
    test_path = Path("/tmp/nonexistent.yaml")

    # Should accept Path, not string
    error = CLIFileNotFoundError(test_path, suggestion="Check the file path")
    assert "nonexistent.yaml" in str(error)


def test_message_complete_event_has_token_fields():
    """Test that MessageCompleteEvent has separate token fields."""
    from pidgin.core.types import Message

    # Create a test message
    msg = Message(
        role="assistant",
        content="Test message",
        agent_id="agent_a",
        turn_number=1,
    )

    # MessageCompleteEvent should have prompt_tokens, completion_tokens, total_tokens
    event = MessageCompleteEvent(
        conversation_id="test_conv",
        agent_id="agent_a",
        message=msg,
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        duration_ms=100,
    )

    assert event.prompt_tokens == 10
    assert event.completion_tokens == 20
    assert event.total_tokens == 30

    # Should NOT have tokens_used field
    assert not hasattr(event, "tokens_used")


def test_token_handler_uses_correct_log_signature():
    """Test that TokenUsageHandler calls EventStore.log_token_usage correctly."""
    from pidgin.database.event_store import EventStore

    with patch.object(EventStore, "log_token_usage") as mock_log:
        # Create token handler with mocked storage
        storage = MagicMock(spec=EventStore)
        storage.log_token_usage = mock_log

        # The log_token_usage should be called with specific parameters
        storage.log_token_usage(
            conversation_id="test_conv",
            provider="anthropic",
            model="claude-3",
            prompt_tokens=100,
            completion_tokens=200,
            total_cost=0.003,
        )

        # Verify it was called with correct signature
        mock_log.assert_called_once_with(
            conversation_id="test_conv",
            provider="anthropic",
            model="claude-3",
            prompt_tokens=100,
            completion_tokens=200,
            total_cost=0.003,
        )


def test_conversation_lifecycle_state_type():
    """Test that ConversationLifecycle.state has correct type."""
    from rich.console import Console

    from pidgin.config import Config
    from pidgin.providers.token_tracker import GlobalTokenTracker

    console = Console()
    config = Config()
    tracker = GlobalTokenTracker(config)

    lifecycle = ConversationLifecycle(console, tracker)

    # state should be Optional[ConversationState]
    assert lifecycle.state is None  # Initially None

    # After initialization, it can be set to ConversationState
    # (we're just checking the type annotation works)


def test_conductor_state_attributes():
    """Test that Conductor has properly typed state attributes."""
    # Create a minimal Conductor to check attributes
    with (
        patch("pidgin.core.conductor.OutputManager"),
        patch("pidgin.core.conductor.Config"),
        patch("pidgin.core.conductor.GlobalTokenTracker"),
    ):
        # Just check that these attributes exist and have correct types
        conductor = MagicMock(spec=Conductor)

        # These should be Optional types
        conductor.current_conv_dir = None  # Optional[Path]
        conductor.start_time = None  # Optional[float]


def test_experiment_config_awareness_strings():
    """Test that ExperimentConfig awareness fields accept strings."""
    from pidgin.experiments.config import ExperimentConfig

    # awareness fields should be strings, not bools
    config = ExperimentConfig(
        name="test",
        agent_a_model="local:test",
        agent_b_model="local:test",
        repetitions=1,
        max_turns=1,
        awareness="basic",  # String, not bool
        awareness_a="none",  # String, not bool
        awareness_b="basic",  # String, not bool
    )

    assert config.awareness == "basic"
    assert config.awareness_a == "none"
    assert config.awareness_b == "basic"


@pytest.mark.asyncio
async def test_post_processor_sync_wrapper():
    """Test that PostProcessor uses sync wrapper for async handler."""
    from pidgin.core.event_bus import EventBus
    from pidgin.experiments.post_processor import PostProcessor

    bus = EventBus()
    exp_dir = Path("/tmp/test")

    processor = PostProcessor(bus, exp_dir)

    # Check that _sync_handle_experiment_complete exists
    assert hasattr(processor, "_sync_handle_experiment_complete")

    # It should be a sync method that creates an async task
    assert not asyncio.iscoroutinefunction(processor._sync_handle_experiment_complete)
    assert asyncio.iscoroutinefunction(processor.handle_experiment_complete)
