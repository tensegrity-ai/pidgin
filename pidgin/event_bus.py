"""Central event distribution system."""

import asyncio
from collections import defaultdict
from typing import Callable, Dict, List, Type, TypeVar

from .events import Event


T = TypeVar('T', bound=Event)


class EventBus:
    """Central event distribution with radical transparency."""
    
    def __init__(self):
        self.subscribers: Dict[Type[Event], List[Callable]] = defaultdict(list)
        self.event_history: List[Event] = []
        self.event_queue: asyncio.Queue = asyncio.Queue()
        
    async def emit(self, event: Event) -> None:
        """Emit an event to all subscribers.
        
        Args:
            event: The event to emit
        """
        # Log to event history
        self.event_history.append(event)
        
        # Queue for processing
        await self.event_queue.put(event)
        
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
                print(f"Error in event handler {handler.__name__}: {e}")
    
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