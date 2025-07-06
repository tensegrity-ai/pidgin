# tests/integration/test_conversation_flow.py
"""Integration tests for conversation flow."""

import pytest
import asyncio
from pathlib import Path
from pidgin.core.conductor import Conductor
from pidgin.core.event_bus import EventBus
from pidgin.core.types import Agent, Conversation
from pidgin.local.test_model import LocalTestModel
from pidgin.providers.local import LocalProvider


class TestConversationFlow:
    """Test end-to-end conversation flow."""
    
    @pytest.mark.asyncio
    async def test_basic_conversation_with_test_model(self, tmp_path):
        """Test basic conversation using local test model."""
        # Set up event bus with JSONL logging
        event_log_dir = tmp_path / "events"
        event_log_dir.mkdir()
        bus = EventBus(event_log_dir=str(event_log_dir))
        
        # Create agents using test model
        agents = [
            Agent(id="agent_a", model="local:test", display_name="Test A"),
            Agent(id="agent_b", model="local:test", display_name="Test B")
        ]
        
        # Create conversation
        conversation = Conversation(
            agents=agents,
            initial_prompt="Let's test the conversation system"
        )
        
        # Create conductor
        conductor = Conductor(bus)
        
        # Track events
        events_received = []
        
        def track_event(event):
            events_received.append(event)
        
        from pidgin.core.events import Event
        bus.subscribe(Event, track_event)
        
        # Run conversation (just a few turns)
        max_turns = 3
        turn_count = 0
        
        # Start bus
        await bus.start()
        
        try:
            # Note: This is a simplified test flow since we don't have
            # all the conductor methods available. In a real test, we'd
            # use the actual conductor.run_conversation method
            
            # Verify we can create providers
            provider_a = LocalProvider()
            provider_b = LocalProvider()
            
            # Verify event logging
            from pidgin.core.events import ConversationStartEvent
            start_event = ConversationStartEvent(
                conversation_id=conversation.id,
                agent_a_model=agents[0].model,
                agent_b_model=agents[1].model,
                initial_prompt=conversation.initial_prompt,
                max_turns=max_turns,
                agent_a_display_name=agents[0].display_name,
                agent_b_display_name=agents[1].display_name
            )
            await bus.emit(start_event)
            
            # Check JSONL file was created
            jsonl_files = list(event_log_dir.glob("*.jsonl"))
            assert len(jsonl_files) == 1
            
            # Verify event was logged
            with open(jsonl_files[0]) as f:
                lines = f.readlines()
                assert len(lines) >= 1
                
        finally:
            await bus.stop()
        
        # Verify events were tracked
        assert len(events_received) >= 1
        assert any(isinstance(e, ConversationStartEvent) for e in events_received)
    
    @pytest.mark.asyncio
    async def test_event_serialization(self, tmp_path):
        """Test that events are properly serialized to JSONL."""
        import json
        
        event_log_dir = tmp_path / "events"
        event_log_dir.mkdir()
        bus = EventBus(event_log_dir=str(event_log_dir))
        
        await bus.start()
        
        try:
            # Emit various event types
            from pidgin.core.events import (
                TurnStartEvent, 
                MessageCompleteEvent,
                MetricsCalculatedEvent
            )
            
            conversation_id = "test_conv_456"
            
            # Turn started
            await bus.emit(TurnStartEvent(
                conversation_id=conversation_id,
                turn_number=1
            ))
            
            # Message complete
            from pidgin.core.types import Message
            test_message = Message(
                role="assistant",
                content="Test response",
                agent_id="agent_a"
            )
            await bus.emit(MessageCompleteEvent(
                conversation_id=conversation_id,
                agent_id="agent_a",
                message=test_message,
                tokens_used=30,
                duration_ms=1500
            ))
            
            # Metrics
            await bus.emit(MetricsCalculatedEvent(
                conversation_id=conversation_id,
                turn_number=1,
                metrics={
                    "length_a": 10,
                    "length_b": 15,
                    "similarity": 0.75
                }
            ))
            
            # Close the conversation log to flush
            bus.close_conversation_log(conversation_id)
            
            # Read and verify JSONL
            jsonl_file = event_log_dir / f"{conversation_id}_events.jsonl"
            assert jsonl_file.exists()
            
            with open(jsonl_file) as f:
                lines = f.readlines()
            
            assert len(lines) == 3
            
            # Verify each event
            for i, line in enumerate(lines):
                event_data = json.loads(line)
                assert "event_type" in event_data
                assert "timestamp" in event_data
                assert "conversation_id" in event_data
                
                if i == 0:
                    assert event_data["event_type"] == "TurnStartEvent"
                    assert event_data["turn_number"] == 1
                elif i == 1:
                    assert event_data["event_type"] == "MessageCompleteEvent"
                    assert event_data["message"]["content"] == "Test response"
                    assert event_data["tokens_used"] == 30
                elif i == 2:
                    assert event_data["event_type"] == "MetricsCalculatedEvent"
                    assert event_data["metrics"]["similarity"] == 0.75
                    
        finally:
            await bus.stop()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_conversation(self, tmp_path):
        """Test error handling during conversation."""
        from pidgin.core.events import ErrorEvent
        
        bus = EventBus()
        errors_received = []
        
        def track_errors(event: ErrorEvent):
            errors_received.append(event)
        
        bus.subscribe(ErrorEvent, track_errors)
        
        await bus.start()
        
        try:
            # Emit an error event
            await bus.emit(ErrorEvent(
                conversation_id="error_test",
                error_type="TestError",
                error_message="This is a test error",
                context="Testing phase"
            ))
            
            # Verify error was tracked
            assert len(errors_received) == 1
            assert errors_received[0].error_type == "TestError"
            assert errors_received[0].error_message == "This is a test error"
            
        finally:
            await bus.stop()