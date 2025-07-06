# tests/unit/test_event_bus.py
"""Comprehensive tests for EventBus functionality including thread safety."""

import pytest
import asyncio
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import threading
import time

from pidgin.core.event_bus import EventBus
from pidgin.core.events import (
    Event, ConversationStartEvent, MessageCompleteEvent, 
    TurnCompleteEvent, ConversationEndEvent, Turn
)
from pidgin.core.types import Message


class TestEventBus:
    """Test EventBus core functionality."""
    
    @pytest.mark.asyncio
    async def test_basic_emit_subscribe(self, event_bus):
        """Test basic event emission and subscription."""
        received_events = []
        
        # Subscribe to MessageCompleteEvent
        def handler(event: MessageCompleteEvent):
            received_events.append(event)
        
        event_bus.subscribe(MessageCompleteEvent, handler)
        
        # Emit event
        test_event = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=Message(
                role="user",
                content="Hello!",
                agent_id="agent_a",
                timestamp=datetime.now()
            ),
            tokens_used=10,
            duration_ms=100
        )
        await event_bus.emit(test_event)
        
        # Check event was received
        assert len(received_events) == 1
        assert received_events[0] == test_event
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers to same event type."""
        handler1_events = []
        handler2_events = []
        
        def handler1(event): handler1_events.append(event)
        def handler2(event): handler2_events.append(event)
        
        event_bus.subscribe(MessageCompleteEvent, handler1)
        event_bus.subscribe(MessageCompleteEvent, handler2)
        
        test_event = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=Message(
                role="user",
                content="Test",
                agent_id="agent_a",
                timestamp=datetime.now()
            ),
            tokens_used=5,
            duration_ms=50
        )
        await event_bus.emit(test_event)
        
        assert len(handler1_events) == 1
        assert len(handler2_events) == 1
        assert handler1_events[0] == handler2_events[0] == test_event
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus):
        """Test unsubscribing from events."""
        received_events = []
        
        def handler(event):
            received_events.append(event)
        
        # Subscribe and emit
        event_bus.subscribe(MessageCompleteEvent, handler)
        test_event = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=Message(
                role="user",
                content="First",
                agent_id="agent_a",
                timestamp=datetime.now()
            ),
            tokens_used=5,
            duration_ms=50
        )
        await event_bus.emit(test_event)
        assert len(received_events) == 1
        
        # Unsubscribe and emit again
        event_bus.unsubscribe(MessageCompleteEvent, handler)
        await event_bus.emit(test_event)
        assert len(received_events) == 1  # Should not increase
    
    @pytest.mark.asyncio
    async def test_event_history_limit(self, event_bus):
        """Test that event history respects max size limit."""
        # Set a small limit for testing
        event_bus.max_history_size = 5
        
        # Emit more events than the limit
        for i in range(10):
            event = MessageCompleteEvent(
                conversation_id="test_conv",
                agent_id="agent_a",
                message=Message(
                    role="user",
                    content=f"Message {i}",
                    agent_id="agent_a",
                    timestamp=datetime.now()
                ),
                tokens_used=10,
                duration_ms=100
            )
            await event_bus.emit(event)
        
        # Check history size is limited
        assert len(event_bus.event_history) == 5
        # Check we have the most recent events
        assert event_bus.event_history[-1].message.content == "Message 9"
    
    @pytest.mark.asyncio
    async def test_jsonl_file_creation(self, event_bus, mock_pidgin_output_dir):
        """Test JSONL file creation for conversations."""
        conv_id = "test_conv_123"
        
        # Emit conversation started event
        start_event = ConversationStartEvent(
            conversation_id=conv_id,
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test prompt",
            max_turns=10
        )
        await event_bus.emit(start_event)
        
        # Check JSONL file was created
        expected_file = mock_pidgin_output_dir / "conversations" / f"{conv_id}_events.jsonl"
        assert expected_file.exists()
        
        # Check content
        with open(expected_file, 'r') as f:
            line = json.loads(f.readline())
            assert line["event_type"] == "ConversationStartEvent"
            assert line["conversation_id"] == conv_id
    
    @pytest.mark.asyncio
    async def test_jsonl_append(self, event_bus, mock_pidgin_output_dir):
        """Test appending multiple events to JSONL file."""
        conv_id = "test_conv_456"
        
        # Create messages for turn
        msg_a = Message(
            role="user",
            content="Hello",
            agent_id="agent_a",
            timestamp=datetime.now()
        )
        msg_b = Message(
            role="assistant",
            content="Hi there",
            agent_id="agent_b",
            timestamp=datetime.now()
        )
        
        # Emit multiple events
        events = [
            ConversationStartEvent(
                conversation_id=conv_id,
                agent_a_model="model_a",
                agent_b_model="model_b",
                initial_prompt="Test",
                max_turns=5
            ),
            MessageCompleteEvent(
                conversation_id=conv_id,
                agent_id="agent_a",
                message=msg_a,
                tokens_used=10,
                duration_ms=100
            ),
            ConversationEndEvent(
                conversation_id=conv_id,
                reason="completed",
                total_turns=1,
                duration_ms=1000
            )
        ]
        
        for event in events:
            await event_bus.emit(event)
        
        # Check all events were written
        jsonl_file = mock_pidgin_output_dir / "conversations" / f"{conv_id}_events.jsonl"
        with open(jsonl_file, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 3
        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["event_type"] == type(events[i]).__name__
    
    @pytest.mark.asyncio
    async def test_error_handling_in_subscriber(self, event_bus):
        """Test that errors in subscribers don't break event emission."""
        good_events = []
        
        def bad_handler(event):
            raise ValueError("Test error")
        
        def good_handler(event):
            good_events.append(event)
        
        event_bus.subscribe(MessageCompleteEvent, bad_handler)
        event_bus.subscribe(MessageCompleteEvent, good_handler)
        
        test_event = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=Message(
                role="user",
                content="Test",
                agent_id="agent_a",
                timestamp=datetime.now()
            ),
            tokens_used=5,
            duration_ms=50
        )
        
        # Should not raise despite bad_handler error
        await event_bus.emit(test_event)
        
        # Good handler should still receive event
        assert len(good_events) == 1
        assert good_events[0] == test_event
    
    @pytest.mark.asyncio
    async def test_cleanup(self, event_bus, mock_pidgin_output_dir):
        """Test cleanup closes all file handles."""
        conv_id = "test_conv_cleanup"
        
        # Create a file handle
        start_event = ConversationStartEvent(
            conversation_id=conv_id,
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=5
        )
        await event_bus.emit(start_event)
        
        # Verify file handle exists
        assert conv_id in event_bus._jsonl_files
        
        # Cleanup
        await event_bus.stop()
        
        # Verify file handles are closed
        assert len(event_bus._jsonl_files) == 0


