"""State manager tracking multiple metrics."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Deque
from collections import deque

from ..core.events import Event


@dataclass  
class DashboardState:
    """Track experiment progress and multiple metrics."""
    # Experiment info
    experiment_name: str = "Loading..."
    total_conversations: int = 0
    started_at: Optional[datetime] = None
    
    # Progress tracking
    current_conversation: int = 0
    current_turn: int = 0
    completed_conversations: int = 0
    
    # Turn metrics sparklines
    convergence_history: Deque[float] = field(default_factory=lambda: deque(maxlen=20))
    vocabulary_overlap_history: Deque[float] = field(default_factory=lambda: deque(maxlen=20))
    ttr_a_history: Deque[float] = field(default_factory=lambda: deque(maxlen=20))
    ttr_b_history: Deque[float] = field(default_factory=lambda: deque(maxlen=20))
    
    # Message metrics sparklines  
    length_a_history: Deque[int] = field(default_factory=lambda: deque(maxlen=20))
    length_b_history: Deque[int] = field(default_factory=lambda: deque(maxlen=20))
    words_a_history: Deque[int] = field(default_factory=lambda: deque(maxlen=20))
    words_b_history: Deque[int] = field(default_factory=lambda: deque(maxlen=20))
    
    # Latest values
    latest_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Message ticker
    recent_messages: Deque[Dict[str, str]] = field(default_factory=lambda: deque(maxlen=6))
    
    # Debug
    total_events: int = 0


class DashboardStateManager:
    """Manage dashboard state from events."""
    
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.state = DashboardState()
        print(f"[DEBUG] StateManager created for experiment {experiment_id}")
        
    def subscribe_to_bus(self, event_bus):
        """Subscribe to events."""
        print(f"[DEBUG] Subscribing to EventBus...")
        event_bus.subscribe(Event, self.handle_event)
        
    async def handle_event(self, event: Event):
        """Handle events and update state."""
        self.state.total_events += 1
        event_type = event.__class__.__name__
        
        print(f"[DEBUG] Event #{self.state.total_events}: {event_type}")
        
        if event_type == 'ExperimentStartEvent':
            print(f"[DEBUG] Got ExperimentStartEvent!")
            if hasattr(event, 'config') and isinstance(event.config, dict):
                self.state.experiment_name = event.config.get('name', 'Unknown')
                self.state.total_conversations = event.config.get('repetitions', 0)
                self.state.started_at = datetime.now()
                    
        elif event_type == 'ConversationStartEvent':
            self.state.current_conversation += 1
            self.state.current_turn = 0
            
        elif event_type == 'TurnCompleteEvent':
            self.state.current_turn += 1
            
        elif event_type == 'MessageCompleteEvent':
            # Add to message ticker
            if hasattr(event, 'message') and hasattr(event, 'agent_id'):
                content = event.message.content
                preview = content[:80] + "..." if len(content) > 80 else content
                # Clean up preview - remove newlines
                preview = preview.replace('\n', ' ').strip()
                self.state.recent_messages.append({
                    'agent': 'A' if event.agent_id == 'agent_a' else 'B',
                    'preview': preview,
                    'turn': self.state.current_turn
                })
            
        elif event_type == 'MetricsCalculatedEvent':
            # Update all metrics
            if hasattr(event, 'metrics') and isinstance(event.metrics, dict):
                metrics = event.metrics
                self.state.latest_metrics = metrics
                
                # Turn metrics
                if 'convergence_score' in metrics:
                    self.state.convergence_history.append(metrics['convergence_score'])
                if 'vocabulary_overlap' in metrics:
                    self.state.vocabulary_overlap_history.append(metrics['vocabulary_overlap'])
                    
                # Extract agent metrics from nested structure
                agent_a = metrics.get('agent_a', {})
                agent_b = metrics.get('agent_b', {})
                
                # TTR metrics
                if 'type_token_ratio' in agent_a:
                    self.state.ttr_a_history.append(agent_a['type_token_ratio'])
                if 'type_token_ratio' in agent_b:
                    self.state.ttr_b_history.append(agent_b['type_token_ratio'])
                    
                # Message metrics
                if 'message_length' in agent_a:
                    self.state.length_a_history.append(agent_a['message_length'])
                if 'message_length' in agent_b:
                    self.state.length_b_history.append(agent_b['message_length'])
                if 'word_count' in agent_a:
                    self.state.words_a_history.append(agent_a['word_count'])
                if 'word_count' in agent_b:
                    self.state.words_b_history.append(agent_b['word_count'])
                
        elif event_type == 'ConversationEndEvent':
            self.state.completed_conversations += 1


# Keep the old classes for backward compatibility
MinimalDashboardState = DashboardState
MinimalStateManager = DashboardStateManager