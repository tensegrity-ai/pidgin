# tests/unit/test_types.py
"""Test core type definitions."""

import pytest
from datetime import datetime
from pidgin.core.types import (
    ConversationRole,
    InterventionSource,
    ConversationTurn,
    Message,
    Agent,
    Conversation,
)


class TestConversationRole:
    """Test ConversationRole enum."""

    def test_values(self):
        """Test enum values."""
        assert ConversationRole.AGENT_A.value == "agent_a"
        assert ConversationRole.AGENT_B.value == "agent_b"

    def test_all_roles(self):
        """Test all roles are defined."""
        roles = [role.value for role in ConversationRole]
        assert "agent_a" in roles
        assert "agent_b" in roles
        assert len(roles) == 2


class TestInterventionSource:
    """Test InterventionSource enum."""

    def test_values(self):
        """Test enum values."""
        assert InterventionSource.SYSTEM.value == "system"
        assert InterventionSource.HUMAN.value == "human"
        assert InterventionSource.MEDIATOR.value == "mediator"

    def test_all_sources(self):
        """Test all sources are defined."""
        sources = [source.value for source in InterventionSource]
        assert len(sources) == 3


class TestMessage:
    """Test Message model."""

    def test_basic_creation(self):
        """Test basic message creation."""
        msg = Message(role="user", content="Hello world", agent_id="agent_a")

        assert msg.role == "user"
        assert msg.content == "Hello world"
        assert msg.agent_id == "agent_a"
        assert isinstance(msg.timestamp, datetime)

    def test_custom_timestamp(self):
        """Test message with custom timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        msg = Message(
            role="assistant",
            content="Response",
            agent_id="agent_b",
            timestamp=custom_time,
        )

        assert msg.timestamp == custom_time

    def test_serialization(self):
        """Test message serialization."""
        msg = Message(role="user", content="Test", agent_id="test_agent")

        # Should be serializable
        data = msg.model_dump()
        assert data["role"] == "user"
        assert data["content"] == "Test"
        assert data["agent_id"] == "test_agent"
        assert "timestamp" in data


class TestAgent:
    """Test Agent model."""

    def test_basic_creation(self):
        """Test basic agent creation."""
        agent = Agent(id="agent_a", model="gpt-4")

        assert agent.id == "agent_a"
        assert agent.model == "gpt-4"
        assert agent.display_name is None
        assert agent.temperature is None

    def test_full_creation(self):
        """Test agent with all fields."""
        agent = Agent(
            id="agent_test",
            model="claude-3-sonnet",
            display_name="Test Agent",
            model_shortname="sonnet",
            temperature=0.8,
        )

        assert agent.display_name == "Test Agent"
        assert agent.model_shortname == "sonnet"
        assert agent.temperature == 0.8


class TestConversation:
    """Test Conversation model."""

    def test_basic_creation(self):
        """Test basic conversation creation."""
        agents = [
            Agent(id="agent_a", model="test-model-a"),
            Agent(id="agent_b", model="test-model-b"),
        ]

        conversation = Conversation(agents=agents)

        # Should have auto-generated ID
        assert len(conversation.id) == 8
        assert conversation.agents == agents
        assert conversation.messages == []
        assert isinstance(conversation.started_at, datetime)
        assert conversation.initial_prompt is None

    def test_with_messages(self):
        """Test conversation with messages."""
        agents = [
            Agent(id="agent_a", model="test-model-a"),
            Agent(id="agent_b", model="test-model-b"),
        ]

        messages = [
            Message(role="user", content="Hi", agent_id="agent_a"),
            Message(role="assistant", content="Hello", agent_id="agent_b"),
        ]

        conversation = Conversation(
            agents=agents, messages=messages, initial_prompt="Start conversation"
        )

        assert len(conversation.messages) == 2
        assert conversation.initial_prompt == "Start conversation"


class TestConversationTurn:
    """Test ConversationTurn model."""

    def test_empty_turn(self):
        """Test empty turn."""
        turn = ConversationTurn()

        assert turn.agent_a_message is None
        assert turn.agent_b_message is None
        assert turn.post_turn_interventions == []
        assert turn.turn_number == 0
        assert not turn.complete

    def test_partial_turn(self):
        """Test partially complete turn."""
        msg_a = Message(role="user", content="Hello", agent_id="agent_a")

        turn = ConversationTurn(agent_a_message=msg_a, turn_number=1)

        assert turn.agent_a_message == msg_a
        assert turn.agent_b_message is None
        assert not turn.complete
        assert turn.conversation_messages == [msg_a]
        assert turn.all_messages == [msg_a]

    def test_complete_turn(self):
        """Test complete turn."""
        msg_a = Message(role="user", content="Hello", agent_id="agent_a")
        msg_b = Message(role="assistant", content="Hi", agent_id="agent_b")

        turn = ConversationTurn(
            agent_a_message=msg_a, agent_b_message=msg_b, turn_number=1
        )

        assert turn.complete
        assert turn.conversation_messages == [msg_a, msg_b]
        assert len(turn.all_messages) == 2

    def test_turn_with_interventions(self):
        """Test turn with interventions."""
        msg_a = Message(role="user", content="Hello", agent_id="agent_a")
        msg_b = Message(role="assistant", content="Hi", agent_id="agent_b")
        intervention = Message(role="user", content="System note", agent_id="system")

        turn = ConversationTurn(
            agent_a_message=msg_a,
            agent_b_message=msg_b,
            post_turn_interventions=[intervention],
            turn_number=2,
        )

        assert turn.complete
        assert turn.conversation_messages == [msg_a, msg_b]
        assert turn.all_messages == [msg_a, msg_b, intervention]
        assert len(turn.post_turn_interventions) == 1
