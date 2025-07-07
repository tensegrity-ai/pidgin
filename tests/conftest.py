# tests/conftest.py
"""Pytest configuration and shared fixtures."""

import asyncio
import pytest
import pytest_asyncio
import tempfile
import shutil
from pathlib import Path
import os
import sys
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock
import json

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ===== Core Pytest Configuration =====

@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ===== Directory and File Fixtures =====

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_pidgin_output_dir(temp_dir):
    """Create a mock pidgin_output directory structure."""
    output_dir = temp_dir / "pidgin_output"
    output_dir.mkdir()
    (output_dir / "conversations").mkdir()
    (output_dir / "experiments").mkdir()
    (output_dir / "experiments" / "active").mkdir()
    return output_dir


@pytest.fixture
def mock_config_dir(temp_dir, monkeypatch):
    """Create a mock config directory and set HOME."""
    config_dir = temp_dir / ".config" / "pidgin"
    config_dir.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(temp_dir))
    return config_dir


# ===== Environment and Config Fixtures =====

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    def _mock_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key, value)
    return _mock_env


@pytest.fixture
def mock_config(monkeypatch, mock_config_dir):
    """Mock configuration settings."""
    from pidgin.config.config import Config
    
    config = Config()
    # Reset to defaults
    config._config = {
        "models": {
            "default_model_a": "local:test",
            "default_model_b": "local:test"
        },
        "display": {
            "show_progress": True,
            "show_cost": True
        },
        "experiments": {
            "max_parallel": 1,
            "default_repetitions": 3
        }
    }
    
    # Mock the global config instance
    monkeypatch.setattr("pidgin.config.config._config_instance", config)
    return config


# ===== Model and Agent Fixtures =====

@pytest.fixture
def sample_agents():
    """Sample agents for testing."""
    from pidgin.core.types import Agent
    
    return [
        Agent(
            id="agent_a",
            model="local:test",
            display_name="Test Agent A",
            temperature=0.7
        ),
        Agent(
            id="agent_b",
            model="local:test",
            display_name="Test Agent B",
            temperature=0.7
        )
    ]


@pytest.fixture
def sample_messages():
    """Sample messages for testing."""
    from pidgin.core.types import Message
    
    return [
        Message(
            role="user",
            content="Hello, how are you?",
            agent_id="agent_a",
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        ),
        Message(
            role="assistant", 
            content="I'm doing well, thank you! How can I help you today?",
            agent_id="agent_b",
            timestamp=datetime(2024, 1, 1, 12, 0, 1)
        )
    ]


# ===== Event Fixtures =====

@pytest.fixture
def sample_events():
    """Sample events for testing."""
    from pidgin.core.events import (
        ConversationStartedEvent,
        TurnStartedEvent,
        MessageEvent,
        TurnCompletedEvent,
        ConversationCompletedEvent
    )
    
    conv_id = "test_conv_123"
    exp_id = "test_exp_456"
    
    return {
        "conversation_started": ConversationStartedEvent(
            conversation_id=conv_id,
            experiment_id=exp_id,
            agents=["agent_a", "agent_b"],
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        ),
        "turn_started": TurnStartedEvent(
            conversation_id=conv_id,
            turn_number=1,
            active_agent="agent_a",
            timestamp=datetime(2024, 1, 1, 12, 0, 1)
        ),
        "message": MessageEvent(
            conversation_id=conv_id,
            turn_number=1,
            agent_id="agent_a",
            role="user",
            content="Hello!",
            timestamp=datetime(2024, 1, 1, 12, 0, 2)
        ),
        "turn_completed": TurnCompletedEvent(
            conversation_id=conv_id,
            turn_number=1,
            timestamp=datetime(2024, 1, 1, 12, 0, 3)
        ),
        "conversation_completed": ConversationCompletedEvent(
            conversation_id=conv_id,
            total_turns=5,
            status="completed",
            timestamp=datetime(2024, 1, 1, 12, 0, 10)
        )
    }


# ===== Provider Fixtures =====

@pytest.fixture
def mock_provider():
    """Create a mock provider for testing."""
    from pidgin.providers.base import Provider
    
    provider = Mock(spec=Provider)
    provider.name = "mock"
    provider.supports_streaming = True
    
    # Mock stream_response to return an async generator
    async def mock_stream():
        yield {"type": "text", "text": "Hello "}
        yield {"type": "text", "text": "world!"}
        yield {"type": "usage", "usage": {"total_tokens": 10}}
    
    provider.stream_response = Mock(return_value=mock_stream())
    return provider


