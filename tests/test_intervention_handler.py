"""Tests for the intervention handler and message source functionality."""

import pytest
from datetime import datetime
from pidgin.types import Message, MessageSource
from pidgin.intervention_handler import InterventionHandler
from rich.console import Console


class TestMessageSource:
    """Test message source functionality."""

    def test_message_display_source_agent_a(self):
        """Test display source for Agent A."""
        message = Message(
            role="assistant",
            content="Hello from Agent A",
            agent_id="agent_a",
            source=MessageSource.AGENT_A,
        )
        assert message.display_source == "Agent A"

    def test_message_display_source_agent_b(self):
        """Test display source for Agent B."""
        message = Message(
            role="assistant",
            content="Hello from Agent B",
            agent_id="agent_b",
            source=MessageSource.AGENT_B,
        )
        assert message.display_source == "Agent B"

    def test_message_display_source_system(self):
        """Test display source for System."""
        message = Message(
            role="user",
            content="System message",
            agent_id="system",
            source=MessageSource.SYSTEM,
        )
        assert message.display_source == "System"

    def test_message_display_source_human(self):
        """Test display source for Human."""
        message = Message(
            role="user",
            content="Human intervention",
            agent_id="human",
            source=MessageSource.HUMAN,
        )
        assert message.display_source == "Human"

    def test_message_display_source_mediator(self):
        """Test display source for Mediator."""
        message = Message(
            role="user",
            content="Mediator message",
            agent_id="mediator",
            source=MessageSource.MEDIATOR,
        )
        assert message.display_source == "Mediator"

    def test_message_display_source_fallback(self):
        """Test fallback when source is None."""
        message = Message(role="assistant", content="Test message", agent_id="agent_a")
        assert message.display_source == "Agent A"

    def test_message_source_enum_values(self):
        """Test MessageSource enum values."""
        assert MessageSource.AGENT_A == "agent_a"
        assert MessageSource.AGENT_B == "agent_b"
        assert MessageSource.SYSTEM == "system"
        assert MessageSource.HUMAN == "human"
        assert MessageSource.MEDIATOR == "mediator"


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

    def test_system_message_creation(self):
        """Test creating a system message."""
        message = Message(
            role="user",
            content="You are both AI assistants in an experiment.",
            agent_id="system",
            source=MessageSource.SYSTEM,
        )

        assert message.role == "user"
        assert message.agent_id == "system"
        assert message.source == MessageSource.SYSTEM
        assert message.display_source == "System"

    def test_human_message_creation(self):
        """Test creating a human message."""
        message = Message(
            role="user",
            content="I'd like to intervene in this conversation.",
            agent_id="human",
            source=MessageSource.HUMAN,
        )

        assert message.role == "user"
        assert message.agent_id == "human"
        assert message.source == MessageSource.HUMAN
        assert message.display_source == "Human"

    def test_mediator_message_creation(self):
        """Test creating a mediator message."""
        message = Message(
            role="user",
            content="Let's pause and reflect on this discussion.",
            agent_id="mediator",
            source=MessageSource.MEDIATOR,
        )

        assert message.role == "user"
        assert message.agent_id == "mediator"
        assert message.source == MessageSource.MEDIATOR
        assert message.display_source == "Mediator"

    def test_agent_message_creation(self):
        """Test creating agent messages with proper source."""
        message_a = Message(
            role="assistant",
            content="Hello from Agent A",
            agent_id="agent_a",
            source=MessageSource.AGENT_A,
        )

        message_b = Message(
            role="assistant",
            content="Hello from Agent B",
            agent_id="agent_b",
            source=MessageSource.AGENT_B,
        )

        assert message_a.source == MessageSource.AGENT_A
        assert message_a.display_source == "Agent A"
        assert message_b.source == MessageSource.AGENT_B
        assert message_b.display_source == "Agent B"

    def test_backward_compatibility(self):
        """Test that messages work without explicit source."""
        message = Message(role="assistant", content="Test message", agent_id="agent_a")

        # Should work without source field
        assert message.agent_id == "agent_a"
        assert message.source is None
        assert message.display_source == "Agent A"  # Should fallback to agent_id
