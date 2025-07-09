"""Deserialize JSONL events back to Event dataclasses."""

import json
from datetime import datetime
from typing import Dict, Any, Optional, Type
from pathlib import Path

from ..core.events import (
    Event,
    ConversationStartEvent,
    ConversationEndEvent,
    TurnCompleteEvent,
    MessageCompleteEvent,
    Turn,
    SystemPromptEvent,
    ErrorEvent,
)
from ..core.types import Message
from ..io.logger import get_logger

logger = get_logger("event_deserializer")


class EventDeserializer:
    """Deserialize JSON events back to Event dataclasses."""
    
    # Map event type strings to event classes
    EVENT_TYPES: Dict[str, Type[Event]] = {
        "ConversationStartEvent": ConversationStartEvent,
        "ConversationEndEvent": ConversationEndEvent,
        "TurnCompleteEvent": TurnCompleteEvent,
        "MessageCompleteEvent": MessageCompleteEvent,
        "SystemPromptEvent": SystemPromptEvent,
        "ErrorEvent": ErrorEvent,
        # Handle legacy names
        "ConversationCreated": ConversationStartEvent,
    }
    
    @classmethod
    def deserialize_event(cls, event_data: Dict[str, Any]) -> Optional[Event]:
        """Deserialize a JSON event to its corresponding Event dataclass.
        
        Args:
            event_data: JSON event data
            
        Returns:
            Event instance or None if unknown event type
        """
        event_type = event_data.get("event_type")
        if not event_type:
            logger.warning("Event missing event_type field")
            return None
            
        event_class = cls.EVENT_TYPES.get(event_type)
        if not event_class:
            # Unknown event type - log but don't fail
            logger.debug(f"Unknown event type: {event_type}")
            return None
            
        try:
            # Parse timestamp if present
            timestamp_str = event_data.get("timestamp")
            timestamp = cls._parse_timestamp(timestamp_str) if timestamp_str else datetime.now()
            
            # Build event based on type
            if event_type == "ConversationStartEvent":
                return cls._build_conversation_start(event_data, timestamp)
            elif event_type == "ConversationEndEvent":
                return cls._build_conversation_end(event_data, timestamp)
            elif event_type == "TurnCompleteEvent":
                return cls._build_turn_complete(event_data, timestamp)
            elif event_type == "MessageCompleteEvent":
                return cls._build_message_complete(event_data, timestamp)
            elif event_type == "SystemPromptEvent":
                return cls._build_system_prompt(event_data, timestamp)
            elif event_type == "ErrorEvent":
                return cls._build_error(event_data, timestamp)
            else:
                logger.warning(f"No builder for event type: {event_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to deserialize {event_type}: {e}")
            return None
    
    @staticmethod
    def _parse_timestamp(timestamp_str: str) -> datetime:
        """Parse ISO timestamp string to datetime."""
        try:
            # Handle timezone-aware timestamps
            if "+" in timestamp_str or timestamp_str.endswith("Z"):
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError, AttributeError):
            # Fallback to now if parsing fails (invalid format, None, or not a string)
            return datetime.now()
    
    @classmethod
    def _build_conversation_start(cls, data: Dict[str, Any], timestamp: datetime) -> ConversationStartEvent:
        """Build ConversationStartEvent from JSON data."""
        event = ConversationStartEvent(
            conversation_id=data.get("conversation_id", ""),
            agent_a_model=data.get("agent_a_model", ""),
            agent_b_model=data.get("agent_b_model", ""),
            initial_prompt=data.get("initial_prompt", ""),
            max_turns=data.get("max_turns", 0),
            agent_a_display_name=data.get("agent_a_display_name"),
            agent_b_display_name=data.get("agent_b_display_name"),
            temperature_a=data.get("temperature_a"),
            temperature_b=data.get("temperature_b"),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event
    
    @classmethod
    def _build_conversation_end(cls, data: Dict[str, Any], timestamp: datetime) -> ConversationEndEvent:
        """Build ConversationEndEvent from JSON data."""
        event = ConversationEndEvent(
            conversation_id=data.get("conversation_id", ""),
            reason=data.get("reason", "unknown"),
            total_turns=data.get("total_turns", 0),
            duration_ms=data.get("duration_ms", 0),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event
    
    @classmethod
    def _build_turn_complete(cls, data: Dict[str, Any], timestamp: datetime) -> TurnCompleteEvent:
        """Build TurnCompleteEvent from JSON data."""
        turn_data = data.get("turn", {})
        
        # Extract messages from turn data
        msg_a_data = turn_data.get("agent_a_message", {})
        msg_b_data = turn_data.get("agent_b_message", {})
        
        msg_a = Message(
            role="assistant",
            content=msg_a_data.get("content", ""),
            agent_id="agent_a",
            timestamp=cls._parse_timestamp(msg_a_data.get("timestamp", "")) if msg_a_data.get("timestamp") else timestamp
        )
        
        msg_b = Message(
            role="assistant",
            content=msg_b_data.get("content", ""),
            agent_id="agent_b",
            timestamp=cls._parse_timestamp(msg_b_data.get("timestamp", "")) if msg_b_data.get("timestamp") else timestamp
        )
        
        turn = Turn(agent_a_message=msg_a, agent_b_message=msg_b)
        
        event = TurnCompleteEvent(
            conversation_id=data.get("conversation_id", ""),
            turn_number=data.get("turn_number", 0),
            turn=turn,
            convergence_score=data.get("convergence_score"),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event
    
    @classmethod
    def _build_message_complete(cls, data: Dict[str, Any], timestamp: datetime) -> MessageCompleteEvent:
        """Build MessageCompleteEvent from JSON data."""
        msg_data = data.get("message", {})
        
        message = Message(
            role=msg_data.get("role", "assistant"),
            content=msg_data.get("content", ""),
            agent_id=data.get("agent_id", ""),
            timestamp=cls._parse_timestamp(msg_data.get("timestamp", "")) if msg_data.get("timestamp") else timestamp
        )
        
        event = MessageCompleteEvent(
            conversation_id=data.get("conversation_id", ""),
            agent_id=data.get("agent_id", ""),
            message=message,
            tokens_used=data.get("tokens_used", 0),
            duration_ms=data.get("duration_ms", 0),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event
    
    @classmethod
    def _build_system_prompt(cls, data: Dict[str, Any], timestamp: datetime) -> SystemPromptEvent:
        """Build SystemPromptEvent from JSON data."""
        event = SystemPromptEvent(
            conversation_id=data.get("conversation_id", ""),
            agent_id=data.get("agent_id", ""),
            prompt=data.get("prompt", ""),
            agent_display_name=data.get("agent_display_name"),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event
    
    @classmethod
    def _build_error(cls, data: Dict[str, Any], timestamp: datetime) -> ErrorEvent:
        """Build ErrorEvent from JSON data."""
        event = ErrorEvent(
            conversation_id=data.get("conversation_id", ""),
            error_type=data.get("error_type", "unknown"),
            error_message=data.get("error_message", ""),
            context=data.get("context"),
        )
        event.timestamp = timestamp
        event.event_id = data.get("event_id", event.event_id)
        return event
    
    @classmethod
    def read_jsonl_events(cls, jsonl_path: Path):
        """Generator that reads and deserializes events from a JSONL file.
        
        Args:
            jsonl_path: Path to JSONL file
            
        Yields:
            (line_number, event) tuples
        """
        with open(jsonl_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    if not line.strip():
                        continue
                        
                    event_data = json.loads(line)
                    event = cls.deserialize_event(event_data)
                    
                    if event:
                        yield line_num, event
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON at line {line_num} in {jsonl_path}: {e}")
                    continue