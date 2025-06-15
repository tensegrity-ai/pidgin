"""Tests for the intervention handler and message source functionality."""

import pytest
from datetime import datetime
from pidgin.types import Message
from pidgin.intervention_handler import InterventionHandler
from rich.console import Console


class TestInterventionHandler:
    """Test conductor functionality."""

    def setup_method(self):
        """Set up test conductor."""
        self.console = Console()
        self.conductor = InterventionHandler(self.console, mode="manual")

    def test_conductor_initialization(self):
        """Test conductor initializes correctly."""
        assert self.conductor.console == self.console
        assert self.conductor.intervention_history == []
        assert self.conductor.mode == "manual"
        assert self.conductor.is_paused == True  # Manual mode starts paused

    def test_intervention_summary_empty(self):
        """Test intervention summary when no interventions made."""
        summary = self.conductor.get_intervention_summary()
        assert summary["total_interventions"] == 0
        assert summary["interventions"] == 0
        assert summary["history"] == []

    def test_intervention_history_tracking(self):
        """Test that intervention history is tracked properly."""
        # Simulate intervention
        self.conductor.intervention_history.append(
            {
                "type": "intervention",
                "source": "human",
                "content": "Test intervention",
                "timestamp": datetime.now().isoformat(),
            }
        )

        summary = self.conductor.get_intervention_summary()
        assert summary["total_interventions"] == 1
        assert summary["interventions"] == 1
        assert len(summary["history"]) == 1

    def test_should_intervene_manual_mode(self):
        """Test intervention decision in manual mode."""
        from pidgin.types import ConversationTurn, Message

        # Create a mock turn
        turn = ConversationTurn(
            agent_a_message=Message(
                role="assistant", content="Hello", agent_id="agent_a"
            ),
            agent_b_message=Message(role="assistant", content="Hi", agent_id="agent_b"),
            turn_number=1,
        )

        # Manual mode should always want to intervene
        assert self.conductor.should_intervene_after_turn(turn) == True

    def test_should_intervene_flowing_mode(self):
        """Test intervention decision in flowing mode."""
        from pidgin.types import ConversationTurn, Message

        flowing_conductor = InterventionHandler(self.console, mode="flowing")

        # Create a mock turn
        turn = ConversationTurn(
            agent_a_message=Message(
                role="assistant", content="Hello", agent_id="agent_a"
            ),
            agent_b_message=Message(role="assistant", content="Hi", agent_id="agent_b"),
            turn_number=1,
        )

        # Flowing mode should not intervene unless paused
        assert flowing_conductor.should_intervene_after_turn(turn) == False

        # After pausing, should intervene
        flowing_conductor.pause()
        assert flowing_conductor.should_intervene_after_turn(turn) == True


class TestMessageTypes:
    """Test message type creation with different sources."""

    def test_message_creation_without_source(self):
        """Test creating messages without source field."""
        message = Message(role="assistant", content="Test message", agent_id="agent_a")
        
        # Should work without source field
        assert message.agent_id == "agent_a"
