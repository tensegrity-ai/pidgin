"""Test that experiment conversations are excluded from batch database loading."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from pidgin.core.conductor import Conductor
from pidgin.core.types import Conversation
from pidgin.io.output_manager import OutputManager
from tests.builders import make_agent


class TestExperimentExclusion:
    """Test that experiment conversations don't trigger database batch loading."""

    @pytest.mark.asyncio
    async def test_experiment_conversations_not_batch_loaded(self, tmp_path):
        """Test that conversations with IDs starting with conv_experiment_ are not batch loaded."""
        # Create conductor
        output_manager = Mock(spec=OutputManager)
        conductor = Conductor(output_manager=output_manager)
        
        # Create a conversation with experiment ID pattern
        conv_id = "conv_experiment_53ed8319_ea4a402b"
        conversation = Conversation(
            agents=[make_agent("agent_a"), make_agent("agent_b")],
            initial_prompt="Test prompt"
        )
        conversation.id = conv_id
        
        # Mock lifecycle to avoid actual event emission
        conductor.lifecycle = Mock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        
        # Mock the batch load method
        with patch.object(conductor, '_batch_load_chat_to_database') as mock_batch_load:
            # Call finalize conversation
            await conductor._finalize_conversation(
                conversation=conversation,
                conv_id=conv_id,
                conv_dir=tmp_path,
                final_turn=5,
                max_turns=10,
                end_reason="completed"
            )
            
            # Verify batch load was NOT called for experiment conversation
            mock_batch_load.assert_not_called()

    @pytest.mark.asyncio
    async def test_regular_conversations_are_batch_loaded(self, tmp_path):
        """Test that regular conversations (not experiments) ARE batch loaded."""
        # Create conductor
        output_manager = Mock(spec=OutputManager)
        conductor = Conductor(output_manager=output_manager)
        
        # Create a regular conversation
        conv_id = "conv_12345678"
        conversation = Conversation(
            agents=[make_agent("agent_a"), make_agent("agent_b")],
            initial_prompt="Test prompt"
        )
        conversation.id = conv_id
        
        # Mock lifecycle to avoid actual event emission
        conductor.lifecycle = Mock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        
        # Mock the batch load method
        with patch.object(conductor, '_batch_load_chat_to_database') as mock_batch_load:
            mock_batch_load.return_value = asyncio.Future()
            mock_batch_load.return_value.set_result(None)
            
            # Call finalize conversation
            await conductor._finalize_conversation(
                conversation=conversation,
                conv_id=conv_id,
                conv_dir=tmp_path,
                final_turn=5,
                max_turns=10,
                end_reason="completed"
            )
            
            # Verify batch load WAS called for regular conversation
            mock_batch_load.assert_called_once()
            # Check it was called with the correct conv_id
            assert mock_batch_load.call_args[0][0] == conv_id

    @pytest.mark.asyncio
    async def test_old_experiment_pattern_still_excluded(self, tmp_path):
        """Test that old pattern conv_exp_ is still excluded for backward compatibility."""
        # Create conductor
        output_manager = Mock(spec=OutputManager)
        conductor = Conductor(output_manager=output_manager)
        
        # Create a conversation with old experiment pattern
        conv_id = "conv_exp_12345678"
        conversation = Conversation(
            agents=[make_agent("agent_a"), make_agent("agent_b")],
            initial_prompt="Test prompt"
        )
        conversation.id = conv_id
        
        # Mock lifecycle to avoid actual event emission
        conductor.lifecycle = Mock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        
        # Mock the batch load method
        with patch.object(conductor, '_batch_load_chat_to_database') as mock_batch_load:
            # Call finalize conversation
            await conductor._finalize_conversation(
                conversation=conversation,
                conv_id=conv_id,
                conv_dir=tmp_path,
                final_turn=5,
                max_turns=10,
                end_reason="completed"
            )
            
            # Verify batch load was NOT called
            mock_batch_load.assert_not_called()