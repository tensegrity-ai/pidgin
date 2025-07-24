"""Test that conductor no longer performs database loading for any conversations."""

import pytest
from unittest.mock import Mock, AsyncMock

from pidgin.core.conductor import Conductor
from pidgin.core.types import Conversation
from pidgin.io.output_manager import OutputManager
from tests.builders import make_agent


class TestNoDatabaseLoading:
    """Test that database loading has been removed entirely."""

    @pytest.mark.asyncio
    async def test_no_database_loading_for_any_conversation(self, tmp_path):
        """Test that no conversations trigger database loading."""
        # Create conductor
        output_manager = Mock(spec=OutputManager)
        conductor = Conductor(output_manager=output_manager)
        
        # Test various conversation ID patterns
        test_ids = [
            "conv_experiment_53ed8319_ea4a402b",  # Experiment
            "conv_exp_test_123",                   # Short experiment
            "conv_chat_456",                       # Regular chat
            "cosmic-prism",                        # Named conversation
        ]
        
        for conv_id in test_ids:
            conversation = Conversation(
                agents=[make_agent("agent_a"), make_agent("agent_b")],
                initial_prompt="Test prompt"
            )
            conversation.id = conv_id
            
            # Mock lifecycle to avoid actual event emission
            conductor.lifecycle = Mock()
            conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
            
            # Verify no batch load method exists
            assert not hasattr(conductor, '_batch_load_chat_to_database')
            
            # Call finalize conversation - should work without database
            await conductor._finalize_conversation(
                conversation=conversation,
                conv_id=conv_id,
                conv_dir=tmp_path,
                final_turn=5,
                max_turns=10,
                end_reason="completed"
            )
            
            # Verify lifecycle method was called
            conductor.lifecycle.emit_end_event_with_reason.assert_called_once()