"""Error tracking and resolution utilities for the monitor."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from ..io.logger import get_logger
from ..io.paths import get_experiments_dir

logger = get_logger("error_tracker")


class ErrorTracker:
    """Tracks errors from JSONL files and monitors resolution."""

    def __init__(self):
        self.exp_base = get_experiments_dir()

    def get_recent_errors(self, minutes: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors from all JSONL files."""
        errors = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)

        # Find all JSONL files
        jsonl_files = list(self.exp_base.glob("**/*.jsonl"))

        for file_path in jsonl_files:
            try:
                # Read the file and look for errors
                with open(file_path) as f:
                    for line_num, line in enumerate(f, 1):
                        if not line.strip():
                            continue

                        try:
                            event = json.loads(line)
                            event_type = event.get("event_type", "")

                            # Check for error events
                            if "error" in event_type.lower() or event.get("error"):
                                timestamp_str = event.get("timestamp")
                                if timestamp_str:
                                    # Parse timestamp
                                    timestamp = datetime.fromisoformat(
                                        timestamp_str.replace("Z", "+00:00")
                                    )

                                    if timestamp >= cutoff_time:
                                        # Extract error details
                                        error_info = {
                                            "timestamp": timestamp,
                                            "file": file_path,
                                            "line": line_num,
                                            "event_type": event_type,
                                            "error": event.get(
                                                "error", "Unknown error"
                                            ),
                                            "details": event.get("details", {}),
                                            "event": event,  # Keep full event for context
                                        }

                                        # Try to extract more context
                                        if "message" in event:
                                            error_info["message"] = event["message"]
                                        if "conversation_id" in event:
                                            error_info["conversation_id"] = event[
                                                "conversation_id"
                                            ]
                                        if "experiment_id" in event:
                                            error_info["experiment_id"] = event[
                                                "experiment_id"
                                            ]

                                        errors.append(error_info)
                        except json.JSONDecodeError:
                            logger.debug(
                                f"Skipping malformed JSON in {file_path}:{line_num}"
                            )
                        except Exception as e:
                            logger.debug(
                                f"Error parsing event in {file_path}:{line_num}: {e}"
                            )

            except Exception as e:
                logger.debug(f"Error reading file {file_path}: {e}")

        # Sort by timestamp (most recent first)
        errors.sort(key=lambda x: x["timestamp"], reverse=True)
        return errors

    def check_error_resolved(
        self, error: Dict[str, Any], all_errors: List[Dict[str, Any]]
    ) -> bool:
        """Check if an error has been resolved.

        An error is considered resolved if:
        1. The same experiment/conversation had a success event after the error
        2. The file that had the error no longer exists
        3. A newer run of the same experiment succeeded
        """
        # Check if the file still exists
        if "file" in error and not Path(error["file"]).exists():
            return True

        # Check for success events after this error
        error_time = error["timestamp"]
        exp_id = error.get("experiment_id")
        conv_id = error.get("conversation_id")

        if exp_id or conv_id:
            # Look for success events with same IDs but later timestamp
            for other in all_errors:
                if other["timestamp"] <= error_time:
                    continue

                # Check if this is a success event for the same context
                if (exp_id and other.get("experiment_id") == exp_id) or (
                    conv_id and other.get("conversation_id") == conv_id
                ):
                    # If it's not an error event, consider original error resolved
                    if "error" not in other.get("event_type", "").lower():
                        return True

        return False
