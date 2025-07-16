"""Comprehensive tests for EventStore with all EventStore functionality."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from pidgin.core.events import (
    ConversationStartEvent,
)
from pidgin.database.event_store import EventStore


class TestEventStoreFull:
    """Comprehensive test suite for EventStore."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""

        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.duckdb"
        yield db_path
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def event_store(self, temp_db_path):
        """Create a EventStore instance."""
        store = EventStore(temp_db_path)
        yield store
        store.close()

    # Event Operations Tests
    def test_save_and_get_events(self, event_store):
        """Test saving and retrieving events."""
        # Create a test event
        event = ConversationStartEvent(
            conversation_id="conv_123",
            agent_a_model="gpt-4",
            agent_b_model="claude-3",
            initial_prompt="Test conversation",
            max_turns=10,
        )

        # Save event
        event_store.save_event(event, "experiment_123", "conv_123")

        # Get events
        events = event_store.get_events(
            conversation_id="conv_123", event_types=["ConversationStartEvent"]
        )

        assert len(events) == 1
        assert events[0]["event_type"] == "ConversationStartEvent"
        assert events[0]["conversation_id"] == "conv_123"

    # Experiment Operations Tests
    def test_create_and_get_experiment(self, event_store):
        """Test creating and retrieving experiments."""
        config = {
            "agent_a_model": "gpt-4",
            "agent_b_model": "claude-3",
            "max_turns": 10,
            "max_conversations": 5,
        }

        # Create experiment
        exp_id = event_store.create_experiment("test-experiment", config)

        assert exp_id is not None

        # Get experiment
        exp = event_store.get_experiment(exp_id)

        assert exp is not None
        assert exp["name"] == "test-experiment"
        assert exp["config"] == config
        assert exp["status"] == "created"

    def test_update_experiment_status(self, event_store):
        """Test updating experiment status."""
        # Create experiment
        exp_id = event_store.create_experiment("test-exp", {})

        # Update status
        event_store.update_experiment_status(exp_id, "running")

        # Verify update
        exp = event_store.get_experiment(exp_id)
        assert exp["status"] == "running"

        # Update with end time
        end_time = datetime.now()
        event_store.update_experiment_status(exp_id, "completed", ended_at=end_time)

        exp = event_store.get_experiment(exp_id)
        assert exp["status"] == "completed"
        assert exp["completed_at"] is not None

    def test_list_experiments(self, event_store):
        """Test listing experiments with filters."""
        # Create multiple experiments
        exp1 = event_store.create_experiment("exp1", {})
        exp2 = event_store.create_experiment("exp2", {})
        exp3 = event_store.create_experiment("exp3", {})

        # Update statuses
        event_store.update_experiment_status(exp1, "completed")
        event_store.update_experiment_status(exp2, "running")
        event_store.update_experiment_status(exp3, "completed")

        # List all
        all_exps = event_store.list_experiments()
        assert len(all_exps) >= 3

        # List by status
        completed = event_store.list_experiments(status_filter="completed")
        assert len(completed) >= 2
        assert all(e["status"] == "completed" for e in completed)

        # Test limit
        limited = event_store.list_experiments(limit=1)
        assert len(limited) == 1

    # Conversation Operations Tests
    def test_create_and_get_conversation(self, event_store):
        """Test creating and retrieving conversations."""
        # Create experiment first
        exp_id = event_store.create_experiment("test-exp", {})

        # Create conversation
        conv_config = {
            "agent_a": {"model": "gpt-4", "temperature": 0.7},
            "agent_b": {"model": "claude-3", "temperature": 0.8},
            "max_turns": 5,
        }

        event_store.create_conversation(exp_id, "conversation_123", conv_config)

        # Get conversation
        conversation = event_store.get_conversation("conversation_123")

        assert conversation is not None
        assert conversation["conversation_id"] == "conversation_123"
        assert conversation["experiment_id"] == exp_id
        assert conversation["status"] == "created"

    def test_update_conversation_status(self, event_store):
        """Test updating conversation status."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})
        event_store.create_conversation(exp_id, "conversation_123", {})

        # Update status
        event_store.update_conversation_status(
            "conversation_123", "completed", end_reason="max_turns", error_message=None
        )

        # Verify
        conversation = event_store.get_conversation("conversation_123")
        assert conversation["status"] == "completed"
        assert conversation["convergence_reason"] == "max_turns"

    def test_get_conversation_history(self, event_store):
        """Test retrieving conversation message history."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})
        event_store.create_conversation(exp_id, "conv_123", {})

        # Add messages
        event_store.save_message("conv_123", 1, "agent_a", "assistant", "Hello!", 5)
        event_store.save_message("conv_123", 1, "agent_b", "assistant", "Hi there!", 6)
        event_store.save_message(
            "conv_123", 2, "agent_a", "assistant", "How are you?", 7
        )

        # Get history
        history = event_store.get_conversation_history("conv_123")

        assert len(history) == 3
        assert history[0]["content"] == "Hello!"
        assert history[0]["turn_number"] == 1
        assert history[2]["turn_number"] == 2

    # Agent Name Operations Tests
    def test_log_and_get_agent_names(self, event_store):
        """Test logging and retrieving agent names."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})
        event_store.create_conversation(exp_id, "conv_123", {})

        # Log names
        event_store.log_agent_name("conv_123", "agent_a", "Alice", turn_number=0)
        event_store.log_agent_name("conv_123", "agent_b", "Bob", turn_number=0)

        # Get names
        names = event_store.get_agent_names("conv_123")

        assert names["agent_a"] == "Alice"
        assert names["agent_b"] == "Bob"

    # Message Operations Tests
    def test_save_message(self, event_store):
        """Test saving messages."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})
        event_store.create_conversation(exp_id, "conv_123", {})

        # Save message
        event_store.save_message(
            conversation_id="conv_123",
            turn_number=1,
            agent_id="agent_a",
            role="assistant",
            content="Test message",
            tokens_used=10,
        )

        # Verify via get_turn_messages
        messages = event_store.get_turn_messages("conv_123", 1)

        assert len(messages) == 1
        assert messages[0]["content"] == "Test message"
        assert messages[0]["token_count"] == 10

    def test_get_turn_messages(self, event_store):
        """Test retrieving messages for a specific turn."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})
        event_store.create_conversation(exp_id, "conv_123", {})

        # Save messages for different turns
        event_store.save_message("conv_123", 1, "agent_a", "assistant", "Turn 1 A", 5)
        event_store.save_message("conv_123", 1, "agent_b", "assistant", "Turn 1 B", 6)
        event_store.save_message("conv_123", 2, "agent_a", "assistant", "Turn 2 A", 7)

        # Get turn 1 messages
        turn1_msgs = event_store.get_turn_messages("conv_123", 1)
        assert len(turn1_msgs) == 2
        assert set(m["content"] for m in turn1_msgs) == {"Turn 1 A", "Turn 1 B"}

        # Get turn 2 messages
        turn2_msgs = event_store.get_turn_messages("conv_123", 2)
        assert len(turn2_msgs) == 1
        assert turn2_msgs[0]["content"] == "Turn 2 A"

    # Metrics Operations Tests
    def test_log_turn_metrics(self, event_store):
        """Test logging turn metrics."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})
        event_store.create_conversation(exp_id, "conv_123", {})

        # Log metrics - during live conversations only convergence_score is logged
        metrics = {"convergence_score": 0.75}

        event_store.log_turn_metrics("conv_123", 1, metrics)

        # Verify by querying directly
        result = event_store.db.execute(
            """
            SELECT convergence_score
            FROM turn_metrics
            WHERE conversation_id = ? AND turn_number = ?
        """,
            ["conv_123", 1],
        ).fetchone()

        assert result[0] == 0.75

    def test_log_message_metrics(self, event_store):
        """Test logging message metrics."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})
        event_store.create_conversation(exp_id, "conv_123", {})

        # First create the turn metrics row (required during live conversations)
        event_store.log_turn_metrics("conv_123", 1, {"convergence_score": 0.5})

        # Log message metrics
        event_store.log_message_metrics(
            conversation_id="conv_123",
            turn_number=1,
            agent_id="agent_a",
            message_length=100,
            vocabulary_size=25,
            punctuation_ratio=0.05,
            sentiment_score=0.8,
        )

        # Verify - check that metrics are stored in turn_metrics
        result = event_store.db.execute(
            """
            SELECT message_a_length, message_a_unique_words
            FROM turn_metrics
            WHERE conversation_id = ? AND turn_number = ?
        """,
            ["conv_123", 1],
        ).fetchone()

        assert result is not None
        assert result[0] == 100  # message_a_length
        assert result[1] == 25  # message_a_unique_words

    def test_get_experiment_metrics(self, event_store):
        """Test retrieving experiment metrics."""
        # Setup experiment with conversations
        exp_id = event_store.create_experiment("test-exp", {})

        # Create multiple conversations
        for i in range(3):
            conversation_id = f"conversation_{i}"
            event_store.create_conversation(exp_id, conversation_id, {})

            # Add some metrics
            event_store.log_turn_metrics(
                conversation_id, 1, {"convergence_score": 0.5 + i * 0.1}
            )
            event_store.log_turn_metrics(
                conversation_id, 2, {"convergence_score": 0.6 + i * 0.1}
            )

            # Complete conversations
            event_store.update_conversation_status(conversation_id, "completed")

        # Get experiment metrics
        metrics = event_store.get_experiment_metrics(exp_id)

        assert "avg_convergence" in metrics
        assert "total_conversations" in metrics
        assert metrics["total_conversations"] == 3

    def test_calculate_convergence_metrics(self, event_store):
        """Test calculating convergence metrics."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})
        event_store.create_conversation(exp_id, "conv_123", {})

        # Add turn metrics
        for i in range(5):
            event_store.log_turn_metrics(
                "conv_123", i + 1, {"convergence_score": 0.5 + i * 0.1}
            )

        # Calculate metrics
        metrics = event_store.calculate_convergence_metrics("conv_123")

        assert "final_score" in metrics
        assert "average_score" in metrics
        assert "max_score" in metrics
        assert metrics["final_score"] == 0.9  # Last score
        assert metrics["average_score"] == 0.7  # Average of 0.5, 0.6, 0.7, 0.8, 0.9

    # Token Usage Tests
    def test_log_token_usage(self, event_store):
        """Test logging token usage."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})
        event_store.create_conversation(exp_id, "conv_123", {})

        # Log token usage
        event_store.log_token_usage(
            conversation_id="conv_123",
            provider="openai",
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_cost=0.015,
        )

        # Verify
        result = event_store.db.execute(
            """
            SELECT total_tokens, total_cost
            FROM token_usage
            WHERE conversation_id = ?
        """,
            ["conv_123"],
        ).fetchone()

        assert result[0] == 150  # 100 + 50
        assert result[1] == 0.015

    # Deletion Tests
    def test_delete_experiment(self, event_store):
        """Test deleting an experiment and all related data."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})
        event_store.create_conversation(exp_id, "conv_123", {})
        event_store.save_message("conv_123", 1, "agent_a", "assistant", "Test", 5)
        event_store.log_turn_metrics("conv_123", 1, {"convergence_score": 0.5})

        # Delete experiment
        event_store.delete_experiment(exp_id)

        # Verify deletion
        assert event_store.get_experiment(exp_id) is None
        assert event_store.get_conversation("conv_123") is None
        assert len(event_store.get_turn_messages("conv_123", 1)) == 0

    def test_delete_conversation(self, event_store):
        """Test deleting a conversation and related data."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})
        event_store.create_conversation(exp_id, "conv_123", {})
        event_store.create_conversation(exp_id, "conv_456", {})
        event_store.save_message("conv_123", 1, "agent_a", "assistant", "Test", 5)

        # Delete one conversation
        event_store.delete_conversation("conv_123")

        # Verify
        assert event_store.get_conversation("conv_123") is None
        assert (
            event_store.get_conversation("conv_456") is not None
        )  # Other conv still exists
        assert event_store.get_experiment(exp_id) is not None  # Experiment still exists

    # Backward Compatibility Tests
    def test_get_conversation_agent_configs(self, event_store):
        """Test getting agent configurations from conversation."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})
        config = {
            "agent_a": {"model": "gpt-4", "temperature": 0.7},
            "agent_b": {"model": "claude-3", "temperature": 0.8},
        }
        event_store.create_conversation(exp_id, "conv_123", config)

        # Get configs
        configs = event_store.get_conversation_agent_configs("conv_123")

        assert configs is not None
        assert configs["agent_a"]["model"] == "gpt-4"
        assert configs["agent_b"]["temperature"] == 0.8

    def test_get_experiment_summary(self, event_store):
        """Test getting experiment summary with statistics."""
        # Setup
        exp_id = event_store.create_experiment("test-exp", {})

        # Create conversations with different statuses
        event_store.create_conversation(exp_id, "conv_1", {})
        event_store.update_conversation_status("conv_1", "completed")

        event_store.create_conversation(exp_id, "conv_2", {})
        event_store.update_conversation_status("conv_2", "failed")

        event_store.create_conversation(exp_id, "conv_3", {})
        event_store.update_conversation_status("conv_3", "running")

        # Get summary
        summary = event_store.get_experiment_summary(exp_id)

        assert summary["experiment_id"] == exp_id
        assert summary["total_conversations"] == 3
        assert summary["completed"] == 1
        assert summary["failed"] == 1
        assert summary["running"] == 1
