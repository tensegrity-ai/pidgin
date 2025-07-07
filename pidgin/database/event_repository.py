"""Repository for event operations."""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from .base_repository import BaseRepository
from ..core.events import Event
from ..io.logger import get_logger

logger = get_logger("event_repository")


class EventRepository(BaseRepository):
    """Repository for event storage and retrieval."""
    
    def save_event(self, event: Event, experiment_id: str, conversation_id: str):
        """Save an event to the database.
        
        Args:
            event: Event to save
            experiment_id: Experiment ID
            conversation_id: Conversation ID
        """
        query = """
            INSERT INTO events (
                timestamp, event_type, conversation_id, 
                experiment_id, event_data, sequence
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        
        # Get next sequence number for this conversation
        seq_result = self.fetchone(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM events WHERE conversation_id = ?",
            [conversation_id]
        )
        sequence = seq_result[0] if seq_result else 1
        
        # Convert event to dict for storage
        event_dict = {
            "event_type": event.__class__.__name__,
            "conversation_id": conversation_id,
            "timestamp": event.timestamp.isoformat(),
            "event_id": event.event_id
        }
        
        # Add event-specific fields
        for field_name in event.__dataclass_fields__:
            if field_name not in ["timestamp", "event_id"]:
                value = getattr(event, field_name)
                if hasattr(value, "isoformat"):
                    event_dict[field_name] = value.isoformat()
                elif hasattr(value, "__dict__"):
                    event_dict[field_name] = value.__dict__
                else:
                    event_dict[field_name] = value
        
        self.execute(query, [
            event.timestamp,
            event.__class__.__name__,
            conversation_id,
            experiment_id,
            json.dumps(event_dict),
            sequence
        ])
        
        logger.debug(f"Saved {event.__class__.__name__} for conversation {conversation_id}")
    
    def get_events(
        self,
        conversation_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
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
        params = []
        
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
            params.append(start_time)
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        
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