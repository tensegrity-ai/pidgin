"""Read experiment data from JSONL event files."""

import json

# Avoid importing pidgin modules to prevent circular imports
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.constants import ConversationStatus, ExperimentStatus

logger = logging.getLogger("jsonl_reader")


class JSONLExperimentReader:
    """Read experiment data from JSONL event files."""

    def __init__(self, experiments_dir: Path):
        """Initialize reader with experiments directory.

        Args:
            experiments_dir: Base directory containing experiments
        """
        self.experiments_dir = Path(experiments_dir)

    def list_experiments(
        self, status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all experiments by scanning JSONL files.

        Args:
            status_filter: Optional status to filter by

        Returns:
            List of experiment dictionaries
        """
        experiments = {}

        # Return empty list if experiments directory doesn't exist yet
        if not self.experiments_dir.exists():
            return []

        # Scan for experiment directories
        for exp_dir in self.experiments_dir.iterdir():
            if not exp_dir.is_dir() or not exp_dir.name.startswith("exp_"):
                continue

            # Look for per-conversation JSONL files in experiment directory
            # Single, canonical pattern: events_<conversation_id>.jsonl
            jsonl_files = list(exp_dir.glob("events_*.jsonl"))
            if not jsonl_files:
                continue

            # Parse JSONL files to get experiment info
            exp_info = self._parse_experiment_from_events(exp_dir.name, exp_dir)
            if exp_info:
                if status_filter is None or exp_info.get("status") == status_filter:
                    experiments[exp_info["experiment_id"]] = exp_info

        # Sort by created_at descending
        return sorted(
            experiments.values(), key=lambda x: x.get("created_at", ""), reverse=True
        )

    def get_experiment_status(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status for a specific experiment.

        Args:
            experiment_id: Experiment ID to look up

        Returns:
            Experiment info dict or None if not found
        """
        exp_dir = self.experiments_dir / experiment_id
        if not exp_dir.exists():
            return None

        # JSONL files are directly in experiment directory, canonical pattern
        jsonl_files = list(exp_dir.glob("events_*.jsonl"))
        if not jsonl_files:
            return None

        return self._parse_experiment_from_events(experiment_id, exp_dir)

    def _parse_experiment_from_events(
        self, experiment_id: str, exp_dir: Path
    ) -> Optional[Dict[str, Any]]:
        """Parse experiment info from JSONL event files.

        Args:
            experiment_id: Experiment ID
            exp_dir: Experiment directory containing JSONL files

        Returns:
            Experiment info dict
        """
        # Aggregate data from all conversation event files
        conversations = {}
        experiment_info: Dict[str, Any] = {
            "experiment_id": experiment_id,
            "status": "unknown",
            "created_at": None,
            "started_at": None,
            "completed_conversations": 0,
            "failed_conversations": 0,
            "total_conversations": 0,
            "config": {},
            "name": experiment_id,  # Default to ID if no name found
        }

        # Process each JSONL file
        for jsonl_file in exp_dir.glob("events_*.jsonl"):
            # Extract conversation id from naming convention: events_<conv_id>.jsonl
            stem = jsonl_file.stem
            conv_id = stem[len("events_") :]
            conv_info = self._parse_conversation_events(jsonl_file)

            if conv_info:
                conversations[conv_id] = conv_info

                # Update experiment info from first conversation
                if not experiment_info["created_at"] and conv_info.get("started_at"):
                    experiment_info["created_at"] = conv_info["started_at"]
                    experiment_info["started_at"] = conv_info["started_at"]

                # Extract config from first conversation
                if not experiment_info["config"] and conv_info.get("config"):
                    experiment_info["config"] = conv_info["config"]

                # Update experiment name if found
                if conv_info.get("experiment_name"):
                    experiment_info["name"] = conv_info["experiment_name"]

                # Count conversation statuses
                if conv_info["status"] == ConversationStatus.COMPLETED:
                    experiment_info["completed_conversations"] += 1
                elif conv_info["status"] == ConversationStatus.FAILED:
                    experiment_info["failed_conversations"] += 1

        # Calculate total conversations and overall status
        experiment_info["total_conversations"] = len(conversations)

        if experiment_info["total_conversations"] == 0:
            return None

        # Determine experiment status
        if (
            experiment_info["completed_conversations"]
            + experiment_info["failed_conversations"]
            == experiment_info["total_conversations"]
        ):
            experiment_info["status"] = ExperimentStatus.COMPLETED
        elif any(
            c["status"] == ConversationStatus.RUNNING for c in conversations.values()
        ):
            experiment_info["status"] = ExperimentStatus.RUNNING
        else:
            experiment_info["status"] = "unknown"

        return experiment_info

    def _parse_conversation_events(self, jsonl_file: Path) -> Optional[Dict[str, Any]]:
        """Parse a single conversation's events.

        Args:
            jsonl_file: Path to JSONL file

        Returns:
            Conversation info dict
        """
        conv_info: Dict[str, Any] = {
            "status": "unknown",
            "started_at": None,
            "ended_at": None,
            "total_turns": 0,
            "config": {},
            "convergence_scores": [],
        }

        try:
            with open(jsonl_file) as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        event = json.loads(line)
                        # Canonical format uses event_type at top-level
                        event_type = event.get("event_type")

                        if event_type == "ConversationStartEvent":
                            conv_info["started_at"] = event.get("timestamp")
                            conv_info["status"] = ConversationStatus.RUNNING
                            # Extract config
                            conv_info["config"] = {
                                "agent_a_model": event.get("agent_a_model"),
                                "agent_b_model": event.get("agent_b_model"),
                                "initial_prompt": event.get("initial_prompt"),
                                "max_turns": event.get("max_turns"),
                                "temperature_a": event.get("temperature_a"),
                                "temperature_b": event.get("temperature_b"),
                            }

                        elif event_type == "ConversationEndEvent":
                            conv_info["ended_at"] = event.get("timestamp")
                            conv_info["total_turns"] = event.get("total_turns", 0)
                            reason = event.get("reason", "")

                            if reason == "max_turns" or reason == "high_convergence":
                                conv_info["status"] = ConversationStatus.COMPLETED
                            elif reason == "error":
                                conv_info["status"] = ConversationStatus.FAILED
                            else:
                                conv_info["status"] = ConversationStatus.INTERRUPTED

                        elif event_type == "TurnCompleteEvent":
                            conv_info["total_turns"] = max(
                                conv_info["total_turns"], event.get("turn_number", 0)
                            )
                            if "convergence_score" in event:
                                conv_info["convergence_scores"].append(
                                    event["convergence_score"]
                                )

                        elif event_type == "ExperimentCreated":
                            if "name" in event:
                                conv_info["experiment_name"] = event["name"]

                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in {jsonl_file}: {line}")
                        continue

        except Exception as e:
            logger.error(f"Error reading {jsonl_file}: {e}")
            return None

        return conv_info

    def _extract_name_from_prompt(self, prompt: str) -> str:
        """Try to extract a meaningful name from the initial prompt.

        Args:
            prompt: Initial prompt text

        Returns:
            Extracted name or truncated prompt
        """
        # Simple heuristic: use first few words
        words = prompt.split()[:5]
        name = " ".join(words)

        # Truncate if too long
        if len(name) > 50:
            name = name[:47] + "..."

        return name
