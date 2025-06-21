"""Event log replayer for catching up dashboard state."""

import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ..core.event_bus import EventBus
from ..core.events import (
    Event,
    ConversationStartEvent,
    TurnCompleteEvent,
    ConversationEndEvent,
    MessageCompleteEvent,
    MetricsCalculatedEvent,
    SystemPromptEvent,
    TurnStartEvent,
    MessageRequestEvent,
)


class EventLogReplayer:
    """Replay events from log to catch up dashboard state."""
    
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        
    def _find_event_logs(self) -> List[Path]:
        """Find all event log files for this experiment."""
        base_dir = Path("pidgin_output") / "experiments" / self.experiment_id
        event_logs = []
        
        if base_dir.exists():
            # Find all events.jsonl files in conversation directories
            for conv_dir in base_dir.glob("*_conv_*"):
                event_log = conv_dir / "events.jsonl"
                if event_log.exists():
                    event_logs.append(event_log)
                    
        return sorted(event_logs)  # Sort to process in order
        
    def _reconstruct_event(self, event_data: Dict[str, Any]) -> Optional[Event]:
        """Reconstruct event object from JSON data."""
        event_type = event_data.get('type', '')
        
        # Map event types to classes
        event_classes = {
            'ConversationStartEvent': ConversationStartEvent,
            'TurnCompleteEvent': TurnCompleteEvent,
            'ConversationEndEvent': ConversationEndEvent,
            'MessageCompleteEvent': MessageCompleteEvent,
            'MetricsCalculatedEvent': MetricsCalculatedEvent,
            'SystemPromptEvent': SystemPromptEvent,
            'TurnStartEvent': TurnStartEvent,
            'MessageRequestEvent': MessageRequestEvent,
        }
        
        event_class = event_classes.get(event_type)
        if not event_class:
            return None
            
        # Remove type and timestamp fields
        event_data = event_data.copy()
        event_data.pop('type', None)
        event_data.pop('timestamp', None)
        event_data.pop('event_id', None)
        
        try:
            # Special handling for complex events
            if event_type == 'TurnCompleteEvent' and 'turn' in event_data:
                # Reconstruct Turn object
                from ..core.events import Turn
                from ..core.types import Message
                
                turn_data = event_data['turn']
                turn = Turn(
                    agent_a_message=Message(**turn_data['agent_a_message']),
                    agent_b_message=Message(**turn_data['agent_b_message']),
                    intervention=None
                )
                event_data['turn'] = turn
                
            elif event_type == 'MessageCompleteEvent' and 'message' in event_data:
                # Reconstruct Message object
                from ..core.types import Message
                event_data['message'] = Message(**event_data['message'])
                
            return event_class(**event_data)
            
        except Exception as e:
            # Skip events we can't reconstruct
            return None
            
    async def replay_recent_events(self, event_bus: EventBus, last_n_turns: int = 5):
        """Replay recent events to populate dashboard state."""
        event_logs = self._find_event_logs()
        
        if not event_logs:
            return
            
        # Collect all events with timestamps
        all_events = []
        
        for log_path in event_logs:
            with open(log_path, 'r') as f:
                for line in f:
                    try:
                        event_data = json.loads(line.strip())
                        event = self._reconstruct_event(event_data)
                        if event:
                            all_events.append(event)
                    except:
                        pass
                        
        # Sort by timestamp if available
        # For now, just use the order in the file
        
        # Find key events to replay
        events_to_replay = []
        
        # Always replay experiment start and conversation starts
        for event in all_events:
            if isinstance(event, (ConversationStartEvent, SystemPromptEvent)):
                events_to_replay.append(event)
                
        # Find last N turns and their metrics
        turn_events = []
        for event in all_events:
            if isinstance(event, (TurnStartEvent, TurnCompleteEvent, MetricsCalculatedEvent)):
                turn_events.append(event)
                
        # Take last N turns worth of events
        if turn_events:
            events_to_replay.extend(turn_events[-last_n_turns * 3:])  # 3 events per turn
            
        # Add any message complete events from recent turns
        recent_messages = []
        for event in reversed(all_events):
            if isinstance(event, MessageCompleteEvent):
                recent_messages.append(event)
                if len(recent_messages) >= last_n_turns * 2:  # 2 messages per turn
                    break
                    
        events_to_replay.extend(reversed(recent_messages))
        
        # Emit events with small delays to avoid overwhelming
        for event in events_to_replay:
            await event_bus.emit(event)
            await asyncio.sleep(0.01)  # Small delay between events
            
        # Finally, emit a custom catch-up complete event
        @dataclass
        class CatchUpCompleteEvent(Event):
            """Dashboard has caught up with historical events."""
            experiment_id: str
            events_replayed: int
            
        await event_bus.emit(CatchUpCompleteEvent(
            experiment_id=self.experiment_id,
            events_replayed=len(events_to_replay)
        ))