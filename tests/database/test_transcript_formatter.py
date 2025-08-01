"""Tests for TranscriptFormatter class extracted from TranscriptGenerator."""

import json
from datetime import datetime
from typing import Dict, List

import pytest

from pidgin.database.transcript_formatter import TranscriptFormatter


class TestTranscriptFormatter:
    """Test suite for TranscriptFormatter."""

    @pytest.fixture
    def formatter(self):
        """Create a TranscriptFormatter instance."""
        return TranscriptFormatter()

    def test_format_header_basic(self, formatter):
        """Test basic header formatting."""
        conv_data = {
            "agent_a_model": "gpt-4",
            "agent_b_model": "claude-3",
            "agent_a_chosen_name": "Alice",
            "agent_b_chosen_name": "Bob",
            "experiment_id": "exp123",
            "started_at": "2024-01-01T10:00:00Z",
            "duration_ms": 125000,
        }
        token_data = {"total_tokens": 1000, "total_cost_cents": 50}

        result = formatter.format_header(conv_data, token_data)

        assert "# Conversation: gpt-4 ↔ claude-3" in result
        assert "**Experiment**: exp123" in result
        assert "**Date**: 2024-01-01T10:00:00Z" in result
        assert "**Duration**: 2m 5s" in result
        assert "**Agents**: Alice ↔ Bob" in result

    def test_format_header_with_none_values(self, formatter):
        """Test header formatting with None values."""
        conv_data = {
            "agent_a_model": None,
            "agent_b_model": None,
            "duration_ms": None,
            "started_at": None,
        }
        token_data = {}

        result = formatter.format_header(conv_data, token_data)

        assert "# Conversation: Unknown ↔ Unknown" in result
        assert "**Duration**: N/A" in result
        assert "**Date**: N/A" in result

    def test_format_summary_metrics(self, formatter):
        """Test summary metrics formatting."""
        conv_data = {
            "total_turns": 10,
            "final_convergence_score": 0.856,
            "convergence_reason": "threshold_reached",
        }
        token_data = {
            "total_tokens": 5000,
            "total_cost_cents": 250,
        }
        num_turns = 10

        result = formatter.format_summary_metrics(conv_data, token_data, num_turns)

        assert "## Summary Metrics" in result
        assert "| Total Turns | 10 |" in result
        assert "| Final Convergence | 0.856 |" in result
        assert "| Total Messages | 20 |" in result
        assert "| Total Tokens | 5,000 |" in result
        assert "| Total Cost | $2.50 |" in result
        assert "| Ended Due To | threshold_reached |" in result

    def test_format_summary_metrics_with_none_convergence(self, formatter):
        """Test summary metrics with None convergence score."""
        conv_data = {
            "total_turns": 5,
            "final_convergence_score": None,
            "convergence_reason": None,
        }
        token_data = {"total_tokens": 100, "total_cost_cents": 0}
        num_turns = 5

        result = formatter.format_summary_metrics(conv_data, token_data, num_turns)

        assert "| Final Convergence | 0.000 |" in result
        assert "| Ended Due To | max_turns |" in result

    def test_format_convergence_progression(self, formatter):
        """Test convergence progression table formatting."""
        turn_metrics = [
            {"turn_number": 1, "convergence_score": 0.2},
            {"turn_number": 2, "convergence_score": 0.3},
            {"turn_number": 5, "convergence_score": 0.5},
            {"turn_number": 10, "convergence_score": 0.7},
            {"turn_number": 15, "convergence_score": 0.85},
            {"turn_number": 20, "convergence_score": 0.9},
            {"turn_number": 25, "convergence_score": 0.95},
        ]

        result = formatter.format_convergence_progression(turn_metrics)

        assert "## Convergence Progression" in result
        assert "| Turn | 1 | 5 | 10 | 15 | 20 | 25 |" in result
        assert "| Score |" in result
        assert "| Trend |" in result
        assert "0.200" in result  # Turn 1 score
        assert "0.950" in result  # Turn 25 score
        assert "↑" in result  # Upward trend

    def test_format_convergence_progression_empty(self, formatter):
        """Test convergence progression with no data."""
        result = formatter.format_convergence_progression([])

        assert "## Convergence Progression" in result
        assert "No data available" in result

    def test_format_message_length_evolution(self, formatter):
        """Test message length evolution formatting."""
        turn_metrics = [
            {
                "turn_number": 1,
                "message_a_length": 50,
                "message_b_length": 45,
                "message_a_word_count": 10,
                "message_b_word_count": 9,
            },
            {
                "turn_number": 5,
                "message_a_length": 100,
                "message_b_length": 95,
                "message_a_word_count": 20,
                "message_b_word_count": 19,
            },
            {
                "turn_number": 10,
                "message_a_length": 150,
                "message_b_length": 145,
                "message_a_word_count": 30,
                "message_b_word_count": 29,
            },
        ]

        result = formatter.format_message_length_evolution(turn_metrics)

        assert "## Message Length Evolution" in result
        assert "| Metric | Turns 1-5 | Turns 6-10 |" in result
        assert "| Avg Chars (A) |" in result
        assert "| Avg Words (B) |" in result

    def test_format_vocabulary_metrics(self, formatter):
        """Test vocabulary metrics formatting."""
        turn_metrics = [
            {
                "turn_number": 5,
                "message_a_unique_words": 50,
                "message_b_unique_words": 45,
                "shared_vocabulary": '["the", "is", "are", "in", "of"]',
            },
            {
                "turn_number": 10,
                "message_a_unique_words": 100,
                "message_b_unique_words": 95,
                "shared_vocabulary": json.dumps(["word"] * 20),
            },
        ]

        result = formatter.format_vocabulary_metrics(turn_metrics)

        assert "## Vocabulary Metrics" in result
        assert "| Turn Range | Unique Words (A) | Unique Words (B) |" in result
        assert "| 1-5 | 50 | 45 | 5 |" in result
        assert "| 6-10 | 100 | 95 | 20 |" in result

    def test_format_vocabulary_metrics_with_none(self, formatter):
        """Test vocabulary metrics with None values."""
        turn_metrics = [
            {
                "turn_number": 1,
                "message_a_unique_words": None,
                "message_b_unique_words": None,
                "shared_vocabulary": None,
            },
            {
                "turn_number": 5,
                "message_a_unique_words": 30,
                "message_b_unique_words": 25,
                "shared_vocabulary": '["test"]',
            },
        ]

        result = formatter.format_vocabulary_metrics(turn_metrics)

        assert "| 1-5 |" in result
        assert "0.0%" not in result or "3.3%" in result  # Should handle division by zero

    def test_format_response_times(self, formatter):
        """Test response time analysis formatting."""
        turn_metrics = [
            {
                "turn_number": 1,
                "message_a_response_time_ms": 1000,
                "message_b_response_time_ms": 1200,
            },
            {
                "turn_number": 5,
                "message_a_response_time_ms": 800,
                "message_b_response_time_ms": 900,
            },
            {
                "turn_number": 10,
                "message_a_response_time_ms": None,
                "message_b_response_time_ms": 1100,
            },
        ]

        result = formatter.format_response_times(turn_metrics)

        assert "## Response Time Analysis" in result
        assert "| Turn Range | Avg Response Time (A) | Avg Response Time (B) |" in result
        assert "900 ms" in result  # Average of 1000 and 800

    def test_format_token_usage(self, formatter):
        """Test token usage formatting."""
        messages = [
            {"turn_number": 1, "agent_id": "agent_a", "token_count": 50},
            {"turn_number": 1, "agent_id": "agent_b", "token_count": 45},
            {"turn_number": 5, "agent_id": "agent_a", "token_count": 100},
            {"turn_number": 5, "agent_id": "agent_b", "token_count": 95},
        ]
        token_data = {"total_tokens": 1000, "total_cost_cents": 50}

        result = formatter.format_token_usage(messages, token_data)

        assert "## Token Usage by Turn" in result
        assert "| Turn | Tokens (A) | Tokens (B) | Cumulative | Cost |" in result
        assert "| 1 | 50 | 45 | 95 |" in result
        assert "| 5 | 100 | 95 | 290 |" in result

    def test_format_transcript(self, formatter):
        """Test full transcript formatting."""
        messages = [
            {
                "turn_number": 1,
                "agent_id": "agent_a",
                "content": "Hello, how are you?",
            },
            {
                "turn_number": 1,
                "agent_id": "agent_b",
                "content": "I'm doing well, thanks!",
            },
            {
                "turn_number": 2,
                "agent_id": "agent_a",
                "content": "That's great to hear.",
            },
            {
                "turn_number": 2,
                "agent_id": "agent_b",
                "content": "How about you?",
            },
        ]
        conv_data = {
            "agent_a_chosen_name": "Alice",
            "agent_b_chosen_name": "Bob",
            "agent_a_model": "gpt-4",
            "agent_b_model": "claude-3",
        }

        result = formatter.format_transcript(messages, conv_data)

        assert "## Transcript" in result
        assert "### Turn 1" in result
        assert "### Turn 2" in result
        assert "**Alice**: Hello, how are you?" in result
        assert "**Bob**: I'm doing well, thanks!" in result

    def test_format_transcript_empty(self, formatter):
        """Test transcript formatting with no messages."""
        result = formatter.format_transcript([], {})

        assert "## Transcript" in result
        assert "No messages found" in result

    def test_generate_experiment_summary(self, formatter):
        """Test experiment summary generation."""
        exp_data = {
            "name": "Test Experiment",
            "experiment_id": "exp123",
            "status": "completed",
            "created_at": "2024-01-01T10:00:00Z",
            "total_conversations": 10,
            "completed_conversations": 8,
            "failed_conversations": 2,
            "config": json.dumps({
                "agent_a_model": "gpt-4",
                "agent_b_model": "claude-3",
                "max_turns": 25,
                "convergence_threshold": 0.8,
            }),
        }

        result = formatter.generate_experiment_summary(exp_data)

        assert "# Experiment: Test Experiment" in result
        assert "**ID**: exp123" in result
        assert "**Status**: completed" in result
        assert "- Total Conversations: 10" in result
        assert "- Completed: 8" in result
        assert "- Failed: 2" in result
        assert "- Agent A: gpt-4" in result
        assert "- Agent B: claude-3" in result
        assert "- Max Turns: 25" in result
        assert "- Convergence Threshold: 0.8" in result

    def test_format_convergence_trend_calculation(self, formatter):
        """Test convergence trend calculation logic."""
        turn_metrics = [
            {"turn_number": 1, "convergence_score": 0.2},
            {"turn_number": 5, "convergence_score": 0.2},  # No change
            {"turn_number": 10, "convergence_score": 0.4},  # Small increase
            {"turn_number": 15, "convergence_score": 0.7},  # Large increase
            {"turn_number": 20, "convergence_score": 0.65},  # Decrease
        ]

        result = formatter.format_convergence_progression(turn_metrics)

        # Check trend symbols
        assert "→" in result  # No change trend
        assert "↑" in result  # Small increase
        assert "↑↑" in result  # Large increase
        assert "↓" in result  # Decrease

    def test_format_with_malformed_json(self, formatter):
        """Test handling of malformed JSON in shared vocabulary."""
        turn_metrics = [
            {
                "turn_number": 1,
                "message_a_unique_words": 10,
                "message_b_unique_words": 8,
                "shared_vocabulary": "not valid json",  # This will trigger the warning
            }
        ]

        # Should not crash, just log warning
        result = formatter.format_vocabulary_metrics(turn_metrics)
        assert "## Vocabulary Metrics" in result
        assert "| 1-5 | 10 | 8 | 0 |" in result  # Should default to 0 shared

    def test_format_header_datetime_object(self, formatter):
        """Test header formatting with datetime object instead of string."""
        conv_data = {
            "agent_a_model": "gpt-4",
            "agent_b_model": "claude-3",
            "started_at": datetime(2024, 1, 1, 10, 0, 0),
            "duration_ms": 60000,
        }
        token_data = {}

        result = formatter.format_header(conv_data, token_data)

        assert "**Date**: 2024-01-01 10:00:00 UTC" in result

    def test_edge_cases_in_calculations(self, formatter):
        """Test edge cases in various calculations."""
        # Test with zero tokens (avoid division by zero)
        messages = [
            {"turn_number": 1, "agent_id": "agent_a", "token_count": 10},
        ]
        token_data = {"total_tokens": 0, "total_cost_cents": 0}

        result = formatter.format_token_usage(messages, token_data)
        assert "| 1 | 10 | 0 | 10 | $0.000 |" in result

        # Test empty turn ranges
        turn_metrics = [
            {"turn_number": 30, "convergence_score": 0.9},  # Beyond sample range
        ]
        
        result = formatter.format_convergence_progression(turn_metrics)
        assert "| Score | - | - | - | - | - | - |" in result  # All dashes for missing data