"""Thread safety tests for EventBus."""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

import pytest

from pidgin.core.event_bus import EventBus
from pidgin.core.events import ConversationStartEvent, Event, MessageCompleteEvent
from tests.builders import (
    make_conversation_start_event,
    make_message,
    make_message_complete_event,
)


class TestEventBusThreadSafety:
    """Test thread safety of EventBus operations."""

    @pytest.fixture
    def event_bus(self, tmp_path):
        """Create an EventBus instance for testing."""
        return EventBus(event_log_dir=str(tmp_path))

    @pytest.mark.asyncio
    async def test_concurrent_emit_operations(self, event_bus):
        """Test that concurrent emit operations are thread-safe."""
        await event_bus.start()

        # Track received events
        received_events = []
        lock = threading.Lock()

        def handler(event):
            with lock:
                received_events.append(event)

        # Subscribe to all events
        event_bus.subscribe(Event, handler)

        # Create multiple events
        num_threads = 10
        events_per_thread = 100

        async def emit_events(thread_id):
            """Emit events from a thread."""
            for i in range(events_per_thread):
                event = ConversationStartEvent(
                    conversation_id=f"conv_{thread_id}_{i}",
                    agent_a_model="gpt-4",
                    agent_b_model="claude-3",
                    initial_prompt=f"Test {thread_id}-{i}",
                    max_turns=10,
                )
                await event_bus.emit(event)

        # Run concurrent emits
        tasks = []
        for thread_id in range(num_threads):
            task = asyncio.create_task(emit_events(thread_id))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Verify all events were received
        assert len(received_events) == num_threads * events_per_thread

        # Verify history is intact
        history = event_bus.get_history()
        assert len(history) == min(
            num_threads * events_per_thread, event_bus.max_history_size
        )

        await event_bus.stop()

    @pytest.mark.asyncio
    async def test_concurrent_subscribe_unsubscribe(self, event_bus):
        """Test concurrent subscribe/unsubscribe operations."""
        await event_bus.start()

        handlers = []
        subscribe_count = 50

        # Create handlers
        for i in range(subscribe_count):
            handler = Mock(name=f"handler_{i}")
            handlers.append(handler)

        async def subscribe_task(handler):
            """Subscribe a handler."""
            event_bus.subscribe(ConversationStartEvent, handler)
            await asyncio.sleep(0.001)  # Small delay
            event_bus.unsubscribe(ConversationStartEvent, handler)

        # Run concurrent subscribe/unsubscribe
        tasks = []
        for handler in handlers:
            task = asyncio.create_task(subscribe_task(handler))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Verify no handlers remain
        assert len(event_bus.subscribers[ConversationStartEvent]) == 0

        await event_bus.stop()

    @pytest.mark.asyncio
    async def test_concurrent_jsonl_writes(self, event_bus):
        """Test concurrent JSONL file writes are thread-safe."""
        await event_bus.start()

        # Create events for multiple conversations
        num_conversations = 5
        events_per_conversation = 50

        async def emit_conversation_events(conv_id):
            """Emit events for a conversation."""
            for i in range(events_per_conversation):
                event = MessageCompleteEvent(
                    conversation_id=conv_id,
                    agent_id="agent_a" if i % 2 == 0 else "agent_b",
                    message=make_message(f"Test message {i}"),
                    tokens_used=100,
                    duration_ms=500,
                )
                await event_bus.emit(event)

        # Run concurrent conversation event streams
        tasks = []
        for i in range(num_conversations):
            conv_id = f"conversation_{i}"
            task = asyncio.create_task(emit_conversation_events(conv_id))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Verify JSONL files were created
        jsonl_dir = Path(event_bus.event_log_dir)
        jsonl_files = list(jsonl_dir.glob("*.jsonl"))
        assert len(jsonl_files) == num_conversations

        # Verify each file has correct number of events
        for jsonl_file in jsonl_files:
            with open(jsonl_file, "r") as f:
                lines = f.readlines()
                assert len(lines) == events_per_conversation

        await event_bus.stop()

    @pytest.mark.asyncio
    async def test_concurrent_history_access(self, event_bus):
        """Test concurrent access to event history."""
        await event_bus.start()

        # Fill history with events
        for i in range(100):
            event = ConversationStartEvent(
                conversation_id=f"conv_{i}",
                agent_a_model="gpt-4",
                agent_b_model="claude-3",
                initial_prompt=f"Test {i}",
                max_turns=10,
            )
            await event_bus.emit(event)

        # Concurrent readers
        read_results = []
        read_lock = threading.Lock()

        async def read_history():
            """Read history multiple times."""
            for _ in range(50):
                history = event_bus.get_history()
                with read_lock:
                    read_results.append(len(history))
                await asyncio.sleep(0.001)

        # Concurrent writer
        async def write_events():
            """Continue writing events."""
            for i in range(100, 200):
                event = ConversationStartEvent(
                    conversation_id=f"conv_{i}",
                    agent_a_model="gpt-4",
                    agent_b_model="claude-3",
                    initial_prompt=f"Test {i}",
                    max_turns=10,
                )
                await event_bus.emit(event)
                await asyncio.sleep(0.001)

        # Run concurrent reads and writes
        tasks = [
            asyncio.create_task(read_history()),
            asyncio.create_task(read_history()),
            asyncio.create_task(read_history()),
            asyncio.create_task(write_events()),
        ]

        await asyncio.gather(*tasks)

        # Verify reads were consistent (no crashes or corrupted data)
        assert all(0 < r <= event_bus.max_history_size for r in read_results)

        await event_bus.stop()

    @pytest.mark.asyncio
    async def test_concurrent_clear_history(self, event_bus):
        """Test concurrent clear operations with ongoing emits."""
        await event_bus.start()

        # Track clear operations
        clear_count = 0
        clear_lock = threading.Lock()

        async def emit_and_clear():
            """Emit events and occasionally clear history."""
            nonlocal clear_count
            for i in range(100):
                event = ConversationStartEvent(
                    conversation_id=f"conv_{i}",
                    agent_a_model="gpt-4",
                    agent_b_model="claude-3",
                    initial_prompt=f"Test {i}",
                    max_turns=10,
                )
                await event_bus.emit(event)

                if i % 20 == 0:
                    event_bus.clear_history()
                    with clear_lock:
                        clear_count += 1

        # Run multiple concurrent emit/clear tasks
        tasks = []
        for _ in range(5):
            task = asyncio.create_task(emit_and_clear())
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Verify clears happened
        assert clear_count > 0

        # Final history should be relatively small
        final_history = event_bus.get_history()
        assert len(final_history) < event_bus.max_history_size

        await event_bus.stop()

    @pytest.mark.asyncio
    async def test_concurrent_close_conversation_logs(self, event_bus):
        """Test concurrent closing of conversation logs."""
        await event_bus.start()

        # Create events for multiple conversations
        num_conversations = 10

        # First, emit events to create log files
        for i in range(num_conversations):
            conv_id = f"conversation_{i}"
            event = MessageCompleteEvent(
                conversation_id=conv_id,
                agent_id="agent_a",
                message=make_message(f"Test message for {conv_id}"),
                tokens_used=100,
                duration_ms=500,
            )
            await event_bus.emit(event)

        # Verify files are created
        assert len(event_bus._jsonl_files) == num_conversations

        # Concurrent close operations
        async def close_log(conv_id):
            """Close a conversation log."""
            event_bus.close_conversation_log(conv_id)
            await asyncio.sleep(0.001)

        # Run concurrent closes
        tasks = []
        for i in range(num_conversations):
            conv_id = f"conversation_{i}"
            task = asyncio.create_task(close_log(conv_id))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Verify all logs are closed
        assert len(event_bus._jsonl_files) == 0

        await event_bus.stop()

    @pytest.mark.asyncio
    async def test_stress_test_all_operations(self, event_bus):
        """Stress test with all operations happening concurrently."""
        await event_bus.start()

        # Track operations
        operation_counts = {
            "emit": 0,
            "subscribe": 0,
            "unsubscribe": 0,
            "get_history": 0,
            "clear_history": 0,
        }
        count_lock = threading.Lock()

        # Handlers
        handlers = [Mock(name=f"handler_{i}") for i in range(20)]

        async def stress_operations(worker_id):
            """Perform random operations."""
            import random

            for _ in range(100):
                op = random.choice(
                    ["emit", "subscribe", "unsubscribe", "get_history", "clear_history"]
                )

                try:
                    if op == "emit":
                        event = ConversationStartEvent(
                            conversation_id=f"conv_{worker_id}_{_}",
                            agent_a_model="gpt-4",
                            agent_b_model="claude-3",
                            initial_prompt=f"Test {worker_id}",
                            max_turns=10,
                        )
                        await event_bus.emit(event)

                    elif op == "subscribe":
                        handler = random.choice(handlers)
                        event_bus.subscribe(Event, handler)

                    elif op == "unsubscribe":
                        handler = random.choice(handlers)
                        event_bus.unsubscribe(Event, handler)

                    elif op == "get_history":
                        history = event_bus.get_history()
                        assert isinstance(history, list)

                    elif op == "clear_history":
                        event_bus.clear_history()

                    with count_lock:
                        operation_counts[op] += 1

                except Exception as e:
                    pytest.fail(f"Operation {op} failed: {e}")

                await asyncio.sleep(0.001)

        # Run stress test with multiple workers
        num_workers = 10
        tasks = []
        for i in range(num_workers):
            task = asyncio.create_task(stress_operations(i))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Verify operations completed
        assert all(count > 0 for count in operation_counts.values())

        await event_bus.stop()
