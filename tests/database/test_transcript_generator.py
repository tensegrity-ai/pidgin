"""Integration tests for TranscriptGenerator with real database."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from pidgin.database.event_store import EventStore
from pidgin.database.transcript_generator import TranscriptGenerator


class TestTranscriptGenerator:
    """Integration test suite for TranscriptGenerator."""

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

            # Insert conversation with some None values
            store.db.execute(
                """
                INSERT INTO conversations (
                    conversation_id, experiment_id, status,
                    agent_a_model, agent_b_model, total_turns,
                    final_convergence_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ["conv_test", "exp_test", "completed", "gpt-4", "claude-3", 2, None],
            )

            # Insert messages
            store.db.execute(
                """
                INSERT INTO messages (
                    conversation_id, turn_number, agent_id,
                    content, timestamp, token_count
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                ["conv_test", 1, "agent_a", "Hello", datetime.now(), None],
            )

            # Insert turn metrics with None values
            store.db.execute(
                """
                INSERT INTO turn_metrics (
                    conversation_id, turn_number, timestamp,
                    convergence_score, message_a_length, message_b_length
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                ["conv_test", 1, datetime.now(), None, 5, None],
            )

        return temp_db_path

    def test_generate_transcript_with_none_values(self, populated_db):
        """Test that transcript generation handles None values gracefully."""
        with EventStore(populated_db) as store:
            with TranscriptGenerator(store) as generator:
                transcript = generator.generate_conversation_transcript("conv_test")
                
                # Should generate transcript without errors
                assert transcript is not None
                assert "# Conversation:" in transcript
                assert "Hello" in transcript

    def test_missing_conversation(self, populated_db):
        """Test handling of missing conversation."""
        with EventStore(populated_db) as store:
            with TranscriptGenerator(store) as generator:
                transcript = generator.generate_conversation_transcript("missing_conv")
                
                # Should return error message
                assert "# Conversation missing_conv not found" in transcript

    def test_empty_experiment_transcript(self, populated_db, tmp_path):
        """Test generating transcripts for experiment with no conversations."""
        with EventStore(populated_db) as store:
            # Insert empty experiment
            store.db.execute(
                """
                INSERT INTO experiments (
                    experiment_id, name, status, created_at,
                    total_conversations, completed_conversations
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                ["empty_exp", "Empty Experiment", "completed", datetime.now(), 0, 0],
            )
            
            with TranscriptGenerator(store) as generator:
                generator.generate_experiment_transcripts("empty_exp", tmp_path)
                
                # Should create summary but no conversation files
                transcripts_dir = tmp_path / "transcripts"
                assert transcripts_dir.exists()
                
                summary_file = transcripts_dir / "summary.md"
                assert summary_file.exists()
                
                # No conversation files
                md_files = list(transcripts_dir.glob("conv_*.md"))
                assert len(md_files) == 0

    def test_malformed_json_in_shared_vocabulary(self, populated_db):
        """Test handling of null/empty shared_vocabulary field."""
        with EventStore(populated_db) as store:
            # Add turn metric with null shared vocabulary
            store.db.execute(
                """
                INSERT INTO turn_metrics (
                    conversation_id, turn_number, timestamp,
                    shared_vocabulary
                ) VALUES (?, ?, ?, ?)
            """,
                ["conv_test", 2, datetime.now(), None],
            )
            
            # Add another with empty JSON array
            store.db.execute(
                """
                INSERT INTO turn_metrics (
                    conversation_id, turn_number, timestamp,
                    shared_vocabulary
                ) VALUES (?, ?, ?, ?)
            """,
                ["conv_test", 3, datetime.now(), "[]"],
            )
            
            with TranscriptGenerator(store) as generator:
                # Should handle null/empty JSON gracefully
                transcript = generator.generate_conversation_transcript("conv_test")
                assert transcript is not None
                assert "## Vocabulary Metrics" in transcript

    def test_failed_conversation_skipped(self, populated_db, tmp_path):
        """Test that failed conversations are skipped in transcript generation."""
        with EventStore(populated_db) as store:
            # Add a failed conversation
            store.db.execute(
                """
                INSERT INTO conversations (
                    conversation_id, experiment_id, status,
                    agent_a_model, agent_b_model, total_turns
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                ["conv_failed", "exp_test", "failed", "gpt-4", "claude-3", 0],
            )
            
            with TranscriptGenerator(store) as generator:
                generator.generate_experiment_transcripts("exp_test", tmp_path)
                
                # Failed conversation should not have a transcript
                transcripts_dir = tmp_path / "transcripts"
                assert (transcripts_dir / "conv_test.md").exists()
                assert not (transcripts_dir / "conv_failed.md").exists()

    def test_convergence_progression_with_gaps(self, populated_db):
        """Test convergence progression with missing turns."""
        with EventStore(populated_db) as store:
            # Add metrics for turns 1, 3, 5 (gaps at 2, 4)
            for turn in [3, 5]:
                store.db.execute(
                    """
                    INSERT INTO turn_metrics (
                        conversation_id, turn_number, timestamp,
                        convergence_score
                    ) VALUES (?, ?, ?, ?)
                """,
                    ["conv_test", turn, datetime.now(), 0.5 + turn * 0.1],
                )
            
            with TranscriptGenerator(store) as generator:
                transcript = generator.generate_conversation_transcript("conv_test")
                
                # Should handle gaps gracefully
                assert "## Convergence Progression" in transcript
                assert transcript is not None