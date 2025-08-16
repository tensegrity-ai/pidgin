"""Parse experiment state from manifest.json files."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from ...io.logger import get_logger
from ..state_types import ConversationState, ExperimentState

logger = get_logger("manifest_parser")


class ManifestParser:
    """Parse experiment manifests into state objects."""

    def parse_manifest(
        self,
        manifest_path: Path,
        exp_dir: Path,
        get_conversation_timestamps=None,
        get_last_convergence=None,
        get_truncation_info=None,
    ) -> Optional[ExperimentState]:
        """Build experiment state from manifest.json.

        Args:
            manifest_path: Path to manifest.json
            exp_dir: Experiment directory path
            get_conversation_timestamps: Callback to get timestamps from JSONL
            get_last_convergence: Callback to get convergence score
            get_truncation_info: Callback to get truncation info

        Returns:
            ExperimentState or None if invalid
        """
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read manifest {manifest_path}: {e}")
            return None

        # Extract experiment info
        exp_id = manifest.get("experiment_id", exp_dir.name)
        config = manifest.get("config", {})

        # Create experiment state
        state = ExperimentState(
            experiment_id=exp_id,
            name=manifest.get("name", exp_id),
            status=manifest.get("status", "unknown"),
            total_conversations=manifest.get("total_conversations", 0),
            completed_conversations=manifest.get("completed_conversations", 0),
            failed_conversations=manifest.get("failed_conversations", 0),
            directory=exp_dir,
        )

        # Parse timestamps
        if created_at := manifest.get("created_at"):
            state.created_at = self.parse_timestamp(created_at)
        if started_at := manifest.get("started_at"):
            state.started_at = self.parse_timestamp(started_at)
        if completed_at := manifest.get("completed_at"):
            state.completed_at = self.parse_timestamp(completed_at)

        # Build conversation states
        for conv_id, conv_info in manifest.get("conversations", {}).items():
            conv_state = self._build_conversation_state(
                conv_id=conv_id,
                conv_info=conv_info,
                exp_id=exp_id,
                config=config,
                exp_dir=exp_dir,
                get_conversation_timestamps=get_conversation_timestamps,
                get_last_convergence=get_last_convergence,
                get_truncation_info=get_truncation_info,
            )
            state.conversations[conv_id] = conv_state

        return state

    def _build_conversation_state(
        self,
        conv_id: str,
        conv_info: Dict,
        exp_id: str,
        config: Dict,
        exp_dir: Path,
        get_conversation_timestamps=None,
        get_last_convergence=None,
        get_truncation_info=None,
    ) -> ConversationState:
        """Build a single conversation state.

        Args:
            conv_id: Conversation ID
            conv_info: Conversation info from manifest
            exp_id: Experiment ID
            config: Experiment config
            exp_dir: Experiment directory
            get_conversation_timestamps: Optional callback
            get_last_convergence: Optional callback
            get_truncation_info: Optional callback

        Returns:
            ConversationState object
        """
        conv_state = ConversationState(
            conversation_id=conv_id,
            experiment_id=exp_id,
            status=conv_info.get("status", "unknown"),
            current_turn=conv_info.get("total_turns", 0),
            max_turns=config.get("max_turns", 20),
        )

        # Set model info from config
        conv_state.agent_a_model = config.get("agent_a_model", "unknown")
        conv_state.agent_b_model = config.get("agent_b_model", "unknown")

        # Parse timestamps
        if updated := conv_info.get("last_updated"):
            # Use last_updated as a proxy for both started and completed
            conv_state.started_at = self.parse_timestamp(updated)
            if conv_state.status == "completed":
                conv_state.completed_at = self.parse_timestamp(updated)

        # Try to get more accurate timestamps from JSONL if callback provided
        if get_conversation_timestamps:
            jsonl_timestamps = get_conversation_timestamps(exp_dir, conv_id)
            if jsonl_timestamps:
                if jsonl_timestamps.get("started_at"):
                    conv_state.started_at = jsonl_timestamps["started_at"]
                if jsonl_timestamps.get("completed_at"):
                    conv_state.completed_at = jsonl_timestamps["completed_at"]

        # Get convergence from JSONL files if callback provided
        if get_last_convergence:
            conv_state.last_convergence = get_last_convergence(exp_dir, conv_id)

        # Get truncation info from JSONL files if callback provided
        if get_truncation_info:
            truncation_info = get_truncation_info(exp_dir, conv_id)
            if truncation_info:
                conv_state.truncation_count = truncation_info.get("count", 0)
                conv_state.last_truncation_turn = truncation_info.get("last_turn")

        return conv_state

    def parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO format timestamp.

        Args:
            timestamp_str: Timestamp string

        Returns:
            datetime object (always timezone-aware)
        """
        # Handle both with and without timezone
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(timestamp_str)
            # Ensure timezone awareness
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            # Try without microseconds
            try:
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
                # Make timezone aware
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                return datetime.now(timezone.utc)
