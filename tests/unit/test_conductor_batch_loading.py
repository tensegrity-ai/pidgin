"""Fixed batch loading tests for conductor."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import sys

import pytest

from pidgin.core.conductor import Conductor
from pidgin.core.types import Conversation
from pidgin.io.output_manager import OutputManager
from tests.builders import make_agent


class MockEventStore:
    """Mock EventStore for testing."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.import_experiment_from_jsonl = Mock(return_value=True)
        self.close = Mock()


def create_mock_event_store_module():
    """Create a mock event_store module."""
    mock_module = MagicMock()
    mock_module.EventStore = MockEventStore
    return mock_module


class TestConductorBatchLoading:
    """Test Conductor batch loading functionality."""

    @pytest.fixture
    def conductor(self):
        """Create a Conductor instance with mocked dependencies."""
        output_manager = Mock(spec=OutputManager)
        conductor = Conductor(output_manager=output_manager)

        # Mock all the lifecycle methods
        conductor.lifecycle = Mock()
        conductor.lifecycle.initialize_event_system = AsyncMock()
        conductor.lifecycle.set_providers = Mock()
        conductor.lifecycle.create_conversation = Mock()
        conductor.lifecycle.add_initial_messages = AsyncMock()
        conductor.lifecycle.emit_start_events = AsyncMock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        conductor.lifecycle.save_transcripts = AsyncMock()
        conductor.lifecycle.cleanup = AsyncMock()

        # Mock name coordinator
        conductor.name_coordinator = Mock()
        conductor.name_coordinator.initialize_name_mode = Mock()
        conductor.name_coordinator.assign_display_names = Mock()

        # Mock turn executor
        conductor.turn_executor = Mock()
        conductor.turn_executor.set_custom_awareness = Mock()
        conductor.turn_executor.run_single_turn = AsyncMock()
        conductor.turn_executor.stop_reason = None

        # Mock interrupt handler
        conductor.interrupt_handler = Mock()
        conductor.interrupt_handler.setup_interrupt_handler = Mock()
        conductor.interrupt_handler.restore_interrupt_handler = Mock()
        conductor.interrupt_handler.interrupt_requested = False
        conductor.interrupt_handler.current_turn = 0

        return conductor

    @pytest.mark.asyncio
    async def test_batch_load_single_chat(self, conductor, tmp_path):
        """Test batch loading for single chat sessions."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Set up conversation directory
        conv_dir = tmp_path / "test_conv_123"
        conv_dir.mkdir()
        conductor.output_manager.create_conversation_dir.return_value = (
            "test_conv_123",
            conv_dir,
        )

        # Create JSONL file
        jsonl_file = conv_dir / "test_conv_123_events.jsonl"
        jsonl_file.write_text('{"event": "test"}\n')

        test_conversation = Conversation(
            id="test_conv_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Mock turn execution to stop immediately
        conductor.turn_executor.run_single_turn.return_value = None

        # Mock the database module
        mock_db_module = create_mock_event_store_module()
        
        with patch.dict('sys.modules', {'pidgin.database': mock_db_module, 'pidgin.database.event_store': mock_db_module}):
            with patch("pidgin.io.paths.get_chats_database_path", return_value="/tmp/chats.db"):
                # Run conversation
                result = await conductor.run_conversation(
                    agent_a=agent_a,
                    agent_b=agent_b,
                    initial_prompt="Hello",
                    max_turns=1,
                )

                # Verify marker file was created (indicates successful batch load)
                marker_file = conv_dir / ".loaded_to_db"
                assert marker_file.exists()

    @pytest.mark.asyncio
    async def test_batch_load_skipped_for_experiments(self, conductor, tmp_path):
        """Test that batch loading is skipped for experiment conversations."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Set up experiment conversation directory
        conv_dir = tmp_path / "conv_exp_test_123"
        conv_dir.mkdir()
        conductor.output_manager.create_conversation_dir.return_value = (
            "conv_exp_test_123",
            conv_dir,
        )

        test_conversation = Conversation(
            id="conv_exp_test_123", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Mock turn execution to stop immediately
        conductor.turn_executor.run_single_turn.return_value = None

        # Track if EventStore was imported
        import_called = False
        import builtins
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            nonlocal import_called
            if name == 'pidgin.database.event_store' or 'event_store' in name:
                import_called = True
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            with patch("pidgin.io.paths.get_chats_database_path", return_value="/tmp/chats.db"):
                # Run conversation
                result = await conductor.run_conversation(
                    agent_a=agent_a,
                    agent_b=agent_b,
                    initial_prompt="Hello",
                    max_turns=1,
                    conversation_id="conv_exp_test_123",
                )

                # Verify EventStore was NOT imported for experiment
                assert not import_called

    @pytest.mark.asyncio
    async def test_batch_load_experiment_pattern(self, conductor, tmp_path):
        """Test that batch loading is skipped for conv_experiment_ pattern."""
        agent_a = make_agent("agent_a", "gpt-4")
        agent_b = make_agent("agent_b", "claude-3")

        # Set up experiment conversation directory with new pattern
        conv_dir = tmp_path / "conv_experiment_53ed8319_ea4a402b"
        conv_dir.mkdir()
        conductor.output_manager.create_conversation_dir.return_value = (
            "conv_experiment_53ed8319_ea4a402b",
            conv_dir,
        )

        test_conversation = Conversation(
            id="conv_experiment_53ed8319_ea4a402b", agents=[agent_a, agent_b], messages=[]
        )
        conductor.lifecycle.create_conversation.return_value = test_conversation

        # Mock turn execution to stop immediately
        conductor.turn_executor.run_single_turn.return_value = None

        # Track if EventStore was imported
        import_called = False
        import builtins
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            nonlocal import_called
            if name == 'pidgin.database.event_store' or 'event_store' in name:
                import_called = True
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            with patch("pidgin.io.paths.get_chats_database_path", return_value="/tmp/chats.db"):
                # Run conversation
                result = await conductor.run_conversation(
                    agent_a=agent_a,
                    agent_b=agent_b,
                    initial_prompt="Hello",
                    max_turns=1,
                    conversation_id="conv_experiment_53ed8319_ea4a402b",
                )

                # Verify EventStore was NOT imported for experiment
                assert not import_called