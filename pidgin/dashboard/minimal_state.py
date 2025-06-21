"""Enhanced state manager that tracks turns and metrics."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Deque
from collections import deque

from ..core.events import Event


@dataclass  
class MinimalDashboardState:
    """Track experiment progress and metrics."""
    # Experiment info
    experiment_name: str = "Waiting for experiment..."
    total_conversations: int = 0
    started_at: Optional[datetime] = None
    
    # Progress tracking
    current_conversation: int = 0
    current_turn: int = 0
    completed_conversations: int = 0
    
    # Metrics tracking - NEW!
    convergence_history: Deque[float] = field(default_factory=lambda: deque(maxlen=20))
    latest_convergence: float = 0.0
    
    # Debug
    total_events: int = 0
    event_types_seen: Dict[str, int] = field(default_factory=dict)


class MinimalStateManager:
    """Subscribe to EventBus and track state."""
    
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.state = MinimalDashboardState()
        print(f"[DEBUG] StateManager created for experiment {experiment_id}")
        
    def subscribe_to_bus(self, event_bus):
        """Subscribe to ALL events."""
        print(f"[DEBUG] Subscribing to EventBus...")
        event_bus.subscribe(Event, self.handle_event)
        
    async def handle_event(self, event: Event):
        """Handle any event."""
        # Count every event
        self.state.total_events += 1
        event_type = event.__class__.__name__
        self.state.event_types_seen[event_type] = self.state.event_types_seen.get(event_type, 0) + 1
        
        print(f"[DEBUG] Event #{self.state.total_events}: {event_type}")
        
        # Handle specific events
        if event_type == 'ExperimentStartEvent':
            print(f"[DEBUG] Got ExperimentStartEvent!")
            if hasattr(event, 'config'):
                config = event.config
                if isinstance(config, dict):
                    self.state.experiment_name = config.get('name', 'Unknown')
                    self.state.total_conversations = config.get('repetitions', 0)
                    self.state.started_at = datetime.now()
                    
        elif event_type == 'ConversationStartEvent':
            self.state.current_conversation += 1
            self.state.current_turn = 0
            
        elif event_type == 'TurnCompleteEvent':
            self.state.current_turn += 1
            
        elif event_type == 'MetricsCalculatedEvent':
            # Extract convergence score!
            if hasattr(event, 'metrics') and isinstance(event.metrics, dict):
                convergence = event.metrics.get('convergence_score', 0.0)
                self.state.latest_convergence = convergence
                self.state.convergence_history.append(convergence)
                
        elif event_type == 'ConversationEndEvent':
            self.state.completed_conversations += 1