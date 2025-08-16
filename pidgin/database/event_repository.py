"""Repository for event operations."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.events import Event
from ..io.logger import get_logger
from .base_repository import BaseRepository

logger = get_logger("event_repository")


class EventRepository(BaseRepository):
    """Repository for event storage and retrieval."""

    def save_event(self, event: Event, experiment_id: str, conversation_id: str):
        """Save an event to the database with atomic sequence generation.

        Args:
            event: Event to save
            experiment_id: Experiment ID
            conversation_id: Conversation ID
        """
        # Convert event to dict for storage
        event_dict: Dict[str, Any] = {
            "event_type": event.__class__.__name__,
            "conversation_id": conversation_id,
            "timestamp": event.timestamp.isoformat(),
            "event_id": event.event_id,
        }

        # Add event-specific fields
        for field_name in event.__dataclass_fields__:
            if field_name not in ["timestamp", "event_id"]:
                value = getattr(event, field_name)
                if value is None:
                    event_dict[field_name] = None
                elif hasattr(value, "isoformat"):
                    # Handle datetime objects
                    event_dict[field_name] = value.isoformat()
                elif hasattr(value, "model_dump"):
                    # Handle Pydantic models
                    event_dict[field_name] = value.model_dump(mode="json")
                elif hasattr(value, "__dict__") and not isinstance(
                    value, (str, int, float, bool, list, dict)
                ):
                    # Handle dataclass objects
                    sub_dict = {}
                    for k, v in value.__dict__.items():
                        if hasattr(v, "isoformat"):
                            sub_dict[k] = v.isoformat()
                        elif hasattr(v, "model_dump"):
                            sub_dict[k] = v.model_dump(mode="json")
                        elif hasattr(v, "__dict__") and not isinstance(
                            v, (str, int, float, bool, list, dict)
                        ):
                            # Recursively handle nested objects
                            sub_dict[k] = {
                                kk: vv.isoformat() if hasattr(vv, "isoformat") else vv
                                for kk, vv in v.__dict__.items()
                            }
                        else:
                            sub_dict[k] = v
                    event_dict[field_name] = sub_dict
                elif isinstance(value, list):
                    # Handle lists - check each item
                    serialized_list = []
                    for item in value:
                        if hasattr(item, "model_dump"):
                            serialized_list.append(item.model_dump(mode="json"))
                        elif hasattr(item, "__dict__") and not isinstance(
                            item, (str, int, float, bool)
                        ):
                            serialized_list.append(dict(item.__dict__.items()))
                        else:
                            serialized_list.append(item)
                    event_dict[field_name] = serialized_list
                else:
                    event_dict[field_name] = value

        # Atomic INSERT with subquery for sequence generation
        # This eliminates the race condition by calculating the sequence
        # within the same INSERT statement
        query = """
            INSERT INTO events (
                timestamp, event_type, conversation_id,
                experiment_id, event_data, sequence
            )
            SELECT ?, ?, ?, ?, ?,
                   COALESCE(MAX(sequence), 0) + 1
            FROM events
            WHERE conversation_id = ?
            RETURNING sequence
        """

        result = self.fetchone(
            query,
            [
                event.timestamp,
                event.__class__.__name__,
                conversation_id,
                experiment_id,
                json.dumps(event_dict),
                conversation_id,  # For the WHERE clause in the subquery
            ],
        )

        if result:
            sequence = result[0]
            logger.debug(
                f"Saved {event.__class__.__name__} for conversation {conversation_id} with sequence {sequence}"
            )
        else:
            # Fallback for DuckDB versions that might not support RETURNING
            logger.debug(
                f"Saved {event.__class__.__name__} for conversation {conversation_id}"
            )

    def get_events(
        self,
        conversation_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get events with optional filters.

        Args:
            conversation_id: Filter by conversation
            experiment_id: Filter by experiment
            event_types: Filter by event types
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of event dictionaries
        """
        conditions = []
        params: List[Any] = []

        if conversation_id:
            conditions.append("conversation_id = ?")
            params.append(conversation_id)

        if experiment_id:
            conditions.append("experiment_id = ?")
            params.append(experiment_id)

        if event_types:
            placeholders = ",".join(["?" for _ in event_types])
            conditions.append(f"event_type IN ({placeholders})")
            params.extend(event_types)

        if start_time:
            conditions.append("timestamp >= ?")
            params.append(
                start_time.isoformat()
                if hasattr(start_time, "isoformat")
                else start_time
            )

        if end_time:
            conditions.append("timestamp <= ?")
            params.append(
                end_time.isoformat() if hasattr(end_time, "isoformat") else end_time
            )

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT event_data
            FROM events
            {where_clause}
            ORDER BY timestamp, sequence
            LIMIT ? OFFSET ?
        """

        params.extend([limit, offset])

        result = self.fetchall(query, params)

        events = []
        for row in result:
            event_data = json.loads(row[0])
            events.append(event_data)

        return events

    def delete_events_for_conversation(self, conversation_id: str):
        """Delete all events for a conversation.

        Args:
            conversation_id: Conversation ID
        """
        self.execute("DELETE FROM events WHERE conversation_id = ?", [conversation_id])
        logger.debug(f"Deleted events for conversation {conversation_id}")

    def delete_events_for_experiment(self, experiment_id: str):
        """Delete all events for an experiment.

        Args:
            experiment_id: Experiment ID
        """
        self.execute("DELETE FROM events WHERE experiment_id = ?", [experiment_id])
        logger.debug(f"Deleted events for experiment {experiment_id}")