@pytest.fixture
def mock_anthropic_provider(mocker):
    """Create a mock Anthropic provider."""
    provider = mocker.create_autospec("pidgin.providers.anthropic.AnthropicProvider")
    provider.name = "anthropic"
    
    async def mock_stream():
        yield {"type": "text", "text": "Claude says hello!"}
        yield {"type": "usage", "usage": {"input_tokens": 5, "output_tokens": 5}}
    
    provider.stream_response.return_value = mock_stream()
    return provider


@pytest.fixture
def mock_openai_provider(mocker):
    """Create a mock OpenAI provider."""
    provider = mocker.create_autospec("pidgin.providers.openai.OpenAIProvider")
    provider.name = "openai"
    
    async def mock_stream():
        yield {"type": "text", "text": "GPT says hello!"}
        yield {"type": "usage", "usage": {"prompt_tokens": 5, "completion_tokens": 5}}
    
    provider.stream_response.return_value = mock_stream()
    return provider


# ===== Event Bus Fixtures =====

@pytest_asyncio.fixture
async def event_bus(mock_pidgin_output_dir):
    """Create an EventBus instance for testing."""
    from pidgin.core.event_bus import EventBus
    
    # Create EventBus with conversations directory for JSONL files
    conversations_dir = mock_pidgin_output_dir / "conversations"
    bus = EventBus(event_log_dir=str(conversations_dir))
    
    yield bus
    
    # Cleanup
    await bus.stop()


# ===== Database Fixtures =====

@pytest.fixture
def mock_event_store(mocker):
    """Create a mock EventStore."""
    store = mocker.create_autospec("pidgin.database.event_store.EventStore")
    store.save_conversation = AsyncMock()
    store.get_conversation = AsyncMock()
    store.list_conversations = AsyncMock(return_value=[])
    return store


@pytest.fixture
def in_memory_duckdb():
    """Create an in-memory DuckDB for testing."""
    from pidgin.database.event_store import EventStore
    
    store = EventStore(Path(":memory:"))
    yield store
    store.close()


# ===== CLI Fixtures =====

@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def mock_console(mocker):
    """Mock Rich console for testing output."""
    console = mocker.patch("pidgin.cli.constants.console")
    return console


# ===== Time Fixtures =====

@pytest.fixture
def frozen_time(mocker):
    """Freeze time for deterministic tests."""
    def _freeze(dt):
        mocker.patch("pidgin.core.events.datetime", Mock(now=Mock(return_value=dt)))
        mocker.patch("pidgin.core.types.datetime", Mock(now=Mock(return_value=dt)))
        return dt
    return _freeze


# ===== Async Helpers =====

@pytest.fixture
def async_mock():
    """Helper to create async mocks."""
    def _create_async_mock(*args, **kwargs):
        mock = AsyncMock(*args, **kwargs)
        return mock
    return _create_async_mock


# ===== Test Data Generators =====

@pytest.fixture
def make_conversation():
    """Factory for creating test conversations."""
    from pidgin.core.types import Conversation, Message
    
    def _make(conv_id="test_conv", num_messages=10):
        messages = []
        for i in range(num_messages):
            agent_id = "agent_a" if i % 2 == 0 else "agent_b"
            role = "user" if i % 2 == 0 else "assistant"
            messages.append(
                Message(
                    role=role,
                    content=f"Message {i}",
                    agent_id=agent_id,
                    timestamp=datetime(2024, 1, 1, 12, 0, i)
                )
            )
        
        return Conversation(
            id=conv_id,
            agents=["agent_a", "agent_b"],
            messages=messages,
            metadata={"test": True}
        )
    
    return _make


@pytest.fixture
def make_experiment():
    """Factory for creating test experiments."""
    from pidgin.core.types import Experiment
    
    def _make(exp_id="test_exp", num_conversations=5):
        return Experiment(
            id=exp_id,
            name="Test Experiment",
            conversations=[f"conv_{i}" for i in range(num_conversations)],
            config={
                "model_a": "local:test",
                "model_b": "local:test",
                "max_turns": 10
            },
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
    
    return _make


# ===== Cleanup Fixtures =====

@pytest.fixture(autouse=True)
def cleanup_singletons(monkeypatch):
    """Clean up singleton instances between tests."""
    # Note: Current implementation doesn't use singletons
    # This fixture is kept for future use if singletons are added
    yield


# ===== Test Markers =====

# Mark slow tests
pytest.mark.slow = pytest.mark.skipif(
    "not config.getoption('--runslow')",
    reason="need --runslow option to run"
)

# Mark integration tests  
pytest.mark.integration = pytest.mark.skipif(
    "not config.getoption('--integration')",
    reason="need --integration option to run"
)


# ===== Pytest Configuration Hooks =====

def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--integration", action="store_true", default=False, help="run integration tests"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")