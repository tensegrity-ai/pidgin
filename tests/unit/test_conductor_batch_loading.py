"""Test that conductor no longer performs batch loading."""

import pytest
from unittest.mock import Mock, AsyncMock

from pidgin.core.conductor import Conductor
from pidgin.io.output_manager import OutputManager


class TestConductorNoBatchLoading:
    """Test that batch loading has been removed."""

    @pytest.fixture
    def conductor(self):
        """Create a Conductor instance."""
        output_manager = Mock(spec=OutputManager)
        conductor = Conductor(output_manager=output_manager)
        return conductor

    def test_no_batch_load_method(self, conductor):
        """Verify _batch_load_chat_to_database method no longer exists."""
        assert not hasattr(conductor, '_batch_load_chat_to_database')

    @pytest.mark.asyncio
    async def test_finalize_does_not_load_database(self, conductor):
        """Test that finalize_conversation doesn't attempt database loading."""
        # Mock necessary attributes
        conductor.lifecycle = Mock()
        conductor.lifecycle.emit_end_event_with_reason = AsyncMock()
        
        # Create a mock conversation
        conversation = Mock()
        conversation.id = "test_conv_123"
        
        # Call finalize - should not raise any errors about missing database methods
        await conductor._finalize_conversation(
            conversation=conversation,
            conv_id="test_conv_123",
            conv_dir=None,
            final_turn=5,
            max_turns=10,
            end_reason="completed"
        )
        
        # Verify lifecycle method was called
        conductor.lifecycle.emit_end_event_with_reason.assert_called_once()