"""Import metrics and turn data into database."""

import hashlib
import json
from typing import Any, Dict

import duckdb

from ...io.logger import get_logger

logger = get_logger("metrics_importer")


class MetricsImporter:
    """Handles metrics calculation and turn data import."""

    def __init__(self, db: duckdb.DuckDBPyConnection):
        """Initialize with database connection.

        Args:
            db: DuckDB connection
        """
        self.db = db

    def prepare_turn_row(
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
            "a_prompt_tokens": messages.get("agent_a", {}).get("prompt_tokens"),
            "a_completion_tokens": messages.get("agent_a", {}).get("completion_tokens"),
            "b_prompt_tokens": messages.get("agent_b", {}).get("prompt_tokens"),
            "b_completion_tokens": messages.get("agent_b", {}).get("completion_tokens"),
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

    def insert_turn(self, row: Dict[str, Any]) -> None:
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

    def insert_turn_metrics(
        self, conversation_id: str, turn_number: int, turn_data: Dict, metrics: Dict
    ) -> None:
        """Insert turn metrics into turn_metrics table for compatibility.

        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            turn_data: Turn data containing convergence score
            metrics: Calculated metrics
        """
        # Extract key metrics
        self.db.execute(
            """
            INSERT INTO turn_metrics (
                conversation_id, turn_number, timestamp,
                convergence_score,
                message_a_length, message_b_length,
                message_a_word_count, message_b_word_count,
                message_a_unique_words, message_b_unique_words,
                shared_vocabulary,
                message_a_response_time_ms, message_b_response_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                conversation_id,
                turn_number,
                turn_data["timestamp"],
                turn_data.get("convergence_score"),
                metrics.get("a_message_length"),
                metrics.get("b_message_length"),
                metrics.get("a_word_count"),
                metrics.get("b_word_count"),
                metrics.get("a_unique_words"),
                metrics.get("b_unique_words"),
                json.dumps(metrics.get("shared_vocabulary", [])),
                metrics.get("response_time_a"),
                metrics.get("response_time_b"),
            ],
        )