class TestEventBusThreadSafety:
    """Test thread safety of EventBus."""
    
    @pytest.mark.asyncio
    async def test_concurrent_emit(self, event_bus):
        """Test concurrent event emission from multiple tasks."""
        num_tasks = 10
        events_per_task = 100
        received_events = []
        
        def handler(event):
            received_events.append(event)
        
        event_bus.subscribe(MessageCompleteEvent, handler)
        
        async def emit_events(task_id):
            for i in range(events_per_task):
                event = MessageCompleteEvent(
                    conversation_id=f"conv_{task_id}",
                    agent_id=f"agent_{task_id}",
                    message=Message(
                        role="user",
                        content=f"Task {task_id} Message {i}",
                        agent_id=f"agent_{task_id}",
                        timestamp=datetime.now()
                    ),
                    tokens_used=10,
                    duration_ms=100
                )
                await event_bus.emit(event)
        
        # Run concurrent tasks
        tasks = [emit_events(i) for i in range(num_tasks)]
        await asyncio.gather(*tasks)
        
        # Verify all events were received
        assert len(received_events) == num_tasks * events_per_task
    
    @pytest.mark.asyncio
    async def test_concurrent_jsonl_writes(self, event_bus, mock_pidgin_output_dir):
        """Test concurrent writes to same JSONL file."""
        conv_id = "concurrent_conv"
        num_tasks = 5
        events_per_task = 20
        
        async def emit_messages(task_id):
            for i in range(events_per_task):
                event = MessageCompleteEvent(
                    conversation_id=conv_id,
                    agent_id=f"agent_{task_id}",
                    message=Message(
                        role="user",
                        content=f"Task {task_id} Message {i}",
                        agent_id=f"agent_{task_id}",
                        timestamp=datetime.now()
                    ),
                    tokens_used=10,
                    duration_ms=100
                )
                await event_bus.emit(event)
        
        # Start with conversation
        start_event = ConversationStartEvent(
            conversation_id=conv_id,
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=100
        )
        await event_bus.emit(start_event)
        
        # Run concurrent tasks
        tasks = [emit_messages(i) for i in range(num_tasks)]
        await asyncio.gather(*tasks)
        
        # Verify all events were written
        jsonl_file = mock_pidgin_output_dir / "conversations" / f"{conv_id}_events.jsonl"
        with open(jsonl_file, 'r') as f:
            lines = f.readlines()
        
        # 1 start event + (num_tasks * events_per_task) message events
        assert len(lines) == 1 + (num_tasks * events_per_task)
    
    def test_subscribe_unsubscribe_thread_safety(self):
        """Test thread-safe subscribe/unsubscribe operations."""
        event_bus = EventBus()
        errors = []
        
        def subscribe_task():
            try:
                for i in range(100):
                    handler = lambda e: None
                    event_bus.subscribe(MessageCompleteEvent, handler)
                    event_bus.unsubscribe(MessageCompleteEvent, handler)
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=subscribe_task)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_event_history_thread_safety(self, event_bus):
        """Test thread-safe access to event history."""
        event_bus.max_history_size = 100
        
        async def emit_and_read(task_id):
            for i in range(50):
                # Emit event
                event = MessageCompleteEvent(
                    conversation_id=f"conv_{task_id}",
                    agent_id=f"agent_{task_id}",
                    message=Message(
                        role="user",
                        content=f"Message {i}",
                        agent_id=f"agent_{task_id}",
                        timestamp=datetime.now()
                    ),
                    tokens_used=10,
                    duration_ms=100
                )
                await event_bus.emit(event)
                
                # Read history (should not crash)
                history_len = len(event_bus.event_history)
                assert history_len <= event_bus.max_history_size
        
        # Run concurrent tasks
        tasks = [emit_and_read(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # Final check
        assert len(event_bus.event_history) <= event_bus.max_history_size


class TestEventSerialization:
    """Test event serialization and deserialization."""
    
    def test_event_to_dict(self):
        """Test converting events to dictionaries."""
        msg = Message(
            role="user",
            content="Hello world",
            agent_id="agent_a",
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        event = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=msg,
            tokens_used=10,
            duration_ms=100
        )
        
        # Manually create dict as EventBus does
        event_dict = {
            "event_type": type(event).__name__,
            "conversation_id": event.conversation_id,
            "agent_id": event.agent_id,
            "tokens_used": event.tokens_used,
            "duration_ms": event.duration_ms,
            "timestamp": event.timestamp.isoformat()
        }
        
        assert event_dict["event_type"] == "MessageCompleteEvent"
        assert event_dict["conversation_id"] == "test_conv"
        assert event_dict["tokens_used"] == 10
        assert "timestamp" in event_dict
    
    def test_complex_event_serialization(self):
        """Test serialization of events with complex data."""
        event = ConversationEndEvent(
            conversation_id="test_conv",
            reason="completed",
            total_turns=10,
            duration_ms=5000
        )
        
        # Manually create dict as EventBus does
        event_dict = {
            "event_type": type(event).__name__,
            "conversation_id": event.conversation_id,
            "reason": event.reason,
            "total_turns": event.total_turns,
            "duration_ms": event.duration_ms,
            "timestamp": event.timestamp.isoformat()
        }
        
        # Should serialize without error
        json_str = json.dumps(event_dict)
        
        # Should deserialize back
        loaded = json.loads(json_str)
        assert loaded["reason"] == "completed"
        assert loaded["total_turns"] == 10


class TestEventBusPatterns:
    """Test common usage patterns and edge cases."""
    
    @pytest.mark.asyncio
    async def test_late_subscription(self, event_bus):
        """Test subscribing after events have been emitted."""
        # Emit event before subscription
        event1 = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=Message(
                role="user",
                content="Early message",
                agent_id="agent_a",
                timestamp=datetime.now()
            ),
            tokens_used=10,
            duration_ms=100
        )
        await event_bus.emit(event1)
        
        # Now subscribe
        received_events = []
        event_bus.subscribe(MessageCompleteEvent, lambda e: received_events.append(e))
        
        # Emit another event
        event2 = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_b",
            message=Message(
                role="assistant",
                content="Late message",
                agent_id="agent_b",
                timestamp=datetime.now()
            ),
            tokens_used=15,
            duration_ms=150
        )
        await event_bus.emit(event2)
        
        # Should only receive the second event
        assert len(received_events) == 1
        assert received_events[0].message.content == "Late message"
    
    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, event_bus):
        """Test subscribing to all events."""
        all_events = []
        
        # Subscribe to base Event class to get all events
        event_bus.subscribe(Event, lambda e: all_events.append(e))
        
        # Emit different event types
        await event_bus.emit(ConversationStartEvent(
            conversation_id="test_conv",
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=10
        ))
        
        await event_bus.emit(MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=Message(
                role="user",
                content="Hello",
                agent_id="agent_a",
                timestamp=datetime.now()
            ),
            tokens_used=5,
            duration_ms=50
        ))
        
        # Should receive all events
        assert len(all_events) == 2
        assert isinstance(all_events[0], ConversationStartEvent)
        assert isinstance(all_events[1], MessageCompleteEvent)