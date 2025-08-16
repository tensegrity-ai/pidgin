"""Generate markdown transcripts from database data."""

from pathlib import Path
from typing import Dict, List, Optional

from ..io.logger import get_logger
from .event_store import EventStore
from .transcript_formatter import TranscriptFormatter

logger = get_logger("transcript_generator")


class TranscriptGenerator:
    """Generate rich markdown transcripts from database data."""

    def __init__(
        self, event_store: EventStore, formatter: Optional[TranscriptFormatter] = None
    ):
        """Initialize with EventStore.

        Args:
            event_store: EventStore instance for database access
            formatter: Optional custom formatter instance
        """
        self.event_store = event_store
        self.formatter = formatter or TranscriptFormatter()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # No cleanup needed - EventStore manages its own connection
        pass

    def generate_experiment_transcripts(self, experiment_id: str, output_dir: Path):
        """Generate all transcripts for an experiment.

        Args:
            experiment_id: Experiment ID
            output_dir: Directory to write transcripts
        """
        # Get experiment data first
        exp_data = self._get_experiment_data(experiment_id)
        if not exp_data:
            logger.error(f"Experiment {experiment_id} not found in database")
            return

        # Generate experiment summary directly in output directory
        summary_path = output_dir / "transcript_summary.md"
        with open(summary_path, "w") as f:
            f.write(self.formatter.generate_experiment_summary(exp_data))
        logger.debug(f"Generated experiment summary: {summary_path}")

        # Get all conversations
        conversations = self._get_conversations(experiment_id)

        # Generate transcript for each conversation
        for conv in conversations:
            # Skip failed conversations
            if conv.get("status") == "failed":
                logger.debug(f"Skipping failed conversation: {conv['conversation_id']}")
                continue

            conv_id = conv["conversation_id"]
            transcript = self.generate_conversation_transcript(conv_id)

            # Write transcript directly in output directory
            transcript_path = output_dir / f"transcript_{conv_id}.md"
            with open(transcript_path, "w") as f:
                f.write(transcript)
            logger.debug(f"Generated transcript: {transcript_path}")

    def generate_conversation_transcript(self, conversation_id: str) -> str:
        """Generate markdown transcript for a single conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Markdown formatted transcript
        """
        # Get all data from database
        conv_data = self._get_conversation_data(conversation_id)
        turn_metrics = self._get_turn_metrics(conversation_id)
        messages = self._get_messages(conversation_id)
        token_data = self._get_token_usage(conversation_id)

        if not conv_data:
            return f"# Conversation {conversation_id} not found"

        # Build transcript sections
        sections = []

        # Header
        sections.append(self.formatter.format_header(conv_data, token_data))

        # Summary metrics table
        sections.append(
            self.formatter.format_summary_metrics(
                conv_data, token_data, len(turn_metrics)
            )
        )

        # Convergence progression
        sections.append(self.formatter.format_convergence_progression(turn_metrics))

        # Message length evolution
        sections.append(self.formatter.format_message_length_evolution(turn_metrics))

        # Vocabulary metrics
        sections.append(self.formatter.format_vocabulary_metrics(turn_metrics))

        # Response time analysis
        sections.append(self.formatter.format_response_times(turn_metrics))

        # Token usage by turn
        sections.append(self.formatter.format_token_usage(messages, token_data))

        # Full transcript
        sections.append(self.formatter.format_transcript(messages, conv_data))

        # Join all sections
        return "\n\n".join(sections)

    def _get_experiment_data(self, experiment_id: str) -> Optional[Dict]:
        """Get experiment data from database."""
        return self.event_store.get_experiment(experiment_id)

    def _get_conversations(self, experiment_id: str) -> List[Dict]:
        """Get all conversations for an experiment."""
        return self.event_store.get_experiment_conversations(experiment_id)

    def _get_conversation_data(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation data from database."""
        return self.event_store.get_conversation(conversation_id)

    def _get_turn_metrics(self, conversation_id: str) -> List[Dict]:
        """Get turn metrics from database."""
        return self.event_store.get_conversation_turn_metrics(conversation_id)

    def _get_messages(self, conversation_id: str) -> List[Dict]:
        """Get messages from database."""
        return self.event_store.get_conversation_messages(conversation_id)

    def _get_token_usage(self, conversation_id: str) -> Dict:
        """Get token usage summary."""
        return self.event_store.get_conversation_token_usage(conversation_id)
