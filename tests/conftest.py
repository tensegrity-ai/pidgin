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
def in_memory_db():
    """Create an in-memory DuckDB connection for fast unit tests."""
    import duckdb
    
    conn = duckdb.connect(':memory:')
    yield conn
    conn.close()


@pytest.fixture
def in_memory_db_with_schema(in_memory_db):
    """In-memory DuckDB with schema already set up."""
    # Read the schema file and execute it
    schema_path = Path(__file__).parent.parent / "pidgin" / "database" / "schema.sql"
    if schema_path.exists():
        with open(schema_path) as f:
            schema_sql = f.read()
            # Execute each statement separately
            for statement in schema_sql.split(';'):
                if statement.strip():
                    in_memory_db.execute(statement)
    
    return in_memory_db


@pytest.fixture
def temp_db_path(temp_dir):
    """Create a temporary database file path for persistence tests."""
    return temp_dir / "test_pidgin.duckdb"


@pytest.fixture
def file_based_db(temp_db_path):
    """File-based DuckDB for testing persistence and concurrent access."""
    import duckdb
    
    conn = duckdb.connect(str(temp_db_path))
    yield conn
    conn.close()


@pytest.fixture
def event_store_memory():
    """Create an EventStore with in-memory database for fast tests."""
    from pidgin.database.event_store import EventStore
    import duckdb
    
    # Create a custom EventStore that uses in-memory connection
    class InMemoryEventStore(EventStore):
        def __init__(self):
            self.db_path = Path(":memory:")  # For compatibility
            self._conn = duckdb.connect(':memory:')
            self._init_database()
    
    store = InMemoryEventStore()
    yield store
    store.close()


@pytest.fixture
def event_store_file(temp_db_path):
    """Create an EventStore with file-based database for persistence tests."""
    from pidgin.database.event_store import EventStore
    
    store = EventStore(temp_db_path)
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


# ===== Data Generation with Faker =====

@pytest.fixture
def faker_factory():
    """Create a Faker instance for generating test data."""
    from faker import Faker
    return Faker()


@pytest.fixture
def realistic_conversation_generator(faker_factory):
    """Generate realistic conversation data using Faker."""
    from pidgin.core.types import Message, Conversation
    
    def _generate(num_turns=10, topic=None):
        """Generate a realistic conversation between two agents."""
        fake = faker_factory
        
        # Define conversation topics and patterns
        topics = {
            "technical": [
                "Can you explain {concept}?",
                "How does {technology} work?",
                "What are the benefits of {approach}?",
                "I'm having trouble with {problem}. Any suggestions?"
            ],
            "casual": [
                "What do you think about {topic}?",
                "Have you heard about {event}?",
                "I've been wondering about {question}.",
                "Do you have any recommendations for {activity}?"
            ],
            "creative": [
                "Can you help me write a {type} about {subject}?",
                "I need ideas for {project}.",
                "What's your take on {creative_work}?",
                "How would you approach {challenge}?"
            ]
        }
        
        if not topic:
            topic = fake.random_element(list(topics.keys()))
        
        templates = topics.get(topic, topics["casual"])
        messages = []
        
        for i in range(num_turns):
            is_user_turn = i % 2 == 0
            
            if is_user_turn:
                # Generate user message
                template = fake.random_element(templates)
                content = template.format(
                    concept=fake.bs(),
                    technology=fake.company(),
                    approach=fake.catch_phrase(),
                    problem=fake.sentence(nb_words=6),
                    topic=fake.sentence(nb_words=4),
                    event=fake.catch_phrase(),
                    question=fake.sentence(nb_words=8),
                    activity=fake.job(),
                    type=fake.random_element(["story", "poem", "article"]),
                    subject=fake.word(),
                    project=fake.bs(),
                    creative_work=fake.catch_phrase(),
                    challenge=fake.sentence(nb_words=5)
                )
            else:
                # Generate assistant response
                responses = [
                    f"That's an interesting question about {fake.word()}. {fake.paragraph(nb_sentences=3)}",
                    f"I understand your concern. {fake.paragraph(nb_sentences=2)} Would you like me to elaborate?",
                    f"Based on my understanding, {fake.paragraph(nb_sentences=4)}",
                    f"Here's what I think: {fake.paragraph(nb_sentences=3)} Does this help?"
                ]
                content = fake.random_element(responses)
            
            messages.append(Message(
                role="user" if is_user_turn else "assistant",
                content=content,
                agent_id="agent_a" if is_user_turn else "agent_b",
                timestamp=fake.date_time_between(start_date="-1hour")
            ))
        
        # Sort messages by timestamp
        messages.sort(key=lambda m: m.timestamp)
        
        return Conversation(
            id=f"conv_{fake.uuid4()}",
            agents=["agent_a", "agent_b"],
            messages=messages,
            metadata={
                "topic": topic,
                "generated_by": "faker",
                "seed": fake.random_int()
            }
        )
    
    return _generate


@pytest.fixture
def metrics_test_data_generator(faker_factory):
    """Generate test data specifically for metrics testing."""
    from pidgin.core.types import Message
    
    def _generate_messages_with_pattern(pattern_type="convergent"):
        """Generate messages with specific linguistic patterns for testing metrics."""
        fake = faker_factory
        
        patterns = {
            "convergent": {
                # Messages that should show high convergence
                "vocabulary": ["understand", "agree", "exactly", "yes", "right", "correct"],
                "style": "short_formal",
                "length_trend": "decreasing"
            },
            "divergent": {
                # Messages that should show low convergence
                "vocabulary": ["disagree", "however", "actually", "but", "different", "wrong"],
                "style": "varied",
                "length_trend": "increasing"
            },
            "stable": {
                # Messages that maintain consistent patterns
                "vocabulary": fake.words(nb=20),
                "style": "consistent",
                "length_trend": "stable"
            }
        }
        
        pattern = patterns.get(pattern_type, patterns["stable"])
        messages = []
        base_length = 50
        
        for i in range(20):
            is_agent_a = i % 2 == 0
            
            # Calculate message length based on trend
            if pattern["length_trend"] == "decreasing":
                length = base_length - (i * 2)
            elif pattern["length_trend"] == "increasing":
                length = base_length + (i * 3)
            else:
                length = base_length
            
            # Build message with pattern vocabulary
            if pattern_type == "convergent" and i > 10:
                # Later messages use more shared vocabulary
                words = fake.random_elements(
                    elements=pattern["vocabulary"],
                    length=min(5, length // 10),
                    unique=False
                )
                content = " ".join(words) + " " + fake.sentence(nb_words=max(1, length // 10 - 5))
            else:
                content = fake.sentence(nb_words=max(1, length // 10))
            
            messages.append(Message(
                role="user" if is_agent_a else "assistant",
                content=content,
                agent_id="agent_a" if is_agent_a else "agent_b",
                timestamp=fake.date_time_between(start_date="-1hour")
            ))
        
        return messages, pattern_type
    
    return _generate_messages_with_pattern


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
    config.addinivalue_line("markers", "database: marks tests that require a real database connection")