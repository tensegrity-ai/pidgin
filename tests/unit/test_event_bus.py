# tests/unit/test_event_bus.py
"""Comprehensive tests for EventBus functionality including thread safety."""

import asyncio
import json
import threading
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from pidgin.core.event_bus import EventBus
from pidgin.core.events import (
    ConversationEndEvent,
    ConversationStartEvent,
    Event,
    MessageCompleteEvent,
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
                timestamp=datetime.now(),
            ),
            tokens_used=10,
            duration_ms=100,
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

        def handler1(event):
            handler1_events.append(event)

        def handler2(event):
            handler2_events.append(event)

        event_bus.subscribe(MessageCompleteEvent, handler1)
        event_bus.subscribe(MessageCompleteEvent, handler2)

        test_event = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=Message(
                role="user",
                content="Test",
                agent_id="agent_a",
                timestamp=datetime.now(),
            ),
            tokens_used=5,
            duration_ms=50,
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
                timestamp=datetime.now(),
            ),
            tokens_used=5,
            duration_ms=50,
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
                    timestamp=datetime.now(),
                ),
                tokens_used=10,
                duration_ms=100,
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
            max_turns=10,
        )
        await event_bus.emit(start_event)

        # Check JSONL file was created
        expected_file = (
            mock_pidgin_output_dir / "conversations" / f"{conv_id}_events.jsonl"
        )
        assert expected_file.exists()

        # Check content
        with open(expected_file, "r") as f:
            line = json.loads(f.readline())
            assert line["event_type"] == "ConversationStartEvent"
            assert line["conversation_id"] == conv_id

    @pytest.mark.asyncio
    async def test_jsonl_append(self, event_bus, mock_pidgin_output_dir):
        """Test appending multiple events to JSONL file."""
        conv_id = "test_conv_456"

        # Create messages for turn
        msg_a = Message(
            role="user", content="Hello", agent_id="agent_a", timestamp=datetime.now()
        )
        _msg_b = Message(
            role="assistant",
            content="Hi there",
            agent_id="agent_b",
            timestamp=datetime.now(),
        )

        # Emit multiple events
        events = [
            ConversationStartEvent(
                conversation_id=conv_id,
                agent_a_model="model_a",
                agent_b_model="model_b",
                initial_prompt="Test",
                max_turns=5,
            ),
            MessageCompleteEvent(
                conversation_id=conv_id,
                agent_id="agent_a",
                message=msg_a,
                tokens_used=10,
                duration_ms=100,
            ),
            ConversationEndEvent(
                conversation_id=conv_id,
                reason="completed",
                total_turns=1,
                duration_ms=1000,
            ),
        ]

        for event in events:
            await event_bus.emit(event)

        # Check all events were written
        jsonl_file = (
            mock_pidgin_output_dir / "conversations" / f"{conv_id}_events.jsonl"
        )
        with open(jsonl_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 3
        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["event_type"] == events[i].__class__.__name__

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
                timestamp=datetime.now(),
            ),
            tokens_used=5,
            duration_ms=50,
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
            max_turns=5,
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
                        timestamp=datetime.now(),
                    ),
                    tokens_used=10,
                    duration_ms=100,
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
                        timestamp=datetime.now(),
                    ),
                    tokens_used=10,
                    duration_ms=100,
                )
                await event_bus.emit(event)

        # Start with conversation
        start_event = ConversationStartEvent(
            conversation_id=conv_id,
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=100,
        )
        await event_bus.emit(start_event)

        # Run concurrent tasks
        tasks = [emit_messages(i) for i in range(num_tasks)]
        await asyncio.gather(*tasks)

        # Verify all events were written
        jsonl_file = (
            mock_pidgin_output_dir / "conversations" / f"{conv_id}_events.jsonl"
        )
        with open(jsonl_file, "r") as f:
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
                    def handler(e):
                        pass
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
                        timestamp=datetime.now(),
                    ),
                    tokens_used=10,
                    duration_ms=100,
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
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )

        event = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=msg,
            tokens_used=10,
            duration_ms=100,
        )

        # Manually create dict as EventBus does
        event_dict = {
            "event_type": type(event).__name__,
            "conversation_id": event.conversation_id,
            "agent_id": event.agent_id,
            "tokens_used": event.tokens_used,
            "duration_ms": event.duration_ms,
            "timestamp": event.timestamp.isoformat(),
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
            duration_ms=5000,
        )

        # Manually create dict as EventBus does
        event_dict = {
            "event_type": type(event).__name__,
            "conversation_id": event.conversation_id,
            "reason": event.reason,
            "total_turns": event.total_turns,
            "duration_ms": event.duration_ms,
            "timestamp": event.timestamp.isoformat(),
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
                timestamp=datetime.now(),
            ),
            tokens_used=10,
            duration_ms=100,
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
                timestamp=datetime.now(),
            ),
            tokens_used=15,
            duration_ms=150,
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
        await event_bus.emit(
            ConversationStartEvent(
                conversation_id="test_conv",
                agent_a_model="model_a",
                agent_b_model="model_b",
                initial_prompt="Test",
                max_turns=10,
            )
        )

        await event_bus.emit(
            MessageCompleteEvent(
                conversation_id="test_conv",
                agent_id="agent_a",
                message=Message(
                    role="user",
                    content="Hello",
                    agent_id="agent_a",
                    timestamp=datetime.now(),
                ),
                tokens_used=5,
                duration_ms=50,
            )
        )

        # Should receive all events
        assert len(all_events) == 2
        assert isinstance(all_events[0], ConversationStartEvent)
        assert isinstance(all_events[1], MessageCompleteEvent)


