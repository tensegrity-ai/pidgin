"""Thread safety tests for ExperimentEventHandler."""

import asyncio
import threading
from datetime import datetime, timezone
from unittest.mock import Mock
import pytest

from pidgin.experiments.event_handler import ExperimentEventHandler
from pidgin.core.events import (
    ConversationStartEvent,
    ConversationEndEvent,
    MessageCompleteEvent,
    TurnCompleteEvent,
    Turn
)
from pidgin.core.types import Message
from tests.builders import (
    make_message,
    make_turn,
    make_conversation_start_event,
    make_conversation_end_event,
    make_message_complete_event,
    make_turn_complete_event
)


class TestExperimentEventHandlerThreadSafety:
    """Test thread safety of ExperimentEventHandler operations."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create a mock EventStore."""
        storage = Mock()
        storage.update_conversation_status = Mock()
        storage.log_agent_name = Mock()
        storage.log_turn_metrics = Mock()
        storage.log_message_metrics = Mock()
        storage.log_word_frequencies = Mock()
        return storage
    
    @pytest.fixture
    def event_handler(self, mock_storage):
        """Create an ExperimentEventHandler instance."""
        return ExperimentEventHandler(
            storage=mock_storage,
            experiment_id="test_experiment_123"
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_conversation_starts(self, event_handler):
        """Test concurrent conversation start events."""
        num_conversations = 20
        
        async def start_conversation(conv_id):
            """Start a conversation."""
            event = ConversationStartEvent(
                conversation_id=conv_id,
                agent_a_model="gpt-4",
                agent_b_model="claude-3",
                initial_prompt=f"Test conversation {conv_id}",
                max_turns=10,
                temperature_a=0.7,
                temperature_b=0.8
            )
            await event_handler.handle_conversation_start(event)
        
        # Start conversations concurrently
        tasks = []
        for i in range(num_conversations):
            conv_id = f"conversation_{i}"
            task = asyncio.create_task(start_conversation(conv_id))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify all conversations were initialized
        assert len(event_handler.metrics_calculators) == num_conversations
        assert len(event_handler.conversation_configs) == num_conversations
        assert len(event_handler.message_timings) == num_conversations
        assert len(event_handler.turn_start_times) == num_conversations
        assert len(event_handler.conversation_metrics) == num_conversations
    
    @pytest.mark.asyncio
    async def test_concurrent_message_completions(self, event_handler):
        """Test concurrent message completion events."""
        num_conversations = 10
        messages_per_conversation = 20
        
        # First initialize conversations
        for i in range(num_conversations):
            conv_id = f"conversation_{i}"
            start_event = ConversationStartEvent(
                conversation_id=conv_id,
                agent_a_model="gpt-4",
                agent_b_model="claude-3",
                initial_prompt=f"Test {i}",
                max_turns=10
            )
            await event_handler.handle_conversation_start(start_event)
        
        async def emit_messages(conv_id):
            """Emit message complete events for a conversation."""
            for i in range(messages_per_conversation):
                event = MessageCompleteEvent(
                    conversation_id=conv_id,
                    agent_id="agent_a" if i % 2 == 0 else "agent_b",
                    message=make_message(f"Message {i}"),
                    tokens_used=100,
                    duration_ms=500 + i
                )
                await event_handler.handle_message_complete(event)
        
        # Emit messages concurrently
        tasks = []
        for i in range(num_conversations):
            conv_id = f"conversation_{i}"
            task = asyncio.create_task(emit_messages(conv_id))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify all message timings were recorded
        for i in range(num_conversations):
            conv_id = f"conversation_{i}"
            assert conv_id in event_handler.message_timings
            # Should have both agent_a and agent_b timings
            assert len(event_handler.message_timings[conv_id]) == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_turn_completions(self, event_handler, mock_storage):
        """Test concurrent turn completion events."""
        num_conversations = 5
        turns_per_conversation = 10
        
        # Initialize conversations
        for i in range(num_conversations):
            conv_id = f"conversation_{i}"
            start_event = ConversationStartEvent(
                conversation_id=conv_id,
                agent_a_model="gpt-4",
                agent_b_model="claude-3",
                initial_prompt=f"Test {i}",
                max_turns=turns_per_conversation
            )
            await event_handler.handle_conversation_start(start_event)
        
        async def complete_turns(conv_id):
            """Complete turns for a conversation."""
            for turn_num in range(turns_per_conversation):
                # Create a turn with messages
                turn = Turn(
                    agent_a_message=make_message(f"A says {turn_num}", "agent_a"),
                    agent_b_message=make_message(f"B says {turn_num}", "agent_b")
                )
                
                event = TurnCompleteEvent(
                    conversation_id=conv_id,
                    turn_number=turn_num,
                    turn=turn
                )
                await event_handler.handle_turn_complete(event)
        
        # Complete turns concurrently
        tasks = []
        for i in range(num_conversations):
            conv_id = f"conversation_{i}"
            task = asyncio.create_task(complete_turns(conv_id))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify metrics were tracked
        for i in range(num_conversations):
            conv_id = f"conversation_{i}"
            metrics = event_handler.conversation_metrics[conv_id]
            assert len(metrics['convergence_history']) == turns_per_conversation
            assert len(metrics['vocabulary_overlap_history']) == turns_per_conversation
    
    @pytest.mark.asyncio
    async def test_concurrent_conversation_ends(self, event_handler):
        """Test concurrent conversation end events."""
        num_conversations = 15
        
        # Initialize and run conversations
        for i in range(num_conversations):
            conv_id = f"conversation_{i}"
            start_event = ConversationStartEvent(
                conversation_id=conv_id,
                agent_a_model="gpt-4",
                agent_b_model="claude-3",
                initial_prompt=f"Test {i}",
                max_turns=5
            )
            await event_handler.handle_conversation_start(start_event)
        
        async def end_conversation(conv_id, reason):
            """End a conversation."""
            event = ConversationEndEvent(
                conversation_id=conv_id,
                reason=reason,
                total_turns=5,
                duration_ms=10000
            )
            await event_handler.handle_conversation_end(event)
        
        # End conversations concurrently with different reasons
        tasks = []
        reasons = ['max_turns_reached', 'high_convergence', 'error', 'user_interrupt']
        for i in range(num_conversations):
            conv_id = f"conversation_{i}"
            reason = reasons[i % len(reasons)]
            task = asyncio.create_task(end_conversation(conv_id, reason))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify all conversations were cleaned up
        assert len(event_handler.metrics_calculators) == 0
        assert len(event_handler.conversation_configs) == 0
        assert len(event_handler.message_timings) == 0
        assert len(event_handler.turn_start_times) == 0
        assert len(event_handler.conversation_metrics) == 0
    
    @pytest.mark.asyncio
    async def test_interleaved_operations(self, event_handler, mock_storage):
        """Test interleaved operations on same conversation."""
        conv_id = "test_conversation"
        
        # Start conversation
        start_event = ConversationStartEvent(
            conversation_id=conv_id,
            agent_a_model="gpt-4",
            agent_b_model="claude-3",
            initial_prompt="Test interleaved",
            max_turns=20
        )
        await event_handler.handle_conversation_start(start_event)
        
        async def message_worker():
            """Emit message events."""
            for i in range(50):
                event = MessageCompleteEvent(
                    conversation_id=conv_id,
                    agent_id="agent_a" if i % 2 == 0 else "agent_b",
                    message=make_message(f"Message {i}"),
                    tokens_used=100,
                    duration_ms=500
                )
                await event_handler.handle_message_complete(event)
                await asyncio.sleep(0.001)
        
        async def turn_worker():
            """Emit turn events."""
            for turn_num in range(20):
                turn = Turn(
                    agent_a_message=make_message(f"A turn {turn_num}", "agent_a"),
                    agent_b_message=make_message(f"B turn {turn_num}", "agent_b")
                )
                event = TurnCompleteEvent(
                    conversation_id=conv_id,
                    turn_number=turn_num,
                    turn=turn
                )
                await event_handler.handle_turn_complete(event)
                await asyncio.sleep(0.005)
        
        async def metric_reader():
            """Read metrics periodically."""
            reads = []
            for _ in range(30):
                with event_handler._state_lock:
                    if conv_id in event_handler.conversation_metrics:
                        metrics = event_handler.conversation_metrics[conv_id]
                        reads.append(len(metrics.get('convergence_history', [])))
                await asyncio.sleep(0.003)
            return reads
        
        # Run all operations concurrently
        tasks = [
            asyncio.create_task(message_worker()),
            asyncio.create_task(turn_worker()),
            asyncio.create_task(metric_reader())
        ]
        
        results = await asyncio.gather(*tasks)
        reads = results[2]
        
        # Verify reads show increasing metric counts
        assert len(reads) > 0
        assert all(isinstance(r, int) for r in reads)
        
        # End conversation
        end_event = ConversationEndEvent(
            conversation_id=conv_id,
            reason="max_turns_reached",
            total_turns=20,
            duration_ms=15000
        )
        await event_handler.handle_conversation_end(end_event)
    
    @pytest.mark.asyncio
    async def test_stress_multiple_conversations(self, event_handler, mock_storage):
        """Stress test with many conversations running concurrently."""
        num_conversations = 50
        operations_per_conversation = 30
        
        async def run_conversation(conv_id):
            """Run a complete conversation lifecycle."""
            # Start
            start_event = ConversationStartEvent(
                conversation_id=conv_id,
                agent_a_model="gpt-4",
                agent_b_model="claude-3",
                initial_prompt=f"Stress test {conv_id}",
                max_turns=10
            )
            await event_handler.handle_conversation_start(start_event)
            
            # Messages and turns
            for i in range(operations_per_conversation):
                if i % 3 == 0:
                    # Message event
                    msg_event = MessageCompleteEvent(
                        conversation_id=conv_id,
                        agent_id="agent_a" if i % 2 == 0 else "agent_b",
                        message=make_message(f"Msg {i}"),
                        tokens_used=100,
                        duration_ms=500
                    )
                    await event_handler.handle_message_complete(msg_event)
                else:
                    # Turn event
                    turn = Turn(
                        agent_a_message=make_message(f"A {i}", "agent_a"),
                        agent_b_message=make_message(f"B {i}", "agent_b")
                    )
                    turn_event = TurnCompleteEvent(
                        conversation_id=conv_id,
                        turn_number=i // 3,
                        turn=turn
                    )
                    await event_handler.handle_turn_complete(turn_event)
                
                # Small delay to simulate real timing
                await asyncio.sleep(0.001)
            
            # End
            end_event = ConversationEndEvent(
                conversation_id=conv_id,
                reason="max_turns_reached",
                total_turns=10,
                duration_ms=5000
            )
            await event_handler.handle_conversation_end(end_event)
        
        # Run all conversations concurrently
        tasks = []
        for i in range(num_conversations):
            conv_id = f"stress_conv_{i}"
            task = asyncio.create_task(run_conversation(conv_id))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify all conversations completed and cleaned up
        assert len(event_handler.metrics_calculators) == 0
        assert len(event_handler.conversation_configs) == 0
        
        # Verify storage was called appropriate number of times
        assert mock_storage.update_conversation_status.call_count >= num_conversations * 2
        assert mock_storage.log_turn_metrics.call_count > 0
    
    @pytest.mark.asyncio
    async def test_conversation_summary_thread_safety(self, event_handler):
        """Test thread safety of conversation summary building."""
        num_conversations = 10
        
        # Initialize conversations with metrics
        for i in range(num_conversations):
            conv_id = f"summary_conv_{i}"
            
            # Start conversation
            start_event = ConversationStartEvent(
                conversation_id=conv_id,
                agent_a_model="gpt-4",
                agent_b_model="claude-3",
                initial_prompt=f"Summary test {i}",
                max_turns=5
            )
            await event_handler.handle_conversation_start(start_event)
            
            # Add some metrics
            metrics = event_handler.conversation_metrics[conv_id]
            metrics['convergence_history'] = [0.1, 0.2, 0.3, 0.4, 0.5]
            metrics['vocabulary_overlap_history'] = [0.2, 0.3, 0.4, 0.5, 0.6]
        
        async def build_summary(conv_id):
            """Build conversation summary."""
            event = ConversationEndEvent(
                conversation_id=conv_id,
                reason="max_turns_reached",
                total_turns=5,
                duration_ms=5000
            )
            summary = event_handler._build_conversation_summary(conv_id, event)
            return summary
        
        # Build summaries concurrently
        tasks = []
        for i in range(num_conversations):
            conv_id = f"summary_conv_{i}"
            task = asyncio.create_task(build_summary(conv_id))
            tasks.append(task)
        
        summaries = await asyncio.gather(*tasks)
        
        # Verify all summaries were built correctly
        assert len(summaries) == num_conversations
        for summary in summaries:
            assert 'conversation_id' in summary
            assert 'final_convergence' in summary
            assert summary['final_convergence'] == 0.5
            assert 'pattern_flags' in summary