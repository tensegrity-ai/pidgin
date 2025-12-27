"""Import conversation-level data into database."""

import json
from datetime import datetime
from typing import Dict

import duckdb

from ...io.logger import get_logger

logger = get_logger("conversation_importer")


class ConversationImporter:
    """Handles importing conversation-level data."""

    def __init__(self, db: duckdb.DuckDBPyConnection):
        """Initialize with database connection.

        Args:
            db: DuckDB connection
        """
        self.db = db

    def ensure_experiment_exists(self, experiment_id: str, manifest: Dict) -> None:
        """Ensure experiment exists in database before importing turns.

        Args:
            experiment_id: Experiment ID
            manifest: Manifest data containing experiment config
        """
        # Check if experiment already exists
        result = self.db.execute(
            "SELECT experiment_id FROM experiments WHERE experiment_id = ?",
            [experiment_id],
        ).fetchone()

        if result is None:
            # Create experiment record from manifest
            config = manifest.get("config", {})
            name = manifest.get("name", experiment_id)
            created_at = manifest.get("created_at", datetime.now().isoformat())

            # Insert experiment
            self.db.execute(
                """
                INSERT INTO experiments (
                    experiment_id, name, config, status,
                    created_at, total_conversations, 
                    completed_conversations, failed_conversations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    experiment_id,
                    name,
                    json.dumps(config),
                    "completed",  # Status is completed since we're importing after completion
                    created_at,
                    manifest.get("total_conversations", 0),
                    manifest.get("completed_conversations", 0),
                    manifest.get("failed_conversations", 0),
                ],
            )

            logger.info(f"Created experiment record for {experiment_id}")

    def ensure_conversation_exists(
        self, experiment_id: str, conversation_id: str, conv_data: Dict
    ) -> bool:
        """Ensure conversation exists in database.

        Args:
            experiment_id: Experiment ID
            conversation_id: Conversation ID
            conv_data: Conversation data from events

        Returns:
            True if conversation was created, False if it already existed
        """
        # Check if conversation already exists
        result = self.db.execute(
            "SELECT conversation_id FROM conversations WHERE conversation_id = ?",
            [conversation_id],
        ).fetchone()

        if result is None:
            config = conv_data.get("config", {})

            # Get first and last turn timestamps
            turn_nums = sorted(conv_data["turns"].keys())
            first_turn = conv_data["turns"][turn_nums[0]] if turn_nums else {}
            last_turn = conv_data["turns"][turn_nums[-1]] if turn_nums else {}

            # Calculate conversation metrics
            total_turns = len(turn_nums)
            final_convergence = last_turn.get("convergence_score", 0)

            # Insert conversation record
            self.db.execute(
                """
                INSERT INTO conversations (
                    conversation_id, experiment_id, status,
                    agent_a_model, agent_b_model,
                    agent_a_temperature, agent_b_temperature,
                    initial_prompt, total_turns, 
                    final_convergence_score,
                    started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    conversation_id,
                    experiment_id,
                    "completed",  # Status is completed since we're importing after completion
                    config.get("agent_a_model"),
                    config.get("agent_b_model"),
                    config.get("temperature_a"),
                    config.get("temperature_b"),
                    config.get("initial_prompt"),
                    total_turns,
                    final_convergence,
                    first_turn.get("timestamp"),
                    last_turn.get("timestamp"),
                ],
            )

            return True

        return False

    def insert_messages(
        self, conversation_id: str, turn_number: int, turn_data: Dict, messages: Dict
    ) -> None:
        """Insert messages into messages table for compatibility.

        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            turn_data: Turn data containing messages
            messages: Message metadata from events
        """
        # Insert agent A message
        self.db.execute(
            """
            INSERT INTO messages (
                conversation_id, turn_number, agent_id, 
                content, timestamp, token_count
            ) VALUES (?, ?, ?, ?, ?, ?)
        """,
            [
                conversation_id,
                turn_number,
                "agent_a",
                turn_data["agent_a_message"],
                turn_data["timestamp"],
                messages.get("agent_a", {}).get("total_tokens", 0),
            ],
        )

        # Insert agent B message
        self.db.execute(
            """
            INSERT INTO messages (
                conversation_id, turn_number, agent_id,
                content, timestamp, token_count
            ) VALUES (?, ?, ?, ?, ?, ?)
        """,
            [
                conversation_id,
                turn_number,
                "agent_b",
                turn_data["agent_b_message"],
                turn_data["timestamp"],
                messages.get("agent_b", {}).get("total_tokens", 0),
            ],
        )

    def insert_thinking_trace(
        self, conversation_id: str, turn_number: int, agent_id: str, thinking: Dict
    ) -> None:
        """Insert thinking trace into thinking_traces table.

        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            agent_id: Agent ID (agent_a or agent_b)
            thinking: Thinking trace data
        """
        self.db.execute(
            """
            INSERT INTO thinking_traces (
                conversation_id, turn_number, agent_id,
                thinking_content, thinking_tokens, duration_ms, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            [
                conversation_id,
                turn_number,
                agent_id,
                thinking.get("thinking_content", ""),
                thinking.get("thinking_tokens"),
                thinking.get("duration_ms"),
                thinking.get("timestamp"),
            ],
        )
