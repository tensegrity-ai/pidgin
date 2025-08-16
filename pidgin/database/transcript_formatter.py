"""Formatting logic extracted from TranscriptGenerator."""

from typing import Dict, List

from ..io.logger import get_logger
from .formatters import (
    HeaderFormatter,
    MetricsFormatter,
    SummaryFormatter,
    TranscriptMessageFormatter,
)

logger = get_logger("transcript_formatter")


class TranscriptFormatter:
    """Handles all markdown formatting for transcripts.

    This class delegates to specialized formatters for different
    sections of the transcript, keeping the main class small and focused.
    """

    def __init__(self):
        """Initialize formatter components."""
        self.header = HeaderFormatter()
        self.metrics = MetricsFormatter()
        self.transcript = TranscriptMessageFormatter()
        self.summary = SummaryFormatter()

    # Delegate to header formatter
    def format_header(self, conv_data: Dict, token_data: Dict) -> str:
        """Format transcript header."""
        return self.header.format_header(conv_data, token_data)

    # Delegate to metrics formatter
    def format_summary_metrics(
        self, conv_data: Dict, token_data: Dict, num_turns: int
    ) -> str:
        """Format summary metrics table."""
        return self.metrics.format_summary_metrics(conv_data, token_data, num_turns)

    def format_convergence_progression(self, turn_metrics: List[Dict]) -> str:
        """Format convergence progression table."""
        return self.metrics.format_convergence_progression(turn_metrics)

    def format_message_length_evolution(self, turn_metrics: List[Dict]) -> str:
        """Format message length evolution table."""
        return self.metrics.format_message_length_evolution(turn_metrics)

    def format_vocabulary_metrics(self, turn_metrics: List[Dict]) -> str:
        """Format vocabulary metrics table."""
        return self.metrics.format_vocabulary_metrics(turn_metrics)

    def format_response_times(self, turn_metrics: List[Dict]) -> str:
        """Format response times table."""
        return self.metrics.format_response_times(turn_metrics)

    # Delegate to transcript formatter
    def format_token_usage(self, messages: List[Dict], token_data: Dict) -> str:
        """Format token usage breakdown."""
        return self.transcript.format_token_usage(messages, token_data)

    def format_transcript(self, messages: List[Dict], conv_data: Dict) -> str:
        """Format conversation transcript."""
        return self.transcript.format_transcript(messages, conv_data)

    # Delegate to summary formatter
    def generate_experiment_summary(self, exp_data: Dict) -> str:
        """Generate experiment summary markdown."""
        return self.summary.generate_experiment_summary(exp_data)
