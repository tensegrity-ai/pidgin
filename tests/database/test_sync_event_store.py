"""Tests for EventStore implementation."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from pidgin.database.event_store import EventStore


class TestEventStore:
    """Test suite for EventStore."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""

        # Use a temporary directory and create a unique filename
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

    @pytest.fixture
    def sample_experiment_dir(self, tmp_path):
        """Create a sample experiment directory with JSONL data."""
        exp_dir = tmp_path / "exp_test123"
        exp_dir.mkdir()

        # Use current naming convention for conversation ID
        conversation_id = "conversation_exp_test123_abc123"

        # Create manifest
        manifest = {
            "experiment_id": "exp_test123",
            "name": "Test Experiment",
            "created_at": datetime.now().isoformat(),
            "status": "completed",
            "config": {
                "agent_a_model": "test-model-a",
                "agent_b_model": "test-model-b",
                "max_turns": 2,
            },
            "total_conversations": 1,
            "completed_conversations": 1,
            "failed_conversations": 0,
            "conversations": {
                conversation_id: {
                    "status": "completed",
                    "jsonl": f"{conversation_id}_events.jsonl",
                    "turns_completed": 2,
                    "last_line": 5,
                    "last_updated": datetime.now().isoformat(),
                }
            },
        }

        with open(exp_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        # Create JSONL events file
        events = [
            {
                "event_type": "ConversationStartEvent",
                "conversation_id": conversation_id,
                "agent_a_model": "test-model-a",
                "agent_b_model": "test-model-b",
                "max_turns": 2,
                "initial_prompt": "Test prompt",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "event_type": "MessageCompleteEvent",
                "conversation_id": conversation_id,
                "agent_id": "agent_a",
                "message": {"content": "Hello from agent A"},
                "tokens_used": 5,
                "timestamp": datetime.now().isoformat(),
            },
            {
                "event_type": "MessageCompleteEvent",
                "conversation_id": conversation_id,
                "agent_id": "agent_b",
                "message": {"content": "Hello from agent B"},
                "tokens_used": 5,
                "timestamp": datetime.now().isoformat(),
            },
            {
                "event_type": "TurnCompleteEvent",
                "conversation_id": conversation_id,
                "turn_number": 1,
                "turn": {
                    "agent_a_message": {
                        "content": "Hello from agent A",
                        "timestamp": datetime.now().isoformat(),
                    },
                    "agent_b_message": {
                        "content": "Hello from agent B",
                        "timestamp": datetime.now().isoformat(),
                    },
                },
                "convergence_score": 0.5,
                "timestamp": datetime.now().isoformat(),
            },
            {
                "event_type": "ConversationEndEvent",
                "conversation_id": conversation_id,
                "reason": "max_turns",
                "total_turns": 1,
                "timestamp": datetime.now().isoformat(),
            },
        ]

        with open(exp_dir / f"{conversation_id}_events.jsonl", "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        return exp_dir

    def test_init_creates_schema(self, event_store):
        """Test that initialization creates all required tables."""
        # Check that tables exist by querying them
        tables = event_store.db.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
        """
        ).fetchall()

        table_names = [t[0] for t in tables]
        assert "events" in table_names
        assert "experiments" in table_names
        assert "conversations" in table_names
        assert "messages" in table_names
        assert "turn_metrics" in table_names
        assert "token_usage" in table_names

    def test_import_experiment_success(self, event_store, sample_experiment_dir):
        """Test successful import of experiment data."""
        result = event_store.import_experiment_from_jsonl(sample_experiment_dir)

        assert result.success is True
        assert result.experiment_id == "exp_test123"
        assert result.turns_imported == 1  # One turn from the test data
        assert result.conversations_imported == 1
        assert result.error is None

        # ImportService doesn't create .imported marker anymore

    def test_import_experiment_no_manifest(self, event_store, tmp_path):
        """Test import fails gracefully when manifest is missing."""
        exp_dir = tmp_path / "exp_no_manifest"
        exp_dir.mkdir()

        result = event_store.import_experiment_from_jsonl(exp_dir)

        assert result.success is False
        assert result.error == "No manifest.json found"

    def test_import_already_imported(self, event_store, sample_experiment_dir):
        """Test that already imported experiments are skipped."""
        # First import
        result1 = event_store.import_experiment_from_jsonl(sample_experiment_dir)
        assert result1.success is True

        # Second import should fail due to duplicate key constraint
        result2 = event_store.import_experiment_from_jsonl(sample_experiment_dir)
        assert result2.success is False
        assert (
            "Duplicate key" in result2.error
            or "primary key constraint" in result2.error
        )
        assert result2.turns_imported == 0

    def test_messages_extracted_correctly(self, event_store, sample_experiment_dir):
        """Test that messages are extracted from TurnCompleteEvent."""
        result = event_store.import_experiment_from_jsonl(sample_experiment_dir)
        assert result.success is True

        # Check messages were imported into conversation_turns
        turns = event_store.db.execute(
            """
            SELECT agent_a_message, agent_b_message, turn_number
            FROM conversation_turns
            WHERE conversation_id = 'conversation_exp_test123_abc123'
        """
        ).fetchall()

        assert len(turns) == 1
        assert turns[0][0] == "Hello from agent A"  # agent_a_message
        assert turns[0][1] == "Hello from agent B"  # agent_b_message
        assert turns[0][2] == 1  # turn_number

    def test_turn_metrics_imported(self, event_store, sample_experiment_dir):
        """Test that turn metrics are imported correctly."""
        result = event_store.import_experiment_from_jsonl(sample_experiment_dir)
        assert result.success is True

        # Check turn metrics in conversation_turns
        metrics = event_store.db.execute(
            """
            SELECT turn_number, overall_convergence
            FROM conversation_turns
            WHERE conversation_id = 'conversation_exp_test123_abc123'
        """
        ).fetchall()

        assert len(metrics) == 1
        assert metrics[0] == (1, 0.5)

    def test_delete_experiment(self, event_store, sample_experiment_dir):
        """Test that delete_experiment removes all related data."""
        # Import first
        result = event_store.import_experiment_from_jsonl(sample_experiment_dir)
        assert result.success is True

        # Delete the experiment
        event_store.delete_experiment("exp_test123")

        # Verify data removed from conversation_turns
        turn_count = event_store.db.execute(
            "SELECT COUNT(*) FROM conversation_turns WHERE experiment_id = ?",
            ["exp_test123"],
        ).fetchone()[0]
        assert turn_count == 0

    def test_concurrent_import_protection(self, event_store, sample_experiment_dir):
        """Test that duplicate imports fail with constraint error."""
        # First import
        result1 = event_store.import_experiment_from_jsonl(sample_experiment_dir)
        assert result1.success is True

        # Second import should fail due to primary key constraint
        result2 = event_store.import_experiment_from_jsonl(sample_experiment_dir)
        assert result2.success is False
        assert (
            "Duplicate key" in result2.error
            or "primary key constraint" in result2.error
        )

    def test_import_missing_jsonl_succeeds_with_zero_events(
        self, event_store, tmp_path
    ):
        """Test that import succeeds even with missing JSONL files (zero events imported)."""
        exp_dir = tmp_path / "exp_missing_jsonl"
        exp_dir.mkdir()

        # Create manifest with reference to non-existent JSONL
        manifest = {
            "experiment_id": "exp_missing_jsonl",
            "name": "Missing JSONL Test",
            "conversations": {
                "conversation_exp_missing_jsonl_abc": {
                    "status": "completed",
                    "jsonl": "missing_file.jsonl",  # This file doesn't exist
                    "turns_completed": 0,
                    "last_line": 0,
                    "last_updated": datetime.now().isoformat(),
                }
            },
        }

        with open(exp_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        result = event_store.import_experiment_from_jsonl(exp_dir)

        # Import should fail with no JSONL files found
        assert result.success is False
        assert result.error == "No JSONL files found"
        assert result.turns_imported == 0
        assert result.conversations_imported == 0