class TestEventBusSerializationEdgeCases:
    """Test edge cases in serialization."""

    @pytest.mark.asyncio
    async def test_serialize_datetime_object(self, event_bus):
        """Test serializing datetime objects (line 50)."""
        # Create an event with datetime
        from datetime import datetime

        _event = ConversationStartEvent(
            conversation_id="test_conv",
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=10,
        )

        # Test serialization
        serialized = event_bus._serialize_value(datetime.now())
        assert isinstance(serialized, str)  # Should be ISO format string

    @pytest.mark.asyncio
    async def test_serialize_list_values(self, event_bus):
        """Test serializing list values (line 54)."""
        test_list = ["hello", 123, {"key": "value"}, None]
        serialized = event_bus._serialize_value(test_list)
        assert isinstance(serialized, list)
        assert len(serialized) == 4
        assert serialized[0] == "hello"
        assert serialized[1] == 123
        assert isinstance(serialized[2], dict)
        assert serialized[3] is None

    @pytest.mark.asyncio
    async def test_serialize_dict_values(self, event_bus):
        """Test serializing dict values (line 56)."""
        test_dict = {
            "string": "value",
            "number": 42,
            "nested": {"inner": "data"},
            "datetime": datetime.now(),
        }
        serialized = event_bus._serialize_value(test_dict)
        assert isinstance(serialized, dict)
        assert serialized["string"] == "value"
        assert serialized["number"] == 42
        assert isinstance(serialized["nested"], dict)
        assert isinstance(serialized["datetime"], str)  # Should be ISO format

    @pytest.mark.asyncio
    async def test_serialize_google_model(self, event_bus):
        """Test serializing Google GenerativeModel objects (lines 59-61)."""

        # Mock a Google GenerativeModel object
        class MockGoogleModel:
            def __init__(self):
                self._model_name = "models/gemini-pro"
                self._client = "mock_client"

        mock_model = MockGoogleModel()
        serialized = event_bus._serialize_value(mock_model)
        assert serialized == "gemini-pro"  # Should extract model name without prefix

    @pytest.mark.asyncio
    async def test_serialize_object_fallback(self, event_bus):
        """Test serializing generic objects (line 68)."""

        # Object without __dict__ attribute
        class CustomObject:
            __slots__ = ["value"]  # No __dict__

            def __init__(self):
                self.value = 42

            def __str__(self):
                return "custom_object_string"

        obj = CustomObject()
        serialized = event_bus._serialize_value(obj)
        assert serialized == "custom_object_string"

    @pytest.mark.asyncio
    async def test_serialize_google_model_in_object(self, event_bus):
        """Test Google model serialization in _serialize_object (lines 84-86)."""

        # Mock a Google GenerativeModel object
        class MockGoogleModel:
            def __init__(self):
                self._model_name = "models/gemini-1.5-pro"
                self._client = "mock_client"

        mock_model = MockGoogleModel()
        serialized = event_bus._serialize_object(mock_model)
        assert serialized == "models/gemini-1.5-pro"

    @pytest.mark.asyncio
    async def test_serialize_object_exception_handling(self, event_bus):
        """Test object serialization with exception (lines 96-99)."""

        # Object that raises exception when accessing __dict__
        class ProblematicObject:
            @property
            def __dict__(self):
                raise AttributeError("No dict access")

            def __str__(self):
                return "problematic_object"

        obj = ProblematicObject()
        serialized = event_bus._serialize_object(obj)
        assert serialized == "problematic_object"

    @pytest.mark.asyncio
    async def test_no_conversation_id_event(self, event_bus):
        """Test event without conversation_id (lines 122-123)."""

        # Create a custom event without conversation_id
        class CustomEvent(Event):
            def __init__(self, data):
                super().__init__()
                self.data = data

        event = CustomEvent("test_data")

        # Should not crash when emitting
        await event_bus.emit(event)

        # Should be in history but not in JSONL
        assert len(event_bus.event_history) == 1
        assert len(event_bus._jsonl_files) == 0

    @pytest.mark.asyncio
    async def test_jsonl_without_event_log_dir(self):
        """Test JSONL operations without event_log_dir (line 104)."""
        # Create EventBus without event_log_dir
        event_bus = EventBus(event_log_dir=None)

        # Try to get JSONL file
        file_handle = event_bus._get_jsonl_file("test_conv")
        assert file_handle is None

        # Emit event - should work without JSONL
        event = ConversationStartEvent(
            conversation_id="test_conv",
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=10,
        )
        await event_bus.emit(event)
        assert len(event_bus.event_history) == 1

    @pytest.mark.asyncio
    async def test_jsonl_serialization_error(self, event_bus, mock_pidgin_output_dir):
        """Test JSONL serialization error handling (lines 132-140)."""
        # Create a mock event that will cause serialization to fail
        event = ConversationStartEvent(
            conversation_id="test_conv",
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=10,
        )

        # Mock json.dumps to fail
        with patch("json.dumps", side_effect=TypeError("Object not serializable")):
            with patch("pidgin.core.event_bus.logger") as mock_logger:
                await event_bus.emit(event)
                # Should log serialization error
                assert any(
                    "Failed to serialize event" in str(call)
                    for call in mock_logger.error.call_args_list
                )

    @pytest.mark.asyncio
    async def test_jsonl_write_error(self, event_bus, mock_pidgin_output_dir):
        """Test JSONL write error handling (lines 146-147)."""
        # Create a valid event
        event = ConversationStartEvent(
            conversation_id="test_conv",
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=10,
        )

        # Mock file handle to raise exception
        with patch.object(event_bus, "_get_jsonl_file") as mock_get_file:
            mock_file = Mock()
            mock_file.write.side_effect = IOError("Disk full")
            mock_get_file.return_value = mock_file

            with patch("pidgin.core.event_bus.logger") as mock_logger:
                await event_bus.emit(event)
                # Should log write error
                assert any(
                    "Error writing to JSONL" in str(call)
                    for call in mock_logger.error.call_args_list
                )

    @pytest.mark.asyncio
    async def test_async_handler(self, event_bus):
        """Test async event handler (line 214)."""
        received_events = []

        async def async_handler(event):
            await asyncio.sleep(0.01)  # Simulate async work
            received_events.append(event)

        event_bus.subscribe(MessageCompleteEvent, async_handler)

        event = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=Message(
                role="user",
                content="Test",
                agent_id="agent_a",
                timestamp=datetime.now(),
            ),
            tokens_used=10,
            duration_ms=100,
        )
        await event_bus.emit(event)

        # Should handle async handler
        assert len(received_events) == 1

    @pytest.mark.asyncio
    async def test_handler_error_with_debug_mode(self, event_bus):
        """Test handler error with debug mode (line 224)."""
        import os

        def bad_handler(event):
            raise ValueError("Test error")

        event_bus.subscribe(MessageCompleteEvent, bad_handler)

        event = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=Message(
                role="user",
                content="Test",
                agent_id="agent_a",
                timestamp=datetime.now(),
            ),
            tokens_used=10,
            duration_ms=100,
        )

        # Test with debug mode
        os.environ["PIDGIN_DEBUG"] = "1"
        try:
            with patch("pidgin.core.event_bus.logger") as mock_logger:
                await event_bus.emit(event)
                # Should log with traceback
                mock_logger.error.assert_called()
                # Check exc_info was passed
                assert mock_logger.error.call_args[1].get("exc_info") is True
        finally:
            os.environ.pop("PIDGIN_DEBUG", None)

    @pytest.mark.asyncio
    async def test_get_history_filtered(self, event_bus):
        """Test get_history with filter (lines 259-263)."""
        # Emit different types of events
        conv_event = ConversationStartEvent(
            conversation_id="test_conv",
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=10,
        )
        msg_event = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=Message(
                role="user",
                content="Test",
                agent_id="agent_a",
                timestamp=datetime.now(),
            ),
            tokens_used=10,
            duration_ms=100,
        )

        await event_bus.emit(conv_event)
        await event_bus.emit(msg_event)

        # Get all history
        all_history = event_bus.get_history()
        assert len(all_history) == 2

        # Get filtered history
        msg_history = event_bus.get_history(MessageCompleteEvent)
        assert len(msg_history) == 1
        assert isinstance(msg_history[0], MessageCompleteEvent)

    @pytest.mark.asyncio
    async def test_clear_history(self, event_bus):
        """Test clear_history method (lines 267-268)."""
        # Add some events
        event = ConversationStartEvent(
            conversation_id="test_conv",
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=10,
        )
        await event_bus.emit(event)
        assert len(event_bus.event_history) == 1

        # Clear history
        event_bus.clear_history()
        assert len(event_bus.event_history) == 0

    @pytest.mark.asyncio
    async def test_start_method(self, event_bus):
        """Test start method (line 272)."""
        assert not event_bus._running
        await event_bus.start()
        assert event_bus._running

    @pytest.mark.asyncio
    async def test_close_error_handling(self, event_bus, mock_pidgin_output_dir):
        """Test error handling in stop method (lines 283-284)."""
        # Create a file handle
        event = ConversationStartEvent(
            conversation_id="test_conv",
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=10,
        )
        await event_bus.emit(event)

        # Mock file handle to raise on close
        mock_file = Mock()
        mock_file.close.side_effect = IOError("Cannot close")
        event_bus._jsonl_files["test_conv"] = mock_file

        # Should not crash on stop
        with patch("pidgin.core.event_bus.logger") as mock_logger:
            await event_bus.stop()
            # Should log error
            assert any(
                "Error closing JSONL file" in str(call)
                for call in mock_logger.error.call_args_list
            )

    @pytest.mark.asyncio
    async def test_close_conversation_log(self, event_bus, mock_pidgin_output_dir):
        """Test close_conversation_log method (lines 293-300)."""
        # Create a file handle
        conv_id = "test_conv"
        event = ConversationStartEvent(
            conversation_id=conv_id,
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=10,
        )
        await event_bus.emit(event)
        assert conv_id in event_bus._jsonl_files

        # Close specific conversation log
        event_bus.close_conversation_log(conv_id)
        assert conv_id not in event_bus._jsonl_files

    @pytest.mark.asyncio
    async def test_close_conversation_log_error(
        self, event_bus, mock_pidgin_output_dir
    ):
        """Test error handling in close_conversation_log (lines 299-300)."""
        conv_id = "test_conv"

        # Mock file handle that errors on close
        mock_file = Mock()
        mock_file.close.side_effect = IOError("Cannot close")
        event_bus._jsonl_files[conv_id] = mock_file

        # Should not crash
        with patch("pidgin.core.event_bus.logger") as mock_logger:
            event_bus.close_conversation_log(conv_id)
            # Should log error
            assert mock_logger.error.called
            assert "Error closing JSONL file" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_close_nonexistent_conversation(self, event_bus):
        """Test closing non-existent conversation log."""
        # Should handle gracefully when closing non-existent conversation
        # This test ensures the method doesn't raise an exception
        try:
            event_bus.close_conversation_log("nonexistent_conv")
        except Exception as e:
            pytest.fail(f"close_conversation_log raised {e} unexpectedly!")

    @pytest.mark.asyncio
    async def test_model_field_handling(self, event_bus, mock_pidgin_output_dir):
        """Test special handling of model field (lines 170-182)."""

        # Test with Google GenerativeModel
        class MockGoogleModel:
            def __init__(self):
                self._model_name = "models/gemini-pro"
                self._client = "mock_client"

        # Create event with model field
        class EventWithModel(Event):
            def __init__(self, conv_id, model):
                super().__init__()
                self.conversation_id = conv_id
                self.model = model

        # Test with GenerativeModel object
        event1 = EventWithModel("test_conv", MockGoogleModel())
        await event_bus.emit(event1)

        # Test with object having model_name attribute
        class ModelWithName:
            def __init__(self):
                self.model_name = "custom-model"

        event2 = EventWithModel("test_conv", ModelWithName())
        await event_bus.emit(event2)

        # Test with string model
        event3 = EventWithModel("test_conv", "string-model")
        await event_bus.emit(event3)

        # Test with unexpected type
        event4 = EventWithModel("test_conv", 12345)
        with patch("pidgin.core.event_bus.logger") as mock_logger:
            await event_bus.emit(event4)
            # Should log warning
            assert any(
                "Unexpected type for model field" in str(call)
                for call in mock_logger.warning.call_args_list
            )

    @pytest.mark.asyncio
    async def test_serialize_sensitive_objects(self, event_bus):
        """Test serialization of sensitive objects (line 92)."""

        # Create objects with sensitive names
        class APIClient:
            def __init__(self):
                self.secret = "secret_value"

        class CredentialManager:
            def __init__(self):
                self.password = "password123"

        class TokenStorage:
            def __init__(self):
                self.token = "auth_token"

        class APIKey:
            def __init__(self):
                self.key = "api_key_123"

        # Test each sensitive object type
        client = APIClient()
        serialized = event_bus._serialize_object(client)
        assert serialized == "<APIClient object>"

        creds = CredentialManager()
        serialized = event_bus._serialize_object(creds)
        assert serialized == "<CredentialManager object>"

        tokens = TokenStorage()
        serialized = event_bus._serialize_object(tokens)
        assert serialized == "<TokenStorage object>"

        api_key = APIKey()
        serialized = event_bus._serialize_object(api_key)
        assert serialized == "<APIKey object>"

    @pytest.mark.asyncio
    async def test_serialize_value_with_dict_object(self, event_bus):
        """Test _serialize_value with object that has __dict__."""

        class SimpleObject:
            def __init__(self):
                self.name = "test"
                self.value = 42

        obj = SimpleObject()
        serialized = event_bus._serialize_value(obj)
        assert isinstance(serialized, dict)
        assert serialized["name"] == "test"
        assert serialized["value"] == 42

    @pytest.mark.asyncio
    async def test_jsonl_serialization_field_error(
        self, event_bus, mock_pidgin_output_dir
    ):
        """Test JSONL serialization with specific field errors (lines 135-140)."""
        # Create event
        event = ConversationStartEvent(
            conversation_id="test_conv",
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test",
            max_turns=10,
        )

        # Mock json.dumps to fail on first call, then succeed on individual fields
        call_count = 0

        def mock_dumps(data, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails
                raise TypeError("Cannot serialize")
            elif "bad_field" in str(data):
                # Specific field fails
                raise TypeError("Bad field")
            else:
                # Other fields succeed
                return json.dumps(data, *args, **kwargs)

        # Add a problematic field
        event.bad_field = object()  # Not serializable

        with patch("json.dumps", side_effect=mock_dumps):
            with patch("pidgin.core.event_bus.logger") as mock_logger:
                await event_bus.emit(event)
                # Should log error about specific field
                error_calls = [str(call) for call in mock_logger.error.call_args_list]
                assert any("Failed to serialize event" in call for call in error_calls)

    @pytest.mark.asyncio
    async def test_event_history_exact_limit(self, event_bus):
        """Test event history at exactly the limit (line 160)."""
        # Set limit to exactly 3
        event_bus.max_history_size = 3
        event_bus.event_history.clear()

        # Add exactly 3 events
        for i in range(3):
            event = ConversationStartEvent(
                conversation_id=f"conv_{i}",
                agent_a_model="model_a",
                agent_b_model="model_b",
                initial_prompt=f"Test {i}",
                max_turns=10,
            )
            await event_bus.emit(event)

        # Should have exactly 3 events
        assert len(event_bus.event_history) == 3

        # Add one more - should trigger trimming
        event = ConversationStartEvent(
            conversation_id="conv_4",
            agent_a_model="model_a",
            agent_b_model="model_b",
            initial_prompt="Test 4",
            max_turns=10,
        )
        await event_bus.emit(event)

        # Should still have 3 events (oldest removed)
        assert len(event_bus.event_history) == 3
        assert event_bus.event_history[0].conversation_id == "conv_1"
        assert event_bus.event_history[-1].conversation_id == "conv_4"

    @pytest.mark.asyncio
    async def test_handler_error_without_debug_mode(self, event_bus):
        """Test handler error without debug mode (line 227)."""
        import os

        # Ensure PIDGIN_DEBUG is not set
        os.environ.pop("PIDGIN_DEBUG", None)

        def bad_handler(event):
            raise ValueError("Test error")

        event_bus.subscribe(MessageCompleteEvent, bad_handler)

        event = MessageCompleteEvent(
            conversation_id="test_conv",
            agent_id="agent_a",
            message=Message(
                role="user",
                content="Test",
                agent_id="agent_a",
                timestamp=datetime.now(),
            ),
            tokens_used=10,
            duration_ms=100,
        )

        with patch("pidgin.core.event_bus.logger") as mock_logger:
            await event_bus.emit(event)
            # Should log without exc_info
            mock_logger.error.assert_called()
            # Check exc_info was NOT passed
            assert mock_logger.error.call_args[1].get("exc_info") is not True

    @pytest.mark.asyncio
    async def test_unsubscribe_missing_handler(self, event_bus):
        """Test unsubscribing a handler that's not subscribed (lines 247-248)."""

        def handler1(event):
            pass

        def handler2(event):
            pass

        # Subscribe handler1
        event_bus.subscribe(MessageCompleteEvent, handler1)

        # Try to unsubscribe handler2 (not subscribed)
        event_bus.unsubscribe(MessageCompleteEvent, handler2)

        # handler1 should still be subscribed
        assert handler1 in event_bus.subscribers[MessageCompleteEvent]
        assert handler2 not in event_bus.subscribers[MessageCompleteEvent]
