"""New import service for wide-table conversation turns."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb

from ..core.events import (
    ConversationStartEvent,
    MessageCompleteEvent,
    TurnCompleteEvent,
)
from ..io.event_deserializer import EventDeserializer
from ..io.logger import get_logger
from ..metrics.flat_calculator import FlatMetricsCalculator
from .schema_manager import schema_manager

logger = get_logger("import_service")


@dataclass
class ImportResult:
    """Result of an import operation."""

    success: bool
    experiment_id: str
    turns_imported: int
    conversations_imported: int
    error: Optional[str] = None
    duration_seconds: float = 0.0


class ImportService:
    """Service for importing JSONL experiment data into DuckDB conversation_turns table."""

    def __init__(self, db_path: str):
        """Initialize with database path.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self.db = duckdb.connect(db_path)

        # Ensure schema exists
        schema_manager.ensure_schema(self.db, db_path)

        self.metrics_calculator = FlatMetricsCalculator()
        self.event_deserializer = EventDeserializer()

    def import_experiment_from_jsonl(self, exp_dir: Path) -> ImportResult:
        """Import experiment data from JSONL files into conversation_turns table.

        Args:
            exp_dir: Directory containing manifest.json and JSONL files

        Returns:
            ImportResult with success status and counts
        """
        start_time = datetime.now()

        try:
            # Load manifest
            manifest_path = exp_dir / "manifest.json"
            if not manifest_path.exists():
                return ImportResult(
                    success=False,
                    experiment_id=exp_dir.name,
                    turns_imported=0,
                    conversations_imported=0,
                    error="No manifest.json found",
                )

            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            experiment_id = manifest.get("experiment_id", exp_dir.name)

            # Find all JSONL files
            jsonl_files = list(exp_dir.glob("*.jsonl"))
            if not jsonl_files:
                return ImportResult(
                    success=False,
                    experiment_id=experiment_id,
                    turns_imported=0,
                    conversations_imported=0,
                    error="No JSONL files found",
                )

            # Process each JSONL file (typically one per conversation)
            total_turns = 0
            conversations_processed = 0

            self.db.begin()

            for jsonl_file in jsonl_files:
                turns_count = self._process_jsonl_file(
                    jsonl_file, experiment_id, manifest
                )
                total_turns += turns_count
                if turns_count > 0:
                    conversations_processed += 1

            self.db.commit()

            duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Successfully imported {experiment_id}: "
                f"{total_turns} turns, {conversations_processed} conversations"
            )

            return ImportResult(
                success=True,
                experiment_id=experiment_id,
                turns_imported=total_turns,
                conversations_imported=conversations_processed,
                duration_seconds=duration,
            )

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to import {exp_dir.name}: {e}")

            return ImportResult(
                success=False,
                experiment_id=exp_dir.name,
                turns_imported=0,
                conversations_imported=0,
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

    def _process_jsonl_file(
        self, jsonl_file: Path, experiment_id: str, manifest: Dict
    ) -> int:
        """Process a single JSONL file and extract turns.

        Args:
            jsonl_file: Path to JSONL file
            experiment_id: Experiment ID
            manifest: Experiment manifest

        Returns:
            Number of turns processed
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

        for conversation_id, conv_data in conversations.items():
            if not conv_data["turns"]:
                continue

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
                turn_row = self._prepare_turn_row(
                    experiment_id,
                    conversation_id,
                    turn_num,
                    turn_data,
                    conv_data["config"],
                    flat_metrics,
                    conv_data.get("messages", {}),
                )

                # Insert into database
                self._insert_turn(turn_row)
                turns_processed += 1

        return turns_processed

    def _prepare_turn_row(
        self,
        experiment_id: str,
        conversation_id: str,
        turn_number: int,
        turn_data: Dict,
        config: Dict,
        metrics: Dict,
        messages: Dict,
    ) -> Dict[str, Any]:
        """Prepare a complete row for the conversation_turns table.

        Args:
            experiment_id: Experiment ID
            conversation_id: Conversation ID
            turn_number: Turn number
            turn_data: Turn data from events
            config: Conversation configuration
            metrics: Flat metrics dictionary
            messages: Message metadata

        Returns:
            Dictionary ready for database insertion
        """
        # Calculate message hashes
        a_hash = hashlib.sha256(turn_data["agent_a_message"].encode()).hexdigest()
        b_hash = hashlib.sha256(turn_data["agent_b_message"].encode()).hexdigest()

        # Base row with identifiers and metadata
        row = {
            "experiment_id": experiment_id,
            "conversation_id": conversation_id,
            "turn_number": turn_number,
            "timestamp": turn_data["timestamp"],
            # Model and context
            "agent_a_model": config.get("agent_a_model", ""),
            "agent_b_model": config.get("agent_b_model", ""),
            "awareness_a": config.get("awareness_a"),
            "awareness_b": config.get("awareness_b"),
            "temperature_a": config.get("temperature_a"),
            "temperature_b": config.get("temperature_b"),
            "initial_prompt": config.get("initial_prompt"),
            # Message content and hashes
            "agent_a_message": turn_data["agent_a_message"],
            "agent_b_message": turn_data["agent_b_message"],
            "a_message_hash": a_hash,
            "b_message_hash": b_hash,
            # Token usage
            "a_prompt_tokens": None,  # TODO: extract from events if available
            "a_completion_tokens": messages.get("agent_a", {}).get("tokens_used"),
            "b_prompt_tokens": None,
            "b_completion_tokens": messages.get("agent_b", {}).get("tokens_used"),
            # Timing
            "response_time_a": messages.get("agent_a", {}).get("duration_ms"),
            "response_time_b": messages.get("agent_b", {}).get("duration_ms"),
            "processing_time_ms": None,
            "api_latency_a": None,
            "api_latency_b": None,
            "turn_duration_ms": None,
            "conversation_velocity": 0.0,
            "adaptation_rate": 0.0,
        }

        # Add all metrics to the row
        row.update(metrics)

        # Override overall_convergence with live calculated value if available
        if turn_data.get("convergence_score") is not None:
            row["overall_convergence"] = turn_data["convergence_score"]

        return row

    def _insert_turn(self, row: Dict[str, Any]) -> None:
        """Insert a turn row into the conversation_turns table.

        Args:
            row: Complete row dictionary
        """
        # Generate INSERT statement dynamically
        columns = list(row.keys())
        placeholders = ", ".join(["?" for _ in columns])
        column_names = ", ".join(columns)

        query = f"""
            INSERT INTO conversation_turns ({column_names})
            VALUES ({placeholders})
        """

        values = [row[col] for col in columns]

        try:
            self.db.execute(query, values)
        except Exception as e:
            logger.error(
                f"Failed to insert turn {row['conversation_id']}:{row['turn_number']}: {e}"
            )
            raise

    def import_all_pending(self, experiments_dir: Path) -> List[ImportResult]:
        """Import all experiments that have JSONL files but haven't been imported.

        Args:
            experiments_dir: Root directory containing experiment subdirectories

        Returns:
            List of ImportResults for each experiment
        """
        results = []

        if not experiments_dir.exists():
            logger.warning(f"Experiments directory {experiments_dir} does not exist")
            return results

        # Find all experiment directories
        for exp_dir in experiments_dir.iterdir():
            if not exp_dir.is_dir() or exp_dir.name.startswith("."):
                continue

            # Check if it has a manifest
            if not (exp_dir / "manifest.json").exists():
                continue

            # Check if already imported (look for data in conversation_turns)
            experiment_id = exp_dir.name
            existing_count = self.db.execute(
                "SELECT COUNT(*) FROM conversation_turns WHERE experiment_id = ?",
                [experiment_id],
            ).fetchone()[0]

            if existing_count > 0:
                logger.info(
                    f"Experiment {experiment_id} already imported ({existing_count} turns)"
                )
                continue

            # Import the experiment
            result = self.import_experiment_from_jsonl(exp_dir)
            results.append(result)

        return results

    def close(self):
        """Close the database connection."""
        if self.db:
            self.db.close()
