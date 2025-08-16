"""Experiment reading utilities for the monitor."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..experiments.state_builder import StateBuilder
from ..io.logger import get_logger

logger = get_logger("experiment_reader")


class ExperimentReader:
    """Reads experiment states and conversation data.

    The ExperimentReader provides a high-level interface for monitoring experiment
    states. It uses the StateBuilder for efficient caching and handles filtering
    of experiments by status. The reader periodically clears the cache to ensure
    fresh data is available for monitoring operations.

    This class is primarily used by the monitor command to display real-time
    experiment status and by the transcript generation tools.
    """

    def __init__(self, exp_base: Path):
        self.exp_base = exp_base
        self.state_builder = StateBuilder()

    def get_experiment_states(
        self, status_filter: Optional[List[str]] = None
    ) -> List[Any]:
        """Get all experiment states efficiently.

        Args:
            status_filter: Optional list of statuses to include

        Returns:
            List of ExperimentState objects
        """
        # Return empty list if no output directory
        if not self.exp_base.exists():
            return []

        # Clear cache periodically for fresh data
        self.state_builder.clear_cache()

        # Get all experiments (not just running)
        experiments = self.state_builder.list_experiments(self.exp_base)

        # Filter by status if requested
        if status_filter:
            experiments = [exp for exp in experiments if exp.status in status_filter]

        return experiments

    def get_failed_conversations(self) -> List[Dict[str, Any]]:
        """Get failed conversations from manifest files.

        Returns:
            List of failed conversation details
        """
        # Return empty list if no output directory
        if not self.exp_base.exists():
            return []

        failed_convs = []

        try:
            for exp_dir in self.exp_base.iterdir():
                if not exp_dir.is_dir():
                    continue

                manifest_path = exp_dir / "manifest.json"
                if not manifest_path.exists():
                    continue

                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)

                    for conv_id, conv_data in manifest.get("conversations", {}).items():
                        if conv_data.get("status") == "failed" and conv_data.get(
                            "error"
                        ):
                            failed_convs.append(
                                {
                                    "experiment_id": exp_dir.name,
                                    "conversation_id": conv_id,
                                    "error": conv_data["error"],
                                    "last_updated": conv_data.get("last_updated", ""),
                                }
                            )

                except (json.JSONDecodeError, OSError) as e:
                    logger.debug(f"Error reading manifest {manifest_path}: {e}")
                    continue
        except FileNotFoundError:
            # Directory doesn't exist
            return []

        return failed_convs

    def is_recent(self, timestamp, minutes: int = 5) -> bool:
        """Check if a timestamp is recent.

        Args:
            timestamp: datetime object
            minutes: How many minutes to consider recent

        Returns:
            True if timestamp is within the last N minutes
        """
        from datetime import datetime, timezone

        try:
            now = datetime.now(timezone.utc)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return (now - timestamp).total_seconds() < (minutes * 60)
        except (AttributeError, TypeError):
            return False
