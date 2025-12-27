# pidgin/experiments/manifest.py
"""Manifest management for experiments."""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from ..core.constants import ConversationStatus, ExperimentStatus


class ManifestManager:
    """Manages experiment manifest with atomic updates."""

    def __init__(self, experiment_dir: Path):
        """Initialize manifest manager.

        Args:
            experiment_dir: Directory containing the experiment
        """
        self.experiment_dir = experiment_dir
        self.manifest_path = experiment_dir / "manifest.json"
        self._lock = threading.Lock()

    def create(
        self,
        experiment_id: str,
        name: str,
        config: Dict[str, Any],
        total_conversations: int,
    ) -> None:
        """Create initial manifest.

        Args:
            experiment_id: Unique experiment ID
            name: Human-readable experiment name
            config: Experiment configuration
            total_conversations: Total number of conversations to run
        """
        manifest = {
            "experiment_id": experiment_id,
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": config,
            "total_conversations": total_conversations,
            "status": ExperimentStatus.CREATED,
            "conversations": {},
        }

        self._write_atomic(manifest)

    def add_conversation(self, conversation_id: str, jsonl_filename: str) -> None:
        """Add a new conversation to the manifest.

        Args:
            conversation_id: Unique conversation ID
            jsonl_filename: Name of the JSONL file for this conversation
        """
        with self._lock:
            manifest = self._read()
            manifest["conversations"][conversation_id] = {
                "status": ConversationStatus.CREATED,
                "jsonl": jsonl_filename,
                "last_line": 0,
                "total_turns": 0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "token_usage": {
                    "agent_a": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "model": None,
                    },
                    "agent_b": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "model": None,
                    },
                    "total": 0,
                },
            }

            # Update experiment status if needed
            if manifest["status"] == ExperimentStatus.CREATED:
                manifest["status"] = ExperimentStatus.RUNNING
                manifest["started_at"] = datetime.now(timezone.utc).isoformat()

            self._write_atomic(manifest)

    def update_conversation(
        self,
        conversation_id: str,
        status: str = None,
        last_line: int = None,
        total_turns: int = None,
        error: str = None,
    ) -> None:
        """Update conversation status and progress.

        Args:
            conversation_id: Conversation to update
            status: New status (running, completed, failed)
            last_line: Last line number written to JSONL
            total_turns: Number of turns completed
            error: Error message if failed
        """
        with self._lock:
            manifest = self._read()
            conversation = manifest["conversations"].get(conversation_id, {})

            if status:
                conversation["status"] = status
            if last_line is not None:
                conversation["last_line"] = last_line
            if total_turns is not None:
                conversation["total_turns"] = total_turns
            if error:
                conversation["error"] = error

            conversation["last_updated"] = datetime.now(timezone.utc).isoformat()
            manifest["conversations"][conversation_id] = conversation

            # Update experiment-level counts
            self._update_experiment_stats(manifest)

            self._write_atomic(manifest)

    def update_token_usage(
        self,
        conversation_id: str,
        agent_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = None,
    ) -> None:
        """Update token usage for a conversation.

        Args:
            conversation_id: Conversation ID
            agent_id: Either "agent_a" or "agent_b"
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens used
            model: Model name (optional, will be set on first update)
        """
        with self._lock:
            manifest = self._read()

            if conversation_id not in manifest["conversations"]:
                return

            conv = manifest["conversations"][conversation_id]

            # Update agent's token usage
            agent_usage = conv["token_usage"][agent_id]
            agent_usage["prompt_tokens"] += prompt_tokens
            agent_usage["completion_tokens"] += completion_tokens
            agent_usage["total_tokens"] += prompt_tokens + completion_tokens

            # Set model if provided and not already set
            if model and not agent_usage["model"]:
                agent_usage["model"] = model

            # Update total
            conv["token_usage"]["total"] = (
                conv["token_usage"]["agent_a"]["total_tokens"]
                + conv["token_usage"]["agent_b"]["total_tokens"]
            )

            self._write_atomic(manifest)

    def update_thinking_tokens(
        self,
        conversation_id: str,
        agent_id: str,
        thinking_tokens: int,
    ) -> None:
        """Update thinking token usage for a conversation.

        Args:
            conversation_id: Conversation ID
            agent_id: Either "agent_a" or "agent_b"
            thinking_tokens: Number of thinking tokens used
        """
        with self._lock:
            manifest = self._read()

            if conversation_id not in manifest["conversations"]:
                return

            conv = manifest["conversations"][conversation_id]

            # Ensure thinking_tokens field exists
            if "thinking_tokens" not in conv["token_usage"][agent_id]:
                conv["token_usage"][agent_id]["thinking_tokens"] = 0

            # Update agent's thinking token usage
            conv["token_usage"][agent_id]["thinking_tokens"] += thinking_tokens

            self._write_atomic(manifest)

    def update_conversation_status(
        self, conversation_id: str, status: str, completed_count: int, failed_count: int
    ) -> None:
        """Update the status of a conversation.

        Args:
            conversation_id: ID of the conversation
            status: New status (completed, failed, etc)
            completed_count: Number of completed conversations
            failed_count: Number of failed conversations
        """
        manifest = self._read()

        # Update conversation status
        if conversation_id in manifest.get("conversations", {}):
            manifest["conversations"][conversation_id]["status"] = status
            manifest["conversations"][conversation_id]["last_updated"] = datetime.now(
                timezone.utc
            ).isoformat()

        # Update experiment counts
        manifest["completed_conversations"] = completed_count
        manifest["failed_conversations"] = failed_count

        # Update running count
        running_count = len(
            [
                c
                for c in manifest.get("conversations", {}).values()
                if c.get("status") == "running"
            ]
        )
        manifest["running_conversations"] = running_count

        self._write_atomic(manifest)

    def update_experiment_status(self, status: str, error: str = None) -> None:
        """Update experiment status.

        Args:
            status: New status (running, completed, failed, interrupted)
            error: Optional error message
        """
        with self._lock:
            manifest = self._read()
            manifest["status"] = status
            if error:
                manifest["error"] = error
            if status in [
                ExperimentStatus.COMPLETED,
                ExperimentStatus.FAILED,
                ExperimentStatus.INTERRUPTED,
            ]:
                manifest["completed_at"] = datetime.now(timezone.utc).isoformat()

            self._write_atomic(manifest)

    def get_manifest(self) -> Dict[str, Any]:
        """Get current manifest data.

        Returns:
            Current manifest dictionary
        """
        return self._read()

    def _read(self) -> Dict[str, Any]:
        """Read manifest from disk.

        Returns:
            Manifest dictionary or empty dict if not found
        """
        if not self.manifest_path.exists():
            return {}

        try:
            with open(self.manifest_path) as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_atomic(self, manifest: Dict[str, Any]) -> None:
        """Write manifest atomically.

        Args:
            manifest: Manifest data to write
        """
        # Write to temporary file first
        temp_path = self.manifest_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(manifest, f, indent=2)

        # Atomic rename
        os.replace(temp_path, self.manifest_path)

    def _update_experiment_stats(self, manifest: Dict[str, Any]) -> None:
        """Update experiment-level statistics based on conversations.

        Args:
            manifest: Manifest to update (modified in place)
        """
        completed = 0
        failed = 0
        running = 0

        for conversation in manifest["conversations"].values():
            if conversation["status"] == ConversationStatus.COMPLETED:
                completed += 1
            elif conversation["status"] == ConversationStatus.FAILED:
                failed += 1
            elif conversation["status"] == ConversationStatus.RUNNING:
                running += 1

        manifest["completed_conversations"] = completed
        manifest["failed_conversations"] = failed
        manifest["running_conversations"] = running

        # Update experiment status if all done
        total = manifest.get("total_conversations", 0)
        if completed + failed >= total and total > 0:
            if failed == 0:
                manifest["status"] = ExperimentStatus.COMPLETED
            else:
                manifest["status"] = ExperimentStatus.COMPLETED_WITH_FAILURES
