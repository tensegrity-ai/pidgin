"""Minimal state manager for testing event flow."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from ..core.events import Event


@dataclass
class MinimalDashboardState:
    """Just track basics to prove events work."""
    # Start with loading state
    experiment_name: str = "Waiting for experiment..."
    total_conversations: int = 0
    started_at: Optional[datetime] = None
    
    # Debug: count ALL events
    total_events: int = 0
    event_types_seen: Dict[str, int] = None
    
    def __post_init__(self):
        if self.event_types_seen is None:
            self.event_types_seen = {}


class MinimalStateManager:
    """Subscribe to EventBus and track state."""
    
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.state = MinimalDashboardState()
        print(f"[DEBUG] StateManager created for experiment {experiment_id}")
        
    def subscribe_to_bus(self, event_bus):
        """Subscribe to ALL events for debugging."""
        print("[DEBUG] Subscribing to EventBus...")
        event_bus.subscribe(Event, self.handle_event)
        
    async def handle_event(self, event: Event):
        """Handle any event - just count for now."""
        # Count every event
        self.state.total_events += 1
        event_type = event.__class__.__name__
        self.state.event_types_seen[event_type] = self.state.event_types_seen.get(event_type, 0) + 1
        
        print(f"[DEBUG] Event #{self.state.total_events}: {event_type}")
        
        # Look for experiment start
        if event_type == 'ExperimentStartEvent':
            print("[DEBUG] Got ExperimentStartEvent!")
            # The event might not have our expected structure yet
            # Be defensive about accessing attributes
            if hasattr(event, 'config'):
                config = event.config
                if isinstance(config, dict):
                    self.state.experiment_name = config.get('name', 'Unknown')
                    self.state.total_conversations = config.get('repetitions', 0)
                    self.state.started_at = datetime.now()