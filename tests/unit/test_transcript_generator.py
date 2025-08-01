"""Tests for transcript generator with refactored code."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from pidgin.database.transcript_generator import TranscriptGenerator
from pidgin.database.transcript_formatter import TranscriptFormatter
from pidgin.database.event_store import EventStore


class TestTranscriptGenerator:
    """Test transcript generation functionality."""

    @pytest.fixture
    def mock_event_store(self):
        """Create a mock EventStore."""
        mock = MagicMock(spec=EventStore)
        return mock

    @pytest.fixture
    def generator(self, mock_event_store):
        """Create a TranscriptGenerator instance with mocked EventStore."""
        return TranscriptGenerator(mock_event_store)

    def test_init(self, mock_event_store):
        """Test TranscriptGenerator initialization."""
        # Default formatter
        gen = TranscriptGenerator(mock_event_store)
        assert gen.event_store == mock_event_store
        assert isinstance(gen.formatter, TranscriptFormatter)
        
        # Custom formatter
        custom_formatter = Mock(spec=TranscriptFormatter)
        gen = TranscriptGenerator(mock_event_store, formatter=custom_formatter)
        assert gen.formatter == custom_formatter

    def test_context_manager(self, generator):
        """Test context manager support."""
        with generator as gen:
            assert gen == generator
        # Context manager doesn't need to do anything special

    def test_generate_conversation_transcript_missing_data(self, generator):
        """Test transcript generation with missing data."""
        # Mock missing conversation
        generator.event_store.get_conversation.return_value = None
        
        transcript = generator.generate_conversation_transcript("missing_conv")
        
        # Should return error message
        assert "# Conversation missing_conv not found" in transcript

    def test_generate_conversation_transcript_full(self, generator):
        """Test full transcript generation."""
        # Mock all the data retrieval methods
        generator.event_store.get_conversation.return_value = {
            "conversation_id": "test_conv",
            "agent_a_model": "gpt-4",
            "agent_b_model": "claude-3",
            "total_turns": 2,
            "final_convergence_score": 0.85,
            "started_at": datetime.now(),
            "duration_ms": 120000,
        }
        
        generator.event_store.get_conversation_turn_metrics.return_value = [
            {
                "turn_number": 1,
                "convergence_score": 0.5,
                "message_a_length": 50,
                "message_b_length": 45,
            }
        ]
        
        generator.event_store.get_conversation_messages.return_value = [
            {
                "turn_number": 1,
                "agent_id": "agent_a",
                "content": "Hello",
                "token_count": 2,
            },
            {
                "turn_number": 1,
                "agent_id": "agent_b",
                "content": "Hi there",
                "token_count": 3,
            },
        ]
        
        generator.event_store.get_conversation_token_usage.return_value = {
            "total_tokens": 5,
            "total_cost_cents": 10,
        }
        
        # Mock formatter to return predictable output
        generator.formatter = Mock()
        generator.formatter.format_header.return_value = "# Header"
        generator.formatter.format_summary_metrics.return_value = "## Summary"
        generator.formatter.format_convergence_progression.return_value = "## Convergence"
        generator.formatter.format_message_length_evolution.return_value = "## Length"
        generator.formatter.format_vocabulary_metrics.return_value = "## Vocabulary"
        generator.formatter.format_response_times.return_value = "## Response"
        generator.formatter.format_token_usage.return_value = "## Tokens"
        generator.formatter.format_transcript.return_value = "## Transcript"
        
        transcript = generator.generate_conversation_transcript("test_conv")
        
        # Verify all sections are included
        assert "# Header" in transcript
        assert "## Summary" in transcript
        assert "## Convergence" in transcript
        assert "## Transcript" in transcript
        
        # Verify formatter was called with correct data
        generator.formatter.format_header.assert_called_once()
        generator.formatter.format_transcript.assert_called_once()

    def test_generate_experiment_transcripts(self, generator, tmp_path):
        """Test generating transcripts for an entire experiment."""
        # Mock experiment data
        generator.event_store.get_experiment.return_value = {
            "experiment_id": "test_exp",
            "name": "Test Experiment",
            "status": "completed",
        }
        
        # Mock conversations - one completed, one failed
        generator.event_store.get_experiment_conversations.return_value = [
            {"conversation_id": "conv1", "status": "completed"},
            {"conversation_id": "conv2", "status": "failed"},
        ]
        
        # Mock the generate_conversation_transcript to return simple content
        generator.generate_conversation_transcript = Mock(return_value="# Test Transcript")
        
        # Mock the formatter for summary
        generator.formatter.generate_experiment_summary = Mock(return_value="# Summary")
        
        # Generate transcripts
        generator.generate_experiment_transcripts("test_exp", tmp_path)
        
        # Check files were created
        transcripts_dir = tmp_path / "transcripts"
        assert transcripts_dir.exists()
        
        summary_file = transcripts_dir / "summary.md"
        assert summary_file.exists()
        assert summary_file.read_text() == "# Summary"
        
        # Only completed conversation should have transcript
        conv1_file = transcripts_dir / "conv1.md"
        assert conv1_file.exists()
        
        conv2_file = transcripts_dir / "conv2.md"
        assert not conv2_file.exists()  # Failed conversations are skipped
        
        # Verify methods were called correctly
        generator.formatter.generate_experiment_summary.assert_called_once()
        generator.generate_conversation_transcript.assert_called_once_with("conv1")

    def test_generate_experiment_transcripts_not_found(self, generator, tmp_path):
        """Test generating transcripts for non-existent experiment."""
        # Mock missing experiment
        generator.event_store.get_experiment.return_value = None
        
        # Generate transcripts
        generator.generate_experiment_transcripts("missing_exp", tmp_path)
        
        # No directory should be created
        transcripts_dir = tmp_path / "transcripts"
        assert not transcripts_dir.exists()