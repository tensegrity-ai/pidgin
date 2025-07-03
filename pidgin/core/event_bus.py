"""Central event distribution system."""

import asyncio
from collections import defaultdict
from typing import Callable, Dict, List, Type, TypeVar, Optional, Any

from .events import Event
from ..io.logger import get_logger

logger = get_logger("event_bus")


T = TypeVar("T", bound=Event)


class EventBus:
    """Central event distribution with radical transparency."""

    def __init__(self, db_store=None):
        """Initialize EventBus.
        
        Args:
            db_store: Optional EventStore for persisting events
        """
        self.subscribers: Dict[Type[Event], List[Callable]] = defaultdict(list)
        self.event_history: List[Event] = []
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.db_store = db_store
        self._running = False
        self._processor_task = None

    def _serialize_value(self, value: Any) -> Any:
        """Convert a value to a JSON-serializable format."""
        # Handle None
        if value is None:
            return None

        # Handle basic types
        if isinstance(value, (str, int, float, bool)):
            return value

        # Handle datetime
        if hasattr(value, "isoformat"):
            return value.isoformat()

        # Handle lists
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]

        # Handle dicts
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}

        # Handle objects with __dict__
        if hasattr(value, "__dict__"):
            # For Message objects, extract key fields
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
        """Emit an event to all subscribers.

        Args:
            event: The event to emit
        """
        # Log to event history
        self.event_history.append(event)

        # Queue for processing (for backward compatibility)
        await self.event_queue.put(event)

        # Write to database if configured
        if self.db_store and self._running:
            try:
                # Convert event data to serializable format
                event_data = {}
                for k, v in event.__dict__.items():
                    if k not in ["timestamp", "event_id"]:
                        event_data[k] = self._serialize_value(v)

                # Add timestamp and event_type to the data
                event_data["timestamp"] = event.timestamp.isoformat()
                event_data["event_type"] = type(event).__name__

                # Emit to database
                await self.db_store.emit_event(
                    event_type=type(event).__name__,
                    conversation_id=getattr(event, 'conversation_id', None),
                    experiment_id=getattr(event, 'experiment_id', None),
                    data=event_data
                )
            except Exception as e:
                logger.error(f"Error storing event {type(event).__name__}: {e}")

        # Get handlers for this event type and parent types
        handlers = []

        # Check all registered event types
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
                # Log but don't crash on handler errors
                logger.error(f"Error in event handler {handler.__name__}: {e}", exc_info=True)

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
        """Get event history, optionally filtered by type.

        Args:
            event_type: Optional event type to filter by

        Returns:
            List of events
        """
        if event_type is None:
            return self.event_history.copy()

        return [e for e in self.event_history if isinstance(e, event_type)]

    def clear_history(self) -> None:
        """Clear the event history."""
        self.event_history.clear()

    async def start(self):
        """Start the event processor."""
        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        # Give the processor task a chance to start
        await asyncio.sleep(0)

    async def stop(self):
        """Stop processor."""
        self._running = False
        if self._processor_task:
            # Put a None to unblock the processor
            await self.event_queue.put(None)
            await self._processor_task
            self._processor_task = None

    async def _process_events(self):
        """Process events from queue."""
        while self._running:
            try:
                event = await self.event_queue.get()

                # Check for stop signal
                if event is None:
                    break

                # Event processing is now handled in emit()
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
