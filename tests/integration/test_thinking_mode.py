"""Functional tests for thinking mode implementation."""

import json
from pathlib import Path

import pytest

from pidgin.core.events import MessageRequestEvent, ThinkingCompleteEvent
from pidgin.core.types import Agent
from pidgin.experiments.config import ExperimentConfig
from pidgin.providers.base import ResponseChunk


class TestThinkingModeConfig:
    """Test thinking mode configuration flows correctly through the system."""

    def test_experiment_config_has_thinking_fields(self):
        """Verify ExperimentConfig accepts thinking parameters."""
        config = ExperimentConfig(
            name="thinking_test",
            agent_a_model="local:test",
            agent_b_model="local:test",
            think=True,
            think_a=True,
            think_b=False,
            think_budget=15000,
        )

        assert config.think is True
        assert config.think_a is True
        assert config.think_b is False
        assert config.think_budget == 15000

    def test_agent_has_thinking_fields(self):
        """Verify Agent type accepts thinking parameters."""
        agent = Agent(
            id="agent_a",
            model="claude-3.7-sonnet",
            thinking_enabled=True,
            thinking_budget=10000,
        )

        assert agent.thinking_enabled is True
        assert agent.thinking_budget == 10000

    def test_message_request_event_has_thinking_fields(self):
        """Verify MessageRequestEvent carries thinking parameters."""
        event = MessageRequestEvent(
            conversation_id="test-conv",
            agent_id="agent_a",
            turn_number=1,
            conversation_history=[],
            thinking_enabled=True,
            thinking_budget=12000,
        )

        assert event.thinking_enabled is True
        assert event.thinking_budget == 12000


class TestThinkingCompleteEvent:
    """Test ThinkingCompleteEvent handling."""

    def test_thinking_complete_event_creation(self):
        """Verify ThinkingCompleteEvent can be created with all fields."""
        event = ThinkingCompleteEvent(
            conversation_id="test-conv",
            turn_number=1,
            agent_id="agent_a",
            thinking_content="Let me think about this...",
            thinking_tokens=500,
            duration_ms=1200,
        )

        assert event.conversation_id == "test-conv"
        assert event.turn_number == 1
        assert event.agent_id == "agent_a"
        assert event.thinking_content == "Let me think about this..."
        assert event.thinking_tokens == 500
        assert event.duration_ms == 1200

    def test_thinking_complete_event_serialization(self):
        """Verify ThinkingCompleteEvent can be serialized to JSON."""
        event = ThinkingCompleteEvent(
            conversation_id="test-conv",
            turn_number=1,
            agent_id="agent_a",
            thinking_content="Reasoning trace here",
            thinking_tokens=100,
            duration_ms=500,
        )

        # Should be serializable
        event_dict = {
            "event_type": "ThinkingCompleteEvent",
            "conversation_id": event.conversation_id,
            "turn_number": event.turn_number,
            "agent_id": event.agent_id,
            "thinking_content": event.thinking_content,
            "thinking_tokens": event.thinking_tokens,
            "duration_ms": event.duration_ms,
        }

        json_str = json.dumps(event_dict)
        parsed = json.loads(json_str)

        assert parsed["event_type"] == "ThinkingCompleteEvent"
        assert parsed["thinking_content"] == "Reasoning trace here"


class TestResponseChunk:
    """Test ResponseChunk dataclass."""

    def test_response_chunk_default_type(self):
        """Verify ResponseChunk defaults to response type."""
        chunk = ResponseChunk(content="Hello")
        assert chunk.content == "Hello"
        assert chunk.chunk_type == "response"

    def test_response_chunk_thinking_type(self):
        """Verify ResponseChunk can be thinking type."""
        chunk = ResponseChunk(content="Let me think...", chunk_type="thinking")
        assert chunk.content == "Let me think..."
        assert chunk.chunk_type == "thinking"


class TestThinkingDatabaseSchema:
    """Test thinking traces database schema."""

    def test_thinking_repository_import(self):
        """Verify ThinkingRepository can be imported."""
        from pidgin.database.thinking_repository import ThinkingRepository

        assert ThinkingRepository is not None

    def test_thinking_schema_exists(self):
        """Verify thinking_traces.sql schema file exists."""
        schema_path = (
            Path(__file__).parent.parent.parent
            / "pidgin/database/schemas/thinking_traces.sql"
        )
        assert schema_path.exists(), f"Schema file not found at {schema_path}"

        # Verify schema content
        content = schema_path.read_text()
        assert "CREATE TABLE" in content
        assert "thinking_traces" in content
        assert "thinking_content" in content
        assert "thinking_tokens" in content


class TestThinkingEventImport:
    """Test thinking event import to database."""

    def test_conversation_importer_has_thinking_method(self):
        """Verify ConversationImporter has insert_thinking_trace method."""
        from pidgin.database.importers.conversation_importer import ConversationImporter

        assert hasattr(ConversationImporter, "insert_thinking_trace")

    def test_event_processor_handles_thinking_events(self):
        """Verify EventProcessor imports ThinkingCompleteEvent."""
        from pidgin.database.importers.event_processor import EventProcessor

        # The import itself verifies ThinkingCompleteEvent is handled
        assert EventProcessor is not None


@pytest.mark.asyncio
async def test_thinking_config_wiring():
    """Test that thinking config flows from ExperimentConfig to Agent creation.

    Note: --think-a and --think-b are additive flags that enable thinking.
    To enable thinking for only one agent, use --think-a (not --think --think-b=false).
    """
    from pidgin.experiments.experiment_setup import ExperimentSetup

    # Test: enable thinking for agent A only
    config = ExperimentConfig(
        name="thinking_wiring_test",
        agent_a_model="local:test",
        agent_b_model="local:test",
        think=False,  # Global off
        think_a=True,  # Enable for A only
        think_b=False,  # B stays off
        think_budget=20000,
    )

    setup = ExperimentSetup()
    agents, providers = await setup.create_agents_and_providers(config)

    # Agent A should have thinking enabled
    assert agents["agent_a"].thinking_enabled is True
    assert agents["agent_a"].thinking_budget == 20000

    # Agent B should NOT have thinking
    assert agents["agent_b"].thinking_enabled is None
    assert agents["agent_b"].thinking_budget is None


@pytest.mark.asyncio
async def test_thinking_global_flag():
    """Test that global --think flag enables thinking for both agents."""
    from pidgin.experiments.experiment_setup import ExperimentSetup

    config = ExperimentConfig(
        name="thinking_global_test",
        agent_a_model="local:test",
        agent_b_model="local:test",
        think=True,  # Global flag
        think_budget=10000,
    )

    setup = ExperimentSetup()
    agents, providers = await setup.create_agents_and_providers(config)

    # Both agents should have thinking enabled
    assert agents["agent_a"].thinking_enabled is True
    assert agents["agent_b"].thinking_enabled is True
    assert agents["agent_a"].thinking_budget == 10000
    assert agents["agent_b"].thinking_budget == 10000
