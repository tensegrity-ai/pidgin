"""EventStore - synchronous database interface using repository pattern.

This is the primary database interface for Pidgin, providing synchronous
access to all experiment, conversation, and metrics data through a clean
repository-based architecture.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb

from ..core.events import Event
from ..core.types import Agent, Conversation, ConversationTurn
from ..io.logger import get_logger
from .base_repository import BaseRepository
from .conversation_repository import ConversationRepository
from .event_repository import EventRepository
from .experiment_repository import ExperimentRepository
from .import_service import ImportResult, ImportService
from .message_repository import MessageRepository
from .metrics_repository import MetricsRepository

logger = get_logger("event_store")


class EventStore:
    """EventStore - primary database interface for Pidgin.

    Provides synchronous access to experiments, conversations, metrics,
    and JSONL import functionality through a clean repository pattern.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize with DuckDB connection and repositories.

        Args:
            db_path: Path to DuckDB database file (uses default if None)
        """
        if db_path is None:
            from ..io.paths import get_database_path

            db_path = get_database_path()

        self.db_path = db_path
        # Create parent directory if it doesn't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = duckdb.connect(str(db_path))
        self._ensure_schema()

        # Initialize repositories
        self.events = EventRepository(self.db)
        self.experiments = ExperimentRepository(self.db)
        self.conversations = ConversationRepository(self.db)
        self.messages = MessageRepository(self.db)
        self.metrics = MetricsRepository(self.db)

        # Initialize import service
        self.importer = ImportService(db_path)

        logger.debug(f"Initialized EventStore with database: {db_path}")

    def _ensure_schema(self):
        """Ensure database schema exists."""
        from .schema_manager import schema_manager

        schema_manager.ensure_schema(self.db, str(self.db_path))

    def close(self):
        """Close database connection."""
        if hasattr(self, "db") and self.db:
            self.db.close()
        if hasattr(self, "importer") and hasattr(self.importer, "db"):
            self.importer.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # Event Operations (delegate to EventRepository)
    def save_event(self, event: Event, experiment_id: str, conversation_id: str):
        """Save an event to the database."""
        self.events.save_event(event, experiment_id, conversation_id)

    def get_events(self, **kwargs) -> List[Dict[str, Any]]:
        """Get events with optional filters."""
        return self.events.get_events(**kwargs)

    # Experiment Operations (delegate to ExperimentRepository)
    def create_experiment(self, name: str, config: dict) -> str:
        """Create a new experiment."""
        return self.experiments.create_experiment(name, config)

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment by ID."""
        return self.experiments.get_experiment(experiment_id)

    def update_experiment_status(
        self, experiment_id: str, status: str, ended_at: Optional[datetime] = None
    ):
        """Update experiment status."""
        self.experiments.update_experiment_status(experiment_id, status, ended_at)

    def list_experiments(
        self, status_filter: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List experiments with optional filters."""
        return self.experiments.list_experiments(status_filter, limit)

    def get_experiment_metrics(self, experiment_id: str) -> Dict[str, Any]:
        """Get aggregate metrics for an experiment."""
        return self.experiments.get_experiment_metrics(experiment_id)

    def get_experiment_summary(self, experiment_id: str) -> Dict[str, Any]:
        """Get summary statistics for an experiment."""
        return self.experiments.get_experiment_summary(experiment_id)

    # Conversation Operations (delegate to ConversationRepository)
    def create_conversation(
        self, experiment_id: str, conversation_id: str, config: dict
    ):
        """Create a new conversation."""
        self.conversations.create_conversation(experiment_id, conversation_id, config)

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        return self.conversations.get_conversation(conversation_id)

    def update_conversation_status(
        self,
        conversation_id: str,
        status: str,
        end_reason: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Update conversation status."""
        self.conversations.update_conversation_status(
            conversation_id, status, end_reason, error_message
        )

    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get message history for a conversation."""
        return self.conversations.get_conversation_history(conversation_id)

    def log_agent_name(
        self,
        conversation_id: str,
        agent_id: str,
        chosen_name: str,
        turn_number: int = 0,
    ):
        """Log agent's chosen name."""
        self.conversations.log_agent_name(
            conversation_id, agent_id, chosen_name, turn_number
        )

    def get_agent_names(self, conversation_id: str) -> Dict[str, str]:
        """Get agent names for a conversation."""
        return self.conversations.get_agent_names(conversation_id)

    def get_conversation_agent_configs(
        self, conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get agent configurations from conversation."""
        return self.conversations.get_conversation_agent_configs(conversation_id)

    def calculate_convergence_metrics(self, conversation_id: str) -> Dict[str, float]:
        """Calculate convergence metrics for a conversation."""
        return self.conversations.calculate_convergence_metrics(conversation_id)

    # Message Operations (delegate to MessageRepository)
    def save_message(
        self,
        conversation_id: str,
        turn_number: int,
        agent_id: str,
        role: str,
        content: str,
        tokens_used: Optional[int] = None,
    ):
        """Save a message."""
        self.messages.save_message(
            conversation_id, turn_number, agent_id, role, content, tokens_used
        )

    def get_turn_messages(
        self, conversation_id: str, turn_number: int
    ) -> List[Dict[str, Any]]:
        """Get all messages for a turn."""
        return self.messages.get_turn_messages(conversation_id, turn_number)

    # Metrics Operations (delegate to MetricsRepository)
    def log_turn_metrics(
        self, conversation_id: str, turn_number: int, metrics: Dict[str, Any]
    ):
        """Log metrics for a turn."""
        self.metrics.log_turn_metrics(conversation_id, turn_number, metrics)

    def log_message_metrics(
        self,
        conversation_id: str,
        turn_number: int,
        agent_id: str,
        message_length: int,
        vocabulary_size: int,
        punctuation_ratio: float,
        sentiment_score: Optional[float] = None,
    ):
        """Log metrics for a message."""
        self.metrics.log_message_metrics(
            conversation_id,
            turn_number,
            agent_id,
            message_length,
            vocabulary_size,
            punctuation_ratio,
            sentiment_score,
        )

    def log_token_usage(
        self,
        conversation_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_cost: float,
    ):
        """Log token usage for billing/tracking."""
        self.metrics.log_token_usage(
            conversation_id,
            provider,
            model,
            prompt_tokens,
            completion_tokens,
            total_cost,
        )

    # Deletion Operations
    def delete_experiment(self, experiment_id: str):
        """Delete an experiment and all related data.

        This operation is wrapped in a transaction to ensure data integrity.
        If any part fails, the entire deletion is rolled back.
        """
        try:
            # Begin transaction
            self.db.begin()

            # Get all conversation IDs for this experiment
            result = self.db.execute(
                "SELECT conversation_id FROM conversations WHERE experiment_id = ?",
                [experiment_id],
            ).fetchall()

            conversation_ids = [row[0] for row in result]

            # Delete all conversations (which cascades to messages, metrics, events)
            for conv_id in conversation_ids:
                # Note: We call the internal delete methods directly to stay in transaction
                self.metrics.delete_metrics_for_conversation(conv_id)
                self.messages.delete_messages_for_conversation(conv_id)
                self.events.delete_events_for_conversation(conv_id)
                self.conversations.delete_conversation(conv_id)

            # Delete experiment-level events
            self.events.delete_events_for_experiment(experiment_id)

            # Delete from conversation_turns table (for imported data)
            self.db.execute(
                "DELETE FROM conversation_turns WHERE experiment_id = ?",
                [experiment_id],
            )

            # Finally delete experiment
            self.experiments.delete_experiment(experiment_id)

            # Commit transaction
            self.db.commit()

            logger.info(f"Deleted experiment {experiment_id}")
            logger.info(f"Deleted {len(conversation_ids)} conversations")

        except Exception as e:
            # Rollback on any error
            self.db.rollback()
            logger.error(f"Failed to delete experiment {experiment_id}: {e}")
            raise

    def delete_conversation(self, conversation_id: str):
        """Delete a conversation and related data.

        This operation is wrapped in a transaction to ensure data integrity.
        If any part fails, the entire deletion is rolled back.
        """
        try:
            # Begin transaction
            self.db.begin()

            # Delete in reverse dependency order
            self.metrics.delete_metrics_for_conversation(conversation_id)
            self.messages.delete_messages_for_conversation(conversation_id)
            self.events.delete_events_for_conversation(conversation_id)
            self.conversations.delete_conversation(conversation_id)

            # Commit transaction
            self.db.commit()

            logger.info(f"Deleted conversation {conversation_id}")

        except Exception as e:
            # Rollback on any error
            self.db.rollback()
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # JSONL Import functionality (delegate to ImportService)
    def import_experiment_from_jsonl(self, experiment_dir: Path) -> ImportResult:
        """Import experiment data from JSONL files into database.

        Args:
            experiment_dir: Directory containing manifest.json and JSONL files

        Returns:
            ImportResult with success status and counts
        """
        return self.importer.import_experiment_from_jsonl(experiment_dir)

    def import_all_pending(self, experiments_dir: Path) -> List[ImportResult]:
        """Import all experiments that have JSONL files but haven't been imported.

        Args:
            experiments_dir: Root directory containing experiment subdirectories

        Returns:
            List of ImportResults for each experiment
        """
        return self.importer.import_all_pending(experiments_dir)
