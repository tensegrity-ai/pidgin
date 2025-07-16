# tests/fixtures/messages.py
"""Common message fixtures for testing."""

from datetime import datetime

import pytest

from pidgin.core.types import Agent, Conversation, ConversationTurn, Message


@pytest.fixture
def simple_message():
    """Simple message fixture."""
    return Message(
        role="user",
        content="Hello, this is a test message",
        agent_id="agent_a",
        timestamp=datetime.now(),
    )


@pytest.fixture
def conversation_messages():
    """List of messages for a conversation."""
    base_time = datetime.now()
    return [
        Message(
            role="user",
            content="Hello! Let's have a conversation.",
            agent_id="agent_a",
            timestamp=base_time,
        ),
        Message(
            role="assistant",
            content="Hi! I'd be happy to chat with you.",
            agent_id="agent_b",
            timestamp=base_time,
        ),
        Message(
            role="user",
            content="What should we talk about?",
            agent_id="agent_a",
            timestamp=base_time,
        ),
        Message(
            role="assistant",
            content="We could discuss any topic you find interesting!",
            agent_id="agent_b",
            timestamp=base_time,
        ),
    ]


@pytest.fixture
def test_agents():
    """Test agent configurations."""
    return [
        Agent(
            id="agent_a",
            model="claude-3-sonnet",
            display_name="Claude",
            temperature=0.7,
        ),
        Agent(id="agent_b", model="gpt-4", display_name="GPT-4", temperature=0.8),
    ]


@pytest.fixture
def test_conversation(test_agents, conversation_messages):
    """Complete test conversation."""
    return Conversation(
        id="test_conv_789",
        agents=test_agents,
        messages=conversation_messages,
        initial_prompt="Let's have a conversation",
    )


@pytest.fixture
def empty_turn():
    """Empty conversation turn."""
    return ConversationTurn(turn_number=1)


@pytest.fixture
def partial_turn(simple_message):
    """Partially complete turn."""
    return ConversationTurn(agent_a_message=simple_message, turn_number=1)


@pytest.fixture
def complete_turn():
    """Complete conversation turn."""
    msg_a = Message(role="user", content="Message from agent A", agent_id="agent_a")
    msg_b = Message(
        role="assistant", content="Response from agent B", agent_id="agent_b"
    )
    return ConversationTurn(agent_a_message=msg_a, agent_b_message=msg_b, turn_number=1)


@pytest.fixture
def turn_with_intervention():
    """Turn with post-turn intervention."""
    msg_a = Message(role="user", content="Message from agent A", agent_id="agent_a")
    msg_b = Message(
        role="assistant", content="Response from agent B", agent_id="agent_b"
    )
    intervention = Message(
        role="user", content="System intervention", agent_id="system"
    )
    return ConversationTurn(
        agent_a_message=msg_a,
        agent_b_message=msg_b,
        post_turn_interventions=[intervention],
        turn_number=2,
    )
