"""Tests for transcript generator."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from pidgin.database.transcript_generator import TranscriptGenerator


class TestTranscriptGenerator:
    """Test transcript generation functionality."""

    @pytest.fixture
    def mock_db_connection(self):
        """Create a mock database connection."""
        mock_conn = MagicMock()
        mock_conn.description = []
        mock_conn.execute.return_value = mock_conn
        mock_conn.fetchone.return_value = None
        mock_conn.fetchall.return_value = []
        return mock_conn

    @pytest.fixture
    def generator(self, tmp_path, mock_db_connection):
        """Create a TranscriptGenerator instance with mocked connection."""
        db_path = tmp_path / "test.db"

        # Don't patch duckdb globally, just override the connection
        gen = TranscriptGenerator.__new__(TranscriptGenerator)
        gen.db_path = db_path
        gen.conn = mock_db_connection
        return gen

    def test_format_summary_metrics_with_none_values(self, generator):
        """Test that format_summary_metrics handles None values properly."""
        # This was the original error case
        conv_data = {
            "total_turns": 5,
            "final_convergence_score": None,  # This was causing the TypeError
            "convergence_reason": "max_turns",
        }
        token_data = {"total_tokens": 1000, "total_cost_cents": 50}

        # Should not raise TypeError
        result = generator._format_summary_metrics(conv_data, token_data, 5)

        assert "| Final Convergence | 0.000 |" in result
        assert "| Total Turns | 5 |" in result
        assert "| Total Cost | $0.50 |" in result

    def test_format_summary_metrics_with_missing_values(self, generator):
        """Test handling of missing values in summary metrics."""
        conv_data = {}  # Empty dict
        token_data = {"total_tokens": 500, "total_cost_cents": None}  # Missing cost

        result = generator._format_summary_metrics(conv_data, token_data, 3)

        # Should use defaults
        assert "| Final Convergence | 0.000 |" in result
        assert "| Total Turns | 3 |" in result
        assert "| Total Cost | $0.00 |" in result
        assert "| Ended Due To | max_turns |" in result

    def test_format_header(self, generator):
        """Test conversation header formatting."""
        conv_data = {
            "conversation_id": "test_conv_123",
            "experiment_id": "exp_456",
            "agent_a_model": "gpt-4",
            "agent_b_model": "claude-3",
            "started_at": "2025-01-06T12:00:00+00:00",
            "duration_ms": 5000,
        }
        token_data = {"total_tokens": 100, "total_cost_cents": 10}

        result = generator._format_header(conv_data, token_data)

        assert "gpt-4 ↔ claude-3" in result
        assert "exp_456" in result
        assert "0m 5s" in result  # Duration

    def test_format_header_missing_keys(self, generator):
        """Test header formatting with missing keys."""
        conv_data = {}  # Missing all keys
        token_data = {}

        # Should not raise KeyError
        result = generator._format_header(conv_data, token_data)

        assert "Unknown ↔ Unknown" in result
        assert "N/A" in result  # Missing experiment_id

    def test_format_convergence_progression_with_none(self, generator):
        """Test convergence progression with None values."""
        turn_metrics = [
            {"turn_number": 1, "convergence_score": 0.1},
            {"turn_number": 5, "convergence_score": None},  # None value
            {"turn_number": 10, "convergence_score": 0.5},
            {"turn_number": 15, "convergence_score": 0.7},
        ]

        result = generator._format_convergence_progression(turn_metrics)

        assert "## Convergence Progression" in result
        # Should handle None values gracefully
        assert "| Turn |" in result
        assert "| Score |" in result
        assert "| Trend |" in result

    def test_format_convergence_progression_empty(self, generator):
        """Test convergence progression with no data."""
        result = generator._format_convergence_progression([])

        assert "## Convergence Progression" in result
        assert "No data available" in result

    def test_format_message_length_evolution(self, generator):
        """Test message length evolution formatting."""
        turn_metrics = [
            {
                "turn_number": 1,
                "message_a_length": 50,
                "message_b_length": 45,
                "message_a_word_count": 10,
                "message_b_word_count": 9,
            }
        ]

        result = generator._format_message_length_evolution(turn_metrics)

        assert "## Message Length Evolution" in result
        assert "50" in result
        assert "45" in result

    def test_format_vocabulary_metrics(self, generator):
        """Test vocabulary metrics formatting."""
        turn_metrics = [
            {
                "turn_number": 5,
                "message_a_unique_words": 50,
                "message_b_unique_words": 45,
                "shared_vocabulary": '["hello", "world"]',
            }
        ]

        result = generator._format_vocabulary_metrics(turn_metrics)

        assert "## Vocabulary Metrics" in result
        assert "50" in result
        assert "45" in result
        assert "2" in result  # shared count

    def test_format_vocabulary_metrics_invalid_json(self, generator):
        """Test vocabulary metrics with invalid JSON."""
        turn_metrics = [
            {
                "turn_number": 5,
                "message_a_unique_words": 10,
                "message_b_unique_words": 8,
                "shared_vocabulary": None,  # Missing/None shared vocabulary
            }
        ]

        result = generator._format_vocabulary_metrics(turn_metrics)

        assert "## Vocabulary Metrics" in result
        # Should handle None shared vocabulary
        assert "10" in result
        assert "8" in result
        assert "0" in result  # 0 shared words

    def test_format_response_times(self, generator):
        """Test response time formatting."""
        turn_metrics = [
            {
                "turn_number": 1,
                "message_a_response_time_ms": 500,
                "message_b_response_time_ms": 600,
            },
            {
                "turn_number": 2,
                "message_a_response_time_ms": None,  # Missing data
                "message_b_response_time_ms": 700,
            },
        ]

        result = generator._format_response_times(turn_metrics)

        assert "## Response Time Analysis" in result
        assert "500" in result
        assert "ms" in result

    def test_format_token_usage_safe_cost(self, generator):
        """Test token usage handles zero tokens safely."""
        messages = [
            {"turn_number": 1, "agent_id": "agent_a", "token_count": None},
            {"turn_number": 1, "agent_id": "agent_b", "token_count": 50},
        ]
        token_data = {"total_tokens": 0, "total_cost_cents": 0}  # Zero tokens

        result = generator._format_token_usage(messages, token_data)

        assert "## Token Usage" in result
        assert "$0.000" in result  # Should not crash

    def test_format_transcript_basic(self, generator):
        """Test basic transcript formatting."""
        messages = [
            {
                "turn_number": 1,
                "agent_id": "agent_a",
                "content": "Hello!",
                "timestamp": datetime(2025, 1, 6, 12, 0, 0, tzinfo=timezone.utc),
            },
            {
                "turn_number": 1,
                "agent_id": "agent_b",
                "content": "Hi there!",
                "timestamp": datetime(2025, 1, 6, 12, 0, 5, tzinfo=timezone.utc),
            },
        ]
        conv_data = {}

        result = generator._format_transcript(messages, conv_data)

        assert "## Transcript" in result
        assert "**Agent A**" in result  # Uses default agent names
        assert "Hello!" in result
        assert "**Agent B**" in result  # Uses default agent names
        assert "Hi there!" in result

    def test_format_transcript_with_none_display_name(self, generator):
        """Test transcript formatting with missing agent names in conv_data."""
        messages = [
            {
                "turn_number": 1,
                "agent_id": "agent_a",
                "content": "Test message",
                "timestamp": datetime.now(timezone.utc),
            }
        ]
        conv_data = {}  # No agent names in conv_data

        result = generator._format_transcript(messages, conv_data)

        assert "**Agent A**" in result  # Should use default
        assert "Test message" in result

    def test_generate_conversation_transcript_missing_data(self, generator):
        """Test transcript generation with missing conversation."""
        # Mock the database queries to return None/empty
        generator._get_conversation_data = Mock(return_value=None)

        transcript = generator.generate_conversation_transcript("missing_123")

        assert transcript == "# Conversation missing_123 not found"

    def test_generate_conversation_transcript_full(self, generator):
        """Test full transcript generation."""
        # Mock all the database query methods
        conv_data = {
            "conversation_id": "test_123",
            "experiment_id": "exp_456",
            "agent_a_model": "gpt-4",
            "agent_b_model": "claude-3",
            "initial_prompt": "Test conversation",
            "total_turns": 2,
            "final_convergence_score": 0.8,
            "convergence_reason": "high_convergence",
            "started_at": "2025-01-06T12:00:00",
            "duration_ms": 5000,
        }

        generator._get_conversation_data = Mock(return_value=conv_data)
        generator._get_messages = Mock(
            return_value=[
                {
                    "turn_number": 1,
                    "agent_id": "agent_a",
                    "display_name": "GPT",
                    "content": "Hello!",
                    "timestamp": datetime.now(timezone.utc),
                    "token_count": 10,
                }
            ]
        )
        generator._get_turn_metrics = Mock(
            return_value=[
                {
                    "turn_number": 1,
                    "convergence_score": 0.5,
                    "message_a_unique_words": 10,
                    "message_b_unique_words": 8,
                    "message_a_length": 100,
                    "message_b_length": 95,
                    "message_a_word_count": 20,
                    "message_b_word_count": 18,
                    "message_a_response_time_ms": 500,
                    "message_b_response_time_ms": 600,
                    "shared_vocabulary": '["hello"]',
                }
            ]
        )
        generator._get_token_usage = Mock(
            return_value={"total_tokens": 15, "total_cost_cents": 1}
        )

        transcript = generator.generate_conversation_transcript("test_123")

        # Verify transcript contains expected sections
        assert "gpt-4 ↔ claude-3" in transcript
        assert "## Summary Metrics" in transcript
        assert "| Final Convergence | 0.800 |" in transcript
        assert "## Convergence Progression" in transcript

    def test_edge_cases(self, generator):
        """Test various edge cases."""
        # Empty token data - must have required keys
        token_data = {"total_tokens": 0, "total_cost_cents": 0}
        result = generator._format_summary_metrics({}, token_data, 0)
        assert "| Total Tokens | 0 |" in result

        # Very large numbers
        token_data = {"total_tokens": 1000000, "total_cost_cents": 50000}
        result = generator._format_summary_metrics({}, token_data, 0)
        assert "1,000,000" in result  # Proper formatting
        assert "$500.00" in result

    def test_generate_experiment_transcripts(self, generator, tmp_path):
        """Test experiment transcript generation."""
        exp_dir = tmp_path / "experiment_123"
        exp_dir.mkdir()

        # Mock experiment data
        generator._get_experiment_data = Mock(
            return_value={
                "experiment_id": "exp_123",
                "name": "Test Experiment",
                "status": "completed",
                "created_at": "2025-01-06T12:00:00",
                "total_conversations": 1,
                "completed_conversations": 1,
                "failed_conversations": 0,
                "config": "{}",
            }
        )
        generator._get_conversations = Mock(
            return_value=[{"conversation_id": "conv_1"}]
        )

        # Mock conversation transcript generation
        with patch.object(
            generator,
            "generate_conversation_transcript",
            return_value="# Test Transcript",
        ):
            generator.generate_experiment_transcripts("exp_123", exp_dir)

            # Verify transcript directory was created
            transcript_dir = exp_dir / "transcripts"
            assert transcript_dir.exists()

            # Verify files were written
            assert (transcript_dir / "conv_1.md").exists()
            assert (transcript_dir / "summary.md").exists()

    def test_context_manager(self, generator):
        """Test context manager functionality."""
        with patch.object(generator.conn, "close") as mock_close:
            with generator:
                pass
            mock_close.assert_called_once()
