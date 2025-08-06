"""Process JSONL event files for import."""

from pathlib import Path
from typing import Dict, Tuple

from ...core.events import (
    ConversationStartEvent,
    MessageCompleteEvent,
    TurnCompleteEvent,
)
from ...io.event_deserializer import EventDeserializer
from ...io.logger import get_logger
from ...metrics.flat_calculator import FlatMetricsCalculator
from .conversation_importer import ConversationImporter
from .metrics_importer import MetricsImporter

logger = get_logger("event_processor")


class EventProcessor:
    """Process JSONL event files and extract conversation data."""

    def __init__(
        self,
        conversation_importer: ConversationImporter,
        metrics_importer: MetricsImporter,
    ):
        """Initialize with importers.

        Args:
            conversation_importer: Conversation data importer
            metrics_importer: Metrics and turn data importer
        """
        self.conversation_importer = conversation_importer
        self.metrics_importer = metrics_importer
        self.event_deserializer = EventDeserializer()
        self.metrics_calculator = FlatMetricsCalculator()

    def process_jsonl_file(
        self, jsonl_file: Path, experiment_id: str, manifest: Dict
    ) -> Tuple[int, int]:
        """Process a single JSONL file and extract turns.

        Args:
            jsonl_file: Path to JSONL file
            experiment_id: Experiment ID
            manifest: Experiment manifest

        Returns:
            Tuple of (turns_processed, conversations_created)
        """
        # Group events by conversation and turn
        conversations = {}

        # Read all events from the file
        for line_num, event in self.event_deserializer.read_jsonl_events(jsonl_file):
            if not event:
                continue

            conversation_id = event.conversation_id

            # Initialize conversation if not seen
            if conversation_id not in conversations:
                conversations[conversation_id] = {
                    "turns": {},
                    "config": {},
                    "messages": {},
                }

            conv = conversations[conversation_id]

            # Process different event types
            if isinstance(event, ConversationStartEvent):
                conv["config"] = {
                    "agent_a_model": event.agent_a_model,
                    "agent_b_model": event.agent_b_model,
                    "temperature_a": event.temperature_a,
                    "temperature_b": event.temperature_b,
                    "initial_prompt": event.initial_prompt,
                    "awareness_a": getattr(event, "awareness_a", None),
                    "awareness_b": getattr(event, "awareness_b", None),
                }

            elif isinstance(event, TurnCompleteEvent):
                turn_num = event.turn_number
                conv["turns"][turn_num] = {
                    "timestamp": event.timestamp,
                    "convergence_score": event.convergence_score,
                    "agent_a_message": event.turn.agent_a_message.content,
                    "agent_b_message": event.turn.agent_b_message.content,
                }

            elif isinstance(event, MessageCompleteEvent):
                # Store message for token counting
                conv["messages"][event.agent_id] = {
                    "tokens_used": event.tokens_used,
                    "duration_ms": event.duration_ms,
                }

        # Calculate metrics for each conversation
        turns_processed = 0
        conversations_created = 0

        for conversation_id, conv_data in conversations.items():
            if not conv_data["turns"]:
                continue

            # Create conversation record if it doesn't exist
            if self.conversation_importer.ensure_conversation_exists(
                experiment_id, conversation_id, conv_data
            ):
                conversations_created += 1

            # Reset metrics calculator for this conversation
            self.metrics_calculator = FlatMetricsCalculator()

            # Process turns in order
            for turn_num in sorted(conv_data["turns"].keys()):
                turn_data = conv_data["turns"][turn_num]

                # Calculate metrics
                flat_metrics = self.metrics_calculator.calculate_turn_metrics(
                    turn_num, turn_data["agent_a_message"], turn_data["agent_b_message"]
                )

                # Prepare data for insertion
                turn_row = self.metrics_importer.prepare_turn_row(
                    experiment_id,
                    conversation_id,
                    turn_num,
                    turn_data,
                    conv_data["config"],
                    flat_metrics,
                    conv_data.get("messages", {}),
                )

                # Insert into database
                self.metrics_importer.insert_turn(turn_row)

                # Also populate messages and turn_metrics tables for transcript generation
                self.conversation_importer.insert_messages(
                    conversation_id, turn_num, turn_data, conv_data.get("messages", {})
                )
                self.metrics_importer.insert_turn_metrics(
                    conversation_id, turn_num, turn_data, flat_metrics
                )

                turns_processed += 1

        return turns_processed, conversations_created