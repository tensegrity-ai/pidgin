"""Repository for event storage and retrieval."""

import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import BaseRepository
from ...io.logger import get_logger

logger = get_logger("event_repository")


class EventRepository(BaseRepository):
    """Handles event storage and retrieval operations."""
    
    async def emit_event(
        self,
        event_type: str,
        conversation_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Emit an event to the database.
        
        Args:
            event_type: Type of event
            conversation_id: Optional conversation ID
            experiment_id: Optional experiment ID
            data: Event data payload
            
        Returns:
            Event ID
        """
        event_id = uuid.uuid4().hex
        timestamp = datetime.now()
        
        # Prepare the query
        query = """
            INSERT INTO events (
                event_id, event_type, conversation_id, experiment_id, 
                data, timestamp, sequence_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING event_id
        """
        
        params = (
            event_id,
            event_type,
            conversation_id,
            experiment_id,
            json.dumps(data or {}),
            timestamp,
            0  # sequence number, can be implemented later
        )
        
        # Execute query
        await self.execute_query(query, params)
        
        # Get the returned event_id
        result = await self.db.fetchone()
        if result and "event_id" in result:
            return result["event_id"]
        
        # Fallback to generated ID
        return event_id
    
    async def get_events(
        self,
        conversation_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve events with optional filters.
        
        Args:
            conversation_id: Filter by conversation
            experiment_id: Filter by experiment
            event_type: Filter by event type
            since: Filter events after this time
            until: Filter events before this time
            limit: Maximum number of events to return
            
        Returns:
            List of event dictionaries
        """
        # Build query
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if conversation_id:
            query += " AND conversation_id = ?"
            params.append(conversation_id)
        
        if experiment_id:
            query += " AND experiment_id = ?"
            params.append(experiment_id)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if since:
            query += " AND timestamp >= ?"
            params.append(since)
        
        if until:
            query += " AND timestamp <= ?"
            params.append(until)
        
        # Order by timestamp
        query += " ORDER BY timestamp ASC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        # Execute query
        events = await self.fetch_all(query, tuple(params))
        
        # Parse JSON data field
        for event in events:
            if "data" in event and isinstance(event["data"], str):
                try:
                    event["data"] = json.loads(event["data"])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse event data for {event.get('event_id')}")
        
        return events
    
    async def search_events(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        experiment_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search events by content.
        
        Args:
            query: Search query
            conversation_id: Optional conversation filter
            experiment_id: Optional experiment filter
            
        Returns:
            List of matching events
        """
        # Build search query
        sql = """
            SELECT * FROM events 
            WHERE data::TEXT LIKE ?
        """
        params = [f"%{query}%"]
        
        if conversation_id:
            sql += " AND conversation_id = ?"
            params.append(conversation_id)
        
        if experiment_id:
            sql += " AND experiment_id = ?"
            params.append(experiment_id)
        
        sql += " ORDER BY timestamp DESC"
        
        # Execute search
        events = await self.fetch_all(sql, tuple(params))
        
        # Parse JSON data
        for event in events:
            if "data" in event and isinstance(event["data"], str):
                try:
                    event["data"] = json.loads(event["data"])
                except json.JSONDecodeError:
                    pass
        
        return events
    
    async def get_event_count(
        self,
        conversation_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> int:
        """Get count of events matching criteria.
        
        Args:
            conversation_id: Optional conversation filter
            experiment_id: Optional experiment filter
            event_type: Optional event type filter
            
        Returns:
            Count of matching events
        """
        query = "SELECT COUNT(*) as count FROM events WHERE 1=1"
        params = []
        
        if conversation_id:
            query += " AND conversation_id = ?"
            params.append(conversation_id)
        
        if experiment_id:
            query += " AND experiment_id = ?"
            params.append(experiment_id)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        result = await self.fetch_one(query, tuple(params))
        return result["count"] if result else 0
    
    async def delete_events(
        self,
        conversation_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        before: Optional[datetime] = None
    ) -> int:
        """Delete events matching criteria.
        
        Args:
            conversation_id: Delete events for this conversation
            experiment_id: Delete events for this experiment
            before: Delete events before this time
            
        Returns:
            Number of deleted events
        """
        if not any([conversation_id, experiment_id, before]):
            raise ValueError("Must specify at least one deletion criteria")
        
        query = "DELETE FROM events WHERE 1=1"
        params = []
        
        if conversation_id:
            query += " AND conversation_id = ?"
            params.append(conversation_id)
        
        if experiment_id:
            query += " AND experiment_id = ?"
            params.append(experiment_id)
        
        if before:
            query += " AND timestamp < ?"
            params.append(before)
        
        # Execute deletion
        await self.execute_query(query, tuple(params))
        
        # Return affected rows (would need to implement in AsyncDuckDB)
        return 0  # Placeholder