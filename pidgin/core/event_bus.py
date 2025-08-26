"""Central event distribution system."""

import asyncio
import json
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Type, TypeVar

from ..io.logger import get_logger
from .constants import SystemDefaults
from .events import Event

logger = get_logger("event_bus")


T = TypeVar("T", bound=Event)


class EventBus:
    """Central event distribution with radical transparency."""

    def __init__(
        self,
        db_store=None,
        event_log_dir=None,
        max_history_size: int = SystemDefaults.MAX_EVENT_HISTORY,
    ):
        """Initialize EventBus.

        Args:
            db_store: Optional EventStore for persisting events
            event_log_dir: Optional directory for JSONL event logs
            max_history_size: Maximum number of events to keep in history (default: 1000)
        """
        self.subscribers: Dict[Type[Event], List[Callable]] = defaultdict(list)
        self.event_history: List[Event] = []
        self.max_history_size = max_history_size
        self.db_store = db_store
        self.event_log_dir = event_log_dir
        self._running = False
        self._jsonl_files: Dict[str, Any] = {}  # conversation_id -> file handle
        self._jsonl_lock = threading.RLock()  # Protect JSONL file access (reentrant)
        self._history_lock = threading.RLock()  # Protect event history (reentrant)
        self._subscriber_lock = threading.RLock()  # Protect subscriber list (reentrant)

    def _serialize_value(self, value: Any) -> Any:
        """Convert a value to a JSON-serializable format."""
        # Handle None and basic types
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        # Handle datetime
        if hasattr(value, "isoformat"):
            return value.isoformat()

        # Handle collections
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}

        # Special check for Google GenerativeModel objects
        if hasattr(value, "_model_name") and hasattr(value, "_client"):
            # This is a Google GenerativeModel, extract just the model name
            return getattr(value, "_model_name", "unknown").replace("models/", "")

        # Handle specific object types
        if hasattr(value, "__dict__"):
            return self._serialize_object(value)

        # Fallback to string representation
        return str(value)

    def _serialize_object(self, obj: Any) -> Any:
        """Serialize an object to a dictionary."""
        # Special handling for Message objects
        if hasattr(obj, "role") and hasattr(obj, "content"):
            return {
                "role": obj.role,
                "content": obj.content,
                "agent_id": getattr(obj, "agent_id", None),
                "timestamp": (
                    obj.timestamp.isoformat() if hasattr(obj, "timestamp") else None
                ),
            }

        # Special handling for Google's GenerativeModel
        if hasattr(obj, "_model_name") and hasattr(obj, "_client"):
            # This is a Google GenerativeModel object, just return the model name
            return getattr(obj, "_model_name", str(obj))

        # Prevent serializing complex objects with sensitive data
        class_name = obj.__class__.__name__
        if any(
            sensitive in class_name.lower()
            for sensitive in ["client", "credential", "key", "token"]
        ):
            # Don't serialize objects that might contain credentials
            return f"<{class_name} object>"

        # Generic object serialization
        try:
            return {k: self._serialize_value(v) for k, v in obj.__dict__.items()}
        except Exception:
            # If we can't serialize it, just return string representation
            return str(obj)

    def _get_jsonl_file(self, conversation_id: str):
        """Get or create JSONL file handle for a conversation."""
        if not self.event_log_dir:
            return None

        with self._jsonl_lock:
            if conversation_id not in self._jsonl_files:
                # Create directory if needed
                log_dir = Path(self.event_log_dir)
                log_dir.mkdir(parents=True, exist_ok=True)

                # Open file in append mode - per-conversation file to avoid concurrency issues
                log_path = log_dir / f"events_{conversation_id}.jsonl"
                self._jsonl_files[conversation_id] = open(
                    log_path, "a", buffering=1
                )  # Line buffered

            return self._jsonl_files[conversation_id]

    def _write_to_jsonl(self, event: Event, event_data: dict):
        """Write event to JSONL file."""
        # Get conversation ID from event
        conversation_id = getattr(event, "conversation_id", None)
        if not conversation_id:
            return

        with self._jsonl_lock:
            try:
                jsonl_file = self._get_jsonl_file(conversation_id)
                if jsonl_file:
                    # First try to serialize to string to catch any issues
                    try:
                        json_str = json.dumps(event_data, separators=(",", ":"))
                    except Exception as e:
                        logger.error(
                            f"Failed to serialize event {type(event).__name__}: {e}"
                        )
                        # Try to identify the problematic field
                        for key, value in event_data.items():
                            try:
                                json.dumps({key: value})
                            except (TypeError, ValueError) as e:
                                logger.error(
                                    f"  Field '{key}' with type {type(value)} cannot be serialized: {e}"
                                )
                        return

                    # Write the pre-serialized string
                    jsonl_file.write(json_str)
                    jsonl_file.write("\n")
                    jsonl_file.flush()
            except Exception as e:
                logger.error(f"Error writing to JSONL: {e}")

    async def emit(self, event: Event) -> None:
        """Emit an event to all subscribers.

        Args:
            event: The event to emit
        """
        # Log to event history with size limit
        with self._history_lock:
            self.event_history.append(event)
            if len(self.event_history) > self.max_history_size:
                # Remove oldest events to maintain size limit
                self.event_history = self.event_history[-self.max_history_size :]

        # Prepare event data for serialization
        event_data = {}
        for k, v in event.__dict__.items():
            if k not in ["timestamp", "event_id"]:
                # Skip attributes that shouldn't be serialized
                if k == "model":
                    # Special handling for model field to prevent GenerativeModel objects
                    if hasattr(v, "_model_name"):
                        # This is a Google GenerativeModel object
                        event_data[k] = getattr(v, "_model_name", str(v))
                    elif hasattr(v, "model_name"):
                        # Alternative attribute name
                        event_data[k] = getattr(v, "model_name", str(v))
                    else:
                        # String or None - just use as is
                        event_data[k] = v
                else:
                    event_data[k] = self._serialize_value(v)

        # Add timestamp and event_type to the data
        event_data["timestamp"] = event.timestamp.isoformat()
        event_data["event_type"] = type(event).__name__

        # Add experiment_id if not present but conversation_id is
        if "experiment_id" not in event_data and hasattr(event, "conversation_id"):
            # Extract experiment_id from conversation_id format: conv_{experiment_id}_{uuid}
            # where experiment_id is like "experiment_b2a10065"
            conversation_id = getattr(event, "conversation_id", None)
            if conversation_id and conversation_id.startswith("conv_"):
                # Remove "conv_" prefix and split the rest
                remainder = conversation_id[5:]  # Skip "conv_"
                # Find the last underscore to separate experiment_id from uuid
                last_underscore = remainder.rfind("_")
                if last_underscore > 0:
                    event_data["experiment_id"] = remainder[:last_underscore]
                else:
                    event_data["experiment_id"] = None
            else:
                event_data["experiment_id"] = None

        # Write to JSONL if configured
        if self.event_log_dir:
            self._write_to_jsonl(event, event_data)

        # Note: Database writes are disabled during active experiments to avoid
        # concurrency issues. Database is populated via batch loading after completion.

        # Get handlers for this event type and parent types
        handlers = []

        # Check all registered event types
        with self._subscriber_lock:
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
                error_msg = f"Error in event handler {handler.__name__}: {e}"

                # Only show traceback in DEBUG mode
                import os

                if os.getenv("PIDGIN_DEBUG"):
                    logger.error(error_msg, exc_info=True)
                else:
                    # In normal mode, just show the error message
                    logger.error(error_msg)

    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """Subscribe to events of a specific type.

        Args:
            event_type: The type of event to subscribe to
            handler: The function to call when event is emitted
        """
        with self._subscriber_lock:
            self.subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """Unsubscribe from events.

        Args:
            event_type: The type of event to unsubscribe from
            handler: The handler to remove
        """
        with self._subscriber_lock:
            if handler in self.subscribers[event_type]:
                self.subscribers[event_type].remove(handler)

    def get_history(self, event_type: Type[T] = None) -> List[Event]:
        """Get event history, optionally filtered by type.

        Args:
            event_type: Optional event type to filter by

        Returns:
            List of events
        """
        with self._history_lock:
            if event_type is None:
                return self.event_history.copy()

            return [e for e in self.event_history if isinstance(e, event_type)]

    def clear_history(self) -> None:
        """Clear the event history."""
        with self._history_lock:
            self.event_history.clear()

    async def start(self):
        """Start the event bus."""
        self._running = True

    async def stop(self):
        """Stop event bus and close resources."""
        self._running = False

        # Close all JSONL files
        with self._jsonl_lock:
            for file_handle in self._jsonl_files.values():
                try:
                    file_handle.close()
                except Exception as e:
                    logger.error(f"Error closing JSONL file: {e}")
            self._jsonl_files.clear()

    def close_conversation_log(self, conversation_id: str) -> None:
        """Close JSONL file for a specific conversation.

        Args:
            conversation_id: The conversation ID whose log to close
        """
        with self._jsonl_lock:
            if conversation_id in self._jsonl_files:
                try:
                    self._jsonl_files[conversation_id].close()
                    del self._jsonl_files[conversation_id]
                    logger.debug(
                        f"Closed JSONL file for conversation {conversation_id}"
                    )
                except Exception as e:
                    logger.error(f"Error closing JSONL file for {conversation_id}: {e}")
