"""Central event distribution system."""

import asyncio
import json
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Type, TypeVar, Optional, Any

from .events import Event
from .logger import get_logger

logger = get_logger("event_bus")


T = TypeVar("T", bound=Event)


class EventBus:
    """Central event distribution with radical transparency."""

    def __init__(self, event_log_path: Optional[Path] = None):
        self.subscribers: Dict[Type[Event], List[Callable]] = defaultdict(list)
        self.event_history: List[Event] = []
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.event_log_path = event_log_path
        self._event_file = None
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

        # Write to file immediately if configured
        if self._event_file and self._running:
            try:
                # Convert event data to serializable format
                event_data = {}
                for k, v in event.__dict__.items():
                    if k not in ["timestamp", "event_id"]:
                        event_data[k] = self._serialize_value(v)

                event_dict = {
                    "timestamp": event.timestamp.isoformat(),
                    "event_type": type(event).__name__,
                    "data": event_data,
                }
                json_str = json.dumps(event_dict)
                self._event_file.write(json_str + "\n")
                self._event_file.flush()  # Ensure it's written immediately
            except Exception as e:
                logger.error(f"Error writing event {type(event).__name__}: {e}")

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
        """Start the event processor and open log file."""
        if self.event_log_path:
            self._event_file = open(self.event_log_path, "w")
            # print(f"Opened event log file: {self.event_log_path}")
        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        # Give the processor task a chance to start
        await asyncio.sleep(0)

    async def stop(self):
        """Stop processor and close log file."""
        self._running = False
        if self._event_file:
            self._event_file.close()
            self._event_file = None
        if self._processor_task:
            # Put a None to unblock the processor
            await self.event_queue.put(None)
            await self._processor_task
            self._processor_task = None

    async def _process_events(self):
        """Process events and write to file."""
        # print(f"Event processor started, running={self._running}")
        while self._running:
            try:
                event = await self.event_queue.get()

                # Check for stop signal
                if event is None:
                    break

                # Write to file if configured (removed - now handled in emit())
                pass
                # else:
                #     print(f"WARNING: No event file open for writing")
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
