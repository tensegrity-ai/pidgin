# tests/fixtures/events.py
"""Common event fixtures for testing."""

import pytest
from datetime import datetime
from pidgin.core.events import (
    ConversationStartedEvent,
    TurnStartedEvent,
    TurnCompletedEvent,
    ConversationCompletedEvent,
    AgentResponseEvent,
    MetricsCalculatedEvent,
    ErrorEvent
)


@pytest.fixture
def sample_conversation_started_event():
    """Sample ConversationStartedEvent."""
    return ConversationStartedEvent(
        conversation_id="test_conv_123",
        experiment_id="test_exp_456",
        agent_a_model="claude-3-sonnet",
        agent_b_model="gpt-4",
        initial_prompt="Let's discuss something interesting",
        metadata={"test": True}
    )


@pytest.fixture
def sample_turn_started_event():
    """Sample TurnStartedEvent."""
    return TurnStartedEvent(
        conversation_id="test_conv_123",
        experiment_id="test_exp_456",
        turn_number=1,
        active_agent="agent_a"
    )


@pytest.fixture
def sample_agent_response_event():
    """Sample AgentResponseEvent."""
    return AgentResponseEvent(
        conversation_id="test_conv_123",
        experiment_id="test_exp_456",
        agent_id="agent_a",
        model="claude-3-sonnet",
        message="Hello, this is a test response",
        turn_number=1,
        tokens_used={"prompt": 50, "completion": 15, "total": 65},
        response_time=1.23,
        metadata={"temperature": 0.7}
    )


@pytest.fixture
def sample_turn_completed_event():
    """Sample TurnCompletedEvent."""
    return TurnCompletedEvent(
        conversation_id="test_conv_123",
        experiment_id="test_exp_456",
        turn_number=1,
        messages={
            "agent_a": "Hello from agent A",
            "agent_b": "Hello from agent B"
        },
        turn_duration=3.45,
        metadata={"test": True}
    )


@pytest.fixture
def sample_metrics_calculated_event():
    """Sample MetricsCalculatedEvent."""
    return MetricsCalculatedEvent(
        conversation_id="test_conv_123",
        experiment_id="test_exp_456",
        turn_number=1,
        metrics={
            "agent_a_length": 18,
            "agent_b_length": 18,
            "vocabulary_overlap": 0.5,
            "message_similarity": 0.8
        }
    )


@pytest.fixture
def sample_conversation_completed_event():
    """Sample ConversationCompletedEvent."""
    return ConversationCompletedEvent(
        conversation_id="test_conv_123",
        experiment_id="test_exp_456",
        total_turns=10,
        total_duration=45.67,
        completion_reason="max_turns",
        final_metrics={
            "total_tokens": 1500,
            "average_turn_duration": 4.567
        }
    )


@pytest.fixture
def sample_error_event():
    """Sample ErrorEvent."""
    return ErrorEvent(
        conversation_id="test_conv_123",
        experiment_id="test_exp_456",
        error_type="APIError",
        error_message="Rate limit exceeded",
        context={"provider": "anthropic", "attempt": 3},
        traceback="Traceback details here..."
    )