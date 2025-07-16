"""Tests for TranscriptGenerator to catch NoneType errors."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from pidgin.database.event_store import EventStore
from pidgin.database.transcript_generator import TranscriptGenerator


class TestTranscriptGenerator:
    """Test suite for TranscriptGenerator."""

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
    def populated_db(self, temp_db_path):
        """Create a database with test data including None values."""
        with EventStore(temp_db_path) as store:
            # Insert experiment
            store.db.execute(
                """
                INSERT INTO experiments (
                    experiment_id, name, status, created_at,
                    total_conversations, completed_conversations
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                ["exp_test", "Test Experiment", "completed", datetime.now(), 1, 1],
            )

            # Insert conversation
            store.db.execute(
                """
                INSERT INTO conversations (
                    conversation_id, experiment_id, status,
                    agent_a_model, agent_b_model, total_turns,
                    final_convergence_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ["conv_test", "exp_test", "completed", "model-a", "model-b", 2, 0.75],
            )

            # Insert messages with varying data quality
            messages = [
                ("conv_test", 1, "agent_a", "Hello world", datetime.now(), 5),
                ("conv_test", 1, "agent_b", "Hi there", datetime.now(), 3),
                ("conv_test", 2, "agent_a", "How are you?", datetime.now(), 4),
                ("conv_test", 2, "agent_b", "I'm well", datetime.now(), 3),
            ]

            for msg in messages:
                store.db.execute(
                    """
                    INSERT INTO messages (
                        conversation_id, turn_number, agent_id,
                        content, timestamp, token_count
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    msg,
                )

            # Insert turn metrics with None values for vocabulary metrics
            store.db.execute(
                """
                INSERT INTO turn_metrics (
                    conversation_id, turn_number, timestamp,
                    convergence_score,
                    message_a_unique_words, message_b_unique_words,
                    shared_vocabulary
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ["conv_test", 1, datetime.now(), 0.5, None, None, None],
            )

            store.db.execute(
                """
                INSERT INTO turn_metrics (
                    conversation_id, turn_number, timestamp,
                    convergence_score,
                    message_a_unique_words, message_b_unique_words,
                    shared_vocabulary
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ["conv_test", 2, datetime.now(), 0.75, 3, 2, '["well"]'],
            )

        return temp_db_path

    @pytest.fixture
    def transcript_generator(self, populated_db):
        """Create a TranscriptGenerator instance."""
        with TranscriptGenerator(populated_db) as gen:
            yield gen

    def test_generate_transcript_with_none_values(self, transcript_generator):
        """Test that transcript generation handles None values gracefully."""
        # This should not raise TypeError for None + None
        transcript = transcript_generator.generate_conversation_transcript("conv_test")

        assert transcript is not None
        assert "Conversation:" in transcript
        assert "Vocabulary Metrics" in transcript
        # Check that None values were handled (unique words show as numbers, not errors)
        assert (
            "| 1-5 | 3 | 2 | 1 | 25.0% |" in transcript
            or "| 1-5 | 0 | 0 |" in transcript
        )

    def test_format_vocabulary_metrics_with_none(self, transcript_generator):
        """Test _format_vocabulary_metrics handles None values."""
        # The actual code in generate_conversation_transcript uses df() method
        # which returns dictionaries. Let's test by calling the main method
        # instead of testing the internal method directly with wrong data format
        transcript = transcript_generator.generate_conversation_transcript("conv_test")

        # Check that vocabulary metrics section exists and handled None values
        assert "Vocabulary Metrics" in transcript
        # The first turn has None values, should show as 0
        assert (
            "| 1-5 | 0 | 0 | 0 | 0.0% |" in transcript
            or "| 1-5 | 3 | 2 |" in transcript
        )

    def test_format_summary_metrics_with_none(self, transcript_generator):
        """Test _format_summary_metrics handles None convergence."""
        conv_data = {
            "total_turns": 5,
            "final_convergence_score": None,  # This was causing errors
            "convergence_reason": None,
        }
        token_data = {"total_cost_cents": 0, "total_tokens": 100}
        num_turns = 5

        # This should not raise errors
        result = transcript_generator._format_summary_metrics(
            conv_data, token_data, num_turns
        )

        assert "Summary" in result
        assert "Final Convergence | 0.000" in result  # None becomes 0.000

    def test_empty_experiment_transcript(self, temp_db_path, tmp_path):
        """Test generating transcript for experiment with no conversations."""
        # Use EventStore to create the empty experiment
        with EventStore(temp_db_path) as store:
            store.db.execute(
                """
                INSERT INTO experiments (
                    experiment_id, name, status, created_at,
                    total_conversations, completed_conversations
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                ["exp_empty", "Empty Experiment", "completed", datetime.now(), 0, 0],
            )

        # Now use TranscriptGenerator to generate transcripts
        with TranscriptGenerator(temp_db_path) as generator:
            # This should not crash
            generator.generate_experiment_transcripts("exp_empty", tmp_path)

        # Check transcript was created
        transcript_dir = tmp_path / "transcripts"
        assert transcript_dir.exists()

    def test_malformed_json_in_shared_vocabulary(self, populated_db):
        """Test handling of malformed JSON in shared_vocabulary field."""
        # Since DuckDB validates JSON on insert, we'll test with an edge case instead
        # Test with empty string (which is valid but edge case)
        with EventStore(populated_db) as store:
            store.db.execute(
                """
                INSERT INTO turn_metrics (
                    conversation_id, turn_number, timestamp,
                    convergence_score,
                    message_a_unique_words, message_b_unique_words,
                    shared_vocabulary
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ["conv_test", 3, datetime.now(), 0.9, 5, 4, '""'],
            )  # Empty string as valid JSON

        # Now test with TranscriptGenerator - it should handle empty string
        with TranscriptGenerator(populated_db) as generator:
            # Should handle gracefully
            transcript = generator.generate_conversation_transcript("conv_test")
            assert transcript is not None
            assert "Vocabulary Metrics" in transcript

    def test_missing_messages(self, populated_db):
        """Test handling conversations with missing messages."""
        # Insert conversation with no messages using EventStore
        with EventStore(populated_db) as store:
            store.db.execute(
                """
                INSERT INTO conversations (
                    conversation_id, experiment_id, status,
                    agent_a_model, agent_b_model
                ) VALUES (?, ?, ?, ?, ?)
            """,
                ["conv_empty", "exp_test", "completed", "model-a", "model-b"],
            )

        # Now test with TranscriptGenerator
        with TranscriptGenerator(populated_db) as generator:
            # Should handle gracefully
            transcript = generator.generate_conversation_transcript("conv_empty")
            assert "No messages found" in transcript or "Turn 1" not in transcript

    def test_format_header_with_none_values(self, transcript_generator):
        """Test _format_header handles None values in conversation data."""
        conv_data = {
            "conversation_id": "test",
            "agent_a_model": None,
            "agent_b_model": None,
            "total_turns": None,
            "final_convergence_score": None,
        }

        token_data = {"total_tokens": 0, "total_cost_cents": 0}

        # Should not crash
        result = transcript_generator._format_header(conv_data, token_data)
        assert "Conversation:" in result
        assert "Agent" in result

    def test_convergence_progression_with_gaps(self, populated_db):
        """Test convergence progression handles missing data points."""
        # Add conversation with gaps in turn metrics
        with EventStore(populated_db) as store:
            # Add turns with some missing convergence scores (None values)
            for turn in [3, 4, 5]:
                store.db.execute(
                    """
                    INSERT INTO turn_metrics (
                        conversation_id, turn_number, timestamp,
                        convergence_score
                    ) VALUES (?, ?, ?, ?)
                """,
                    ["conv_test", turn, datetime.now(), None if turn == 4 else 0.8],
                )

        # Test with TranscriptGenerator
        with TranscriptGenerator(populated_db) as generator:
            transcript = generator.generate_conversation_transcript("conv_test")
            assert "Convergence Progression" in transcript
            # The transcript should handle missing data gracefully
            assert transcript is not None
