"""Event bus with DuckDB persistence for event sourcing."""

import asyncio
import json
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Type, TypeVar, Optional, Any
from datetime import datetime

from ..core.events import Event
from ..io.logger import get_logger
from .async_duckdb import AsyncDuckDB

logger = get_logger("event_bus_db")

T = TypeVar("T", bound=Event)


class DatabaseEventBus:
    """Event bus that persists events to DuckDB for event sourcing."""
    
    def __init__(self, db_path: Path, conversation_id: Optional[str] = None,
                 experiment_id: Optional[str] = None):
        """Initialize event bus with database persistence.
        
        Args:
            db_path: Path to DuckDB database
            conversation_id: Optional conversation ID for all events
            experiment_id: Optional experiment ID for all events
        """
        self.subscribers: Dict[Type[Event], List[Callable]] = defaultdict(list)
        self.event_history: List[Event] = []
        self.db = AsyncDuckDB(db_path)
        self.conversation_id = conversation_id
        self.experiment_id = experiment_id
        self._running = False
        
        # Event buffer for batch writing
        self._event_buffer = []
        self._buffer_lock = asyncio.Lock()
        self._flush_task = None
    
    def _serialize_value(self, value: Any) -> Any:
        """Convert a value to a JSON-serializable format."""
        if value is None:
            return None
        
        if isinstance(value, (str, int, float, bool)):
            return value
        
        if hasattr(value, "isoformat"):
            return value.isoformat()
        
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        
        # Handle objects with __dict__
        if hasattr(value, "__dict__"):
            # Special handling for Message objects
            if hasattr(value, "role") and hasattr(value, "content"):
                return {
                    "role": value.role,
                    "content": value.content,
                    "agent_id": getattr(value, "agent_id", None),
                    "timestamp": value.timestamp.isoformat()
                    if hasattr(value, "timestamp")
                    else None,
                }
            else:
                # Generic object serialization
                return {k: self._serialize_value(v) for k, v in value.__dict__.items()}
        
        # Fallback to string representation
        return str(value)
    
    async def emit(self, event: Event) -> None:
        """Emit an event to all subscribers and persist to database.
        
        Args:
            event: The event to emit
        """
        # Add to history
        self.event_history.append(event)
        
        # Prepare event data
        event_data = {}
        for k, v in event.__dict__.items():
            if k not in ["timestamp", "event_id"]:
                event_data[k] = self._serialize_value(v)
        
        # Use conversation/experiment ID from event if available
        conv_id = self.conversation_id
        exp_id = self.experiment_id
        
        if hasattr(event, 'conversation_id'):
            conv_id = event.conversation_id
        if hasattr(event, 'experiment_id'):
            exp_id = event.experiment_id
        
        # Add to buffer for batch writing
        async with self._buffer_lock:
            self._event_buffer.append({
                'event_type': type(event).__name__,
                'conversation_id': conv_id,
                'experiment_id': exp_id,
                'event_data': json.dumps(event_data),
                'timestamp': event.timestamp
            })
        
        # Schedule flush if not already scheduled
        if not self._flush_task or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_buffer())
        
        # Get handlers for this event type and parent types
        handlers = []
        for event_type, handler_list in self.subscribers.items():
            if isinstance(event, event_type):
                handlers.extend(handler_list)
        
        # Notify all subscribers
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler {handler.__name__}: {e}", exc_info=True)
    
    async def _flush_buffer(self):
        """Flush event buffer to database."""
        await asyncio.sleep(0.1)  # Small delay for batching
        
        async with self._buffer_lock:
            if not self._event_buffer:
                return
            
            events_to_write = self._event_buffer.copy()
            self._event_buffer.clear()
        
        # Batch insert events
        try:
            if events_to_write:
                # Prepare batch insert
                query = """
                    INSERT INTO events (event_type, conversation_id, experiment_id, event_data, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """
                
                params_list = [
                    (e['event_type'], e['conversation_id'], e['experiment_id'], 
                     e['event_data'], e['timestamp'])
                    for e in events_to_write
                ]
                
                await self.db.executemany(query, params_list)
                
                logger.debug(f"Flushed {len(events_to_write)} events to database")
                
        except Exception as e:
            logger.error(f"Error flushing events to database: {e}", exc_info=True)
    
    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """Subscribe to events of a specific type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: The function to call when event is emitted
        """
        self.subscribers[event_type].append(handler)
    
    def unsubscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """Unsubscribe from events.
        
        Args:
            event_type: The type of event to unsubscribe from
            handler: The handler to remove
        """
        if handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)
    
    def get_history(self, event_type: Type[T] = None) -> List[Event]:
        """Get in-memory event history, optionally filtered by type.
        
        Args:
            event_type: Optional event type to filter by
            
        Returns:
            List of events
        """
        if event_type is None:
            return self.event_history.copy()
        
        return [e for e in self.event_history if isinstance(e, event_type)]
    
    async def get_persisted_events(self, event_type: Optional[str] = None,
                                  since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get events from database.
        
        Args:
            event_type: Optional event type to filter by
            since: Optional timestamp to get events after
            
        Returns:
            List of event dictionaries
        """
        conditions = []
        params = []
        
        if self.conversation_id:
            conditions.append("conversation_id = ?")
            params.append(self.conversation_id)
        
        if self.experiment_id:
            conditions.append("experiment_id = ?")
            params.append(self.experiment_id)
        
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        
        if since:
            conditions.append("timestamp > ?")
            params.append(since)
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
            SELECT event_id, timestamp, event_type, conversation_id, 
                   experiment_id, event_data
            FROM events
            {where_clause}
            ORDER BY timestamp
        """
        
        return await self.db.fetch_all(query, tuple(params))
    
    def clear_history(self) -> None:
        """Clear in-memory event history."""
        self.event_history.clear()
    
    async def start(self):
        """Start the event bus."""
        self._running = True
        # Initialize database schema if needed
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT now(),
                event_type TEXT NOT NULL,
                conversation_id TEXT,
                experiment_id TEXT,
                event_data JSON
            )
        """)
        
        # Create indexes if they don't exist
        await self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_conversation ON events(conversation_id)"
        )
        await self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_experiment ON events(experiment_id)"
        )
        await self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)"
        )
        
        # Start batch processor
        self.db.start_batch_processor()
    
    async def stop(self):
        """Stop the event bus and flush remaining events."""
        self._running = False
        
        # Final flush
        async with self._buffer_lock:
            if self._event_buffer:
                await self._flush_buffer()
        
        # Stop batch processor
        self.db.stop_batch_processor()
    
    async def close(self):
        """Close database connections."""
        await self.stop()
        await self.db.close()


def create_database_event_bus(db_path: Path, conversation_id: Optional[str] = None,
                             experiment_id: Optional[str] = None) -> DatabaseEventBus:
    """Create a database-backed event bus.
    
    Args:
        db_path: Path to DuckDB database
        conversation_id: Optional conversation ID
        experiment_id: Optional experiment ID
        
    Returns:
        DatabaseEventBus instance
    """
    return DatabaseEventBus(db_path, conversation_id, experiment_id)