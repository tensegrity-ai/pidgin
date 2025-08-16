"""Repository for experiment operations."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.constants import ExperimentStatus
from ..io.logger import get_logger
from .base_repository import BaseRepository

logger = get_logger("experiment_repository")


class ExperimentRepository(BaseRepository):
    """Repository for experiment CRUD operations."""

    def create_experiment(self, name: str, config: dict) -> str:
        """Create a new experiment.

        Args:
            name: Experiment name
            config: Experiment configuration

        Returns:
            Experiment ID
        """
        experiment_id = uuid.uuid4().hex
        created_at = datetime.now()

        query = """
            INSERT INTO experiments (
                experiment_id, name, config, status,
                created_at, total_conversations, completed_conversations,
                failed_conversations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.execute(
            query,
            [
                experiment_id,
                name,
                json.dumps(config),
                ExperimentStatus.CREATED,
                created_at,
                0,  # total_conversations
                0,  # completed_conversations
                0,  # failed_conversations
            ],
        )

        logger.info(f"Created experiment {experiment_id}: {name}")
        return experiment_id

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment by ID.

        Args:
            experiment_id: Experiment ID

        Returns:
            Experiment data as dict or None
        """
        result = self.db.execute(
            "SELECT * FROM experiments WHERE experiment_id = ?", [experiment_id]
        ).fetchone()

        if result:
            experiment_dict = self.row_to_dict(result)

            # Parse JSON fields
            experiment_dict["config"] = self.parse_json_field(
                experiment_dict.get("config")
            )
            experiment_dict["metadata"] = self.parse_json_field(
                experiment_dict.get("metadata")
            )

            return experiment_dict

        return None

    def update_experiment_status(
        self, experiment_id: str, status: str, ended_at: Optional[datetime] = None
    ):
        """Update experiment status.

        Args:
            experiment_id: Experiment ID
            status: New status
            ended_at: Optional end timestamp
        """
        if ended_at:
            query = """
                UPDATE experiments
                SET status = ?, completed_at = ?
                WHERE experiment_id = ?
            """
            params = [status, ended_at, experiment_id]
        else:
            query = "UPDATE experiments SET status = ? WHERE experiment_id = ?"
            params = [status, experiment_id]

        self.execute(query, params)
        logger.info(f"Updated experiment {experiment_id} status to {status}")

    def list_experiments(
        self, status_filter: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List experiments with optional filters.

        Args:
            status_filter: Optional status to filter by
            limit: Maximum number of results

        Returns:
            List of experiment dicts
        """
        if status_filter:
            query = """
                SELECT * FROM experiments
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """
            params = [status_filter, limit]
        else:
            query = """
                SELECT * FROM experiments
                ORDER BY created_at DESC
                LIMIT ?
            """
            params = [limit]

        results = self.fetchall(query, params)

        if not results:
            return []

        experiments = []
        for row in results:
            experiment_dict = self.row_to_dict(row)

            # Parse JSON fields
            experiment_dict["config"] = self.parse_json_field(
                experiment_dict.get("config")
            )
            experiment_dict["metadata"] = self.parse_json_field(
                experiment_dict.get("metadata")
            )

            experiments.append(experiment_dict)

        return experiments

    def get_experiment_metrics(self, experiment_id: str) -> Dict[str, Any]:
        """Get aggregate metrics for an experiment.

        Args:
            experiment_id: Experiment ID

        Returns:
            Dict of experiment metrics
        """
        # Get conversation stats
        conv_stats = self.fetchone(
            """
            SELECT
                COUNT(*) as total_conversations,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                AVG(final_convergence_score) as avg_convergence,
                MAX(final_convergence_score) as max_convergence,
                MIN(final_convergence_score) as min_convergence
            FROM conversations
            WHERE experiment_id = ?
        """,
            [experiment_id],
        )

        metrics = {
            "total_conversations": conv_stats[0] or 0,
            "completed_conversations": conv_stats[1] or 0,
            "failed_conversations": conv_stats[2] or 0,
            "avg_convergence": conv_stats[3] or 0.0,
            "max_convergence": conv_stats[4] or 0.0,
            "min_convergence": conv_stats[5] or 0.0,
        }

        # Get turn stats
        turn_stats = self.fetchone(
            """
            SELECT
                AVG(tm.convergence_score) as avg_turn_convergence,
                COUNT(DISTINCT tm.conversation_id) as conversations_with_metrics
            FROM turn_metrics tm
            JOIN conversations c ON tm.conversation_id = c.conversation_id
            WHERE c.experiment_id = ?
        """,
            [experiment_id],
        )

        if turn_stats:
            metrics["avg_turn_convergence"] = turn_stats[0] or 0.0
            metrics["conversations_with_metrics"] = turn_stats[1] or 0

        return metrics

    def delete_experiment(self, experiment_id: str):
        """Delete an experiment record.

        Args:
            experiment_id: Experiment ID to delete
        """
        self.execute("DELETE FROM experiments WHERE experiment_id = ?", [experiment_id])
        logger.info(f"Deleted experiment {experiment_id}")

    def get_experiment_summary(self, experiment_id: str) -> Dict[str, Any]:
        """Get summary statistics for an experiment.

        Args:
            experiment_id: Experiment ID

        Returns:
            Dict with experiment summary
        """
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            return {}

        # Get conversation stats
        conversations = self.fetchall(
            """
            SELECT conversation_id, status
            FROM conversations
            WHERE experiment_id = ?
        """,
            [experiment_id],
        )

        completed = sum(1 for c in conversations if c[1] == "completed")
        failed = sum(1 for c in conversations if c[1] == "failed")
        running = sum(1 for c in conversations if c[1] == "running")

        # Get metrics
        metrics = self.get_experiment_metrics(experiment_id)

        return {
            "experiment_id": experiment_id,
            "status": experiment["status"],
            "total_conversations": len(conversations),
            "completed": completed,
            "failed": failed,
            "running": running,
            "started_at": experiment.get("started_at"),
            "ended_at": experiment.get("completed_at"),
            **metrics,
        }
