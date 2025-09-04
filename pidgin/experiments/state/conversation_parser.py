"""Parse conversation data from JSONL event files."""

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from ...io.logger import get_logger
from ..state_types import ConversationState

if TYPE_CHECKING:
    pass

logger = get_logger("conversation_parser")


class ConversationParser:
    """Parse conversation state from JSONL event files."""

    def get_conversation_timestamps(
        self, exp_dir: Path, conv_id: str
    ) -> Optional[Dict[str, datetime]]:
        """Get conversation start/end timestamps from JSONL.

        Args:
            exp_dir: Experiment directory
            conv_id: Conversation ID

        Returns:
            Dict with started_at and completed_at timestamps
        """
        # Canonical location
        possible_files = [exp_dir / f"events_{conv_id}.jsonl"]

        for events_file in possible_files:
            if events_file.exists():
                return self._extract_timestamps_from_jsonl(events_file, conv_id)

        return None

    def _extract_timestamps_from_jsonl(
        self, events_file: Path, conv_id: str
    ) -> Optional[Dict[str, datetime]]:
        """Extract timestamps from a JSONL file.

        Args:
            events_file: Path to events.jsonl
            conv_id: Conversation ID to filter by

        Returns:
            Dict with timestamps or None
        """
        timestamps = {}

        try:
            with open(events_file) as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        # Support both current (event_type + top-level fields)
                        # and legacy (type + nested data) formats
                        event_type = event.get("event_type") or event.get("type", "")
                        data = event if "event_type" in event else event.get("data", {})

                        # Check if this event is for our conversation
                        if data.get("conversation_id") != conv_id:
                            continue

                        if event_type == "ConversationStartEvent":
                            if timestamp_str := event.get("timestamp"):
                                from .manifest_parser import ManifestParser

                                parser = ManifestParser()
                                timestamps["started_at"] = parser.parse_timestamp(
                                    timestamp_str
                                )

                        elif event_type == "ConversationEndEvent":
                            if timestamp_str := event.get("timestamp"):
                                from .manifest_parser import ManifestParser

                                parser = ManifestParser()
                                timestamps["completed_at"] = parser.parse_timestamp(
                                    timestamp_str
                                )

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.debug(f"Failed to read timestamps from {events_file}: {e}")
            return None

        return timestamps if timestamps else None

    def get_last_convergence(self, exp_dir: Path, conv_id: str) -> Optional[float]:
        """Get the last convergence score for a conversation from JSONL files.

        Args:
            exp_dir: Experiment directory
            conv_id: Conversation ID

        Returns:
            Last convergence score or None
        """
        # Canonical location only
        possible_files = [exp_dir / f"events_{conv_id}.jsonl"]

        last_convergence = None

        for events_file in possible_files:
            if not events_file.exists():
                continue

            try:
                with open(events_file) as f:
                    for line in f:
                        try:
                            event = json.loads(line)
                            event_type = event.get("event_type")
                            data = event

                            # Check if this is a TurnCompleteEvent for our conversation
                            if (
                                event_type == "TurnCompleteEvent"
                                and data.get("conversation_id") == conv_id
                            ):
                                # Get convergence score if present
                                if score := data.get("convergence_score"):
                                    last_convergence = score

                        except json.JSONDecodeError:
                            continue

            except Exception as e:
                logger.debug(f"Failed to read convergence from {events_file}: {e}")
                continue

            if last_convergence is not None:
                break

        return last_convergence

    def get_truncation_info(self, exp_dir: Path, conv_id: str) -> Dict[str, Any]:
        """Get truncation information for a conversation.

        Args:
            exp_dir: Experiment directory
            conv_id: Conversation ID

        Returns:
            Dict with truncation count and last turn
        """
        # Canonical location only
        possible_files = [exp_dir / f"events_{conv_id}.jsonl"]

        truncation_count = 0
        last_truncation_turn = None

        for events_file in possible_files:
            if not events_file.exists():
                continue

            try:
                with open(events_file) as f:
                    for line in f:
                        try:
                            event = json.loads(line)
                            event_type = event.get("event_type")
                            data = event

                            # Check if this is a ContextTruncationEvent for our conversation
                            if (
                                event_type == "ContextTruncationEvent"
                                and data.get("conversation_id") == conv_id
                            ):
                                truncation_count += 1
                                last_truncation_turn = data.get("turn_number")

                        except json.JSONDecodeError:
                            continue

            except Exception as e:
                logger.debug(f"Failed to read truncation info from {events_file}: {e}")
                continue

            if truncation_count > 0:
                break

        return (
            {"count": truncation_count, "last_turn": last_truncation_turn}
            if truncation_count > 0
            else {}
        )

    def get_conversation_state(
        self, exp_dir: Path, conv_id: str
    ) -> Optional[ConversationState]:
        """Build conversation state directly from JSONL files.

        This is used when we don't have a manifest entry for a conversation.

        Args:
            exp_dir: Experiment directory
            conv_id: Conversation ID

        Returns:
            ConversationState or None
        """
        # Try to find events for this conversation (canonical location)
        possible_files = [exp_dir / f"events_{conv_id}.jsonl"]

        for events_file in possible_files:
            if not events_file.exists():
                continue

            state = self._build_state_from_events(events_file, conv_id)
            if state:
                return state

        return None

    def _build_state_from_events(
        self, events_file: Path, conv_id: str
    ) -> Optional[ConversationState]:
        """Build conversation state from event file.

        Args:
            events_file: Path to events.jsonl
            conv_id: Conversation ID

        Returns:
            ConversationState or None
        """
        state = None
        turn_count = 0
        has_end_event = False

        try:
            with open(events_file) as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        data = event

                        if data.get("conversation_id") != conv_id:
                            continue

                        event_type = event.get("event_type", "")

                        # Initialize state on first event for this conversation
                        if state is None:
                            state = ConversationState(
                                conversation_id=conv_id,
                                experiment_id=data.get("experiment_id", "unknown"),
                                status="running",
                                current_turn=0,
                                max_turns=20,  # Default
                            )

                        # Process different event types
                        if event_type == "ConversationStartEvent":
                            state.agent_a_model = data.get("agent_a_model", "unknown")
                            state.agent_b_model = data.get("agent_b_model", "unknown")
                            state.max_turns = data.get("max_turns", 20)
                            if timestamp := event.get("timestamp"):
                                from .manifest_parser import ManifestParser

                                parser = ManifestParser()
                                state.started_at = parser.parse_timestamp(timestamp)

                        elif event_type == "TurnCompleteEvent":
                            turn_count += 1
                            state.current_turn = turn_count
                            if score := data.get("convergence_score"):
                                state.last_convergence = score

                        elif event_type == "ConversationEndEvent":
                            has_end_event = True
                            state.status = "completed"
                            if timestamp := event.get("timestamp"):
                                from .manifest_parser import ManifestParser

                                parser = ManifestParser()
                                state.completed_at = parser.parse_timestamp(timestamp)

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.debug(f"Failed to build state from {events_file}: {e}")
            return None

        # Set final status if we have state but no end event
        if state and not has_end_event:
            state.status = "interrupted"

        return state
