"""Event handler for capturing metrics during experiments."""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from ..core.events import (
    ConversationStartEvent,
    TurnCompleteEvent,
    ConversationEndEvent,
    MessageCompleteEvent,
    SystemPromptEvent,
    MetricsCalculatedEvent,
    Turn
)
from ..core.types import Message
from .storage import ExperimentStore
from ..metrics import MetricsCalculator


class ExperimentEventHandler:
    """Handles events during experiment runs and stores metrics."""
    
    def __init__(self, storage: ExperimentStore, experiment_id: str, event_bus=None):
        """Initialize event handler.
        
        Args:
            storage: Database storage instance
            experiment_id: Parent experiment identifier
            event_bus: Optional EventBus for emitting metrics events
        """
        self.storage = storage
        self.experiment_id = experiment_id
        self.event_bus = event_bus
        self.metrics_calculators: Dict[str, MetricsCalculator] = {}
        self.conversation_configs: Dict[str, Dict[str, Any]] = {}
        self.message_timings: Dict[str, Dict[str, int]] = {}
        self.turn_messages: Dict[str, Dict[int, Dict[str, Message]]] = {}
        self.turn_start_times: Dict[str, Dict[int, datetime]] = {}
    
    async def handle_conversation_start(self, event: ConversationStartEvent):
        """Initialize tracking for new conversation."""
        conv_id = event.conversation_id
        
        # Initialize metrics calculator for this conversation
        self.metrics_calculators[conv_id] = MetricsCalculator()
        
        # Store conversation config
        self.conversation_configs[conv_id] = {
            'agent_a_model': event.agent_a_model,
            'agent_b_model': event.agent_b_model,
            'initial_prompt': event.initial_prompt,
            'max_turns': event.max_turns,
            'temperature_a': event.temperature_a,
            'temperature_b': event.temperature_b,
            'started_at': event.timestamp
        }
        
        # Initialize message tracking
        self.turn_messages[conv_id] = {}
        self.message_timings[conv_id] = {}
        self.turn_start_times[conv_id] = {}
        
        # Update conversation status to running
        self.storage.update_conversation_status(conv_id, 'running')
    
    async def handle_system_prompt(self, event: SystemPromptEvent):
        """Handle system prompt events to capture agent names if chosen."""
        conv_id = event.conversation_id
        
        # Check if this is a name choice (look for specific patterns)
        if event.agent_display_name and event.agent_display_name != event.agent_id:
            # Agent has a chosen name
            turn_number = 0  # System prompts typically happen at start
            self.storage.log_agent_name(
                conv_id,
                event.agent_id,
                event.agent_display_name,
                turn_number
            )
    
    async def handle_message_complete(self, event: MessageCompleteEvent):
        """Track message completion for timing metrics."""
        conv_id = event.conversation_id
        
        # Store timing information
        if conv_id not in self.message_timings:
            self.message_timings[conv_id] = {}
        
        self.message_timings[conv_id][event.agent_id] = event.duration_ms
    
    async def handle_turn_complete(self, event: TurnCompleteEvent):
        """Calculate and store metrics when turn completes."""
        conv_id = event.conversation_id
        turn_number = event.turn_number
        turn = event.turn
        
        # Track turn timing
        if conv_id not in self.turn_start_times:
            self.turn_start_times[conv_id] = {}
        
        # Set turn start time if not already set
        if turn_number not in self.turn_start_times[conv_id]:
            self.turn_start_times[conv_id][turn_number] = datetime.now()
        
        # Calculate turn duration
        turn_start = self.turn_start_times[conv_id].get(turn_number, datetime.now())
        turn_duration_ms = int((datetime.now() - turn_start).total_seconds() * 1000)
        
        # Get metrics calculator
        calculator = self.metrics_calculators.get(conv_id)
        if not calculator:
            return
        
        # Extract messages
        msg_a = turn.agent_a_message.content
        msg_b = turn.agent_b_message.content
        
        # Calculate all metrics
        metrics = calculator.calculate_turn_metrics(turn_number, msg_a, msg_b)
        
        # Separate turn-level and message-level metrics
        turn_metrics = {}
        agent_a_metrics = {}
        agent_b_metrics = {}
        
        # Extract convergence and turn-level metrics
        convergence_keys = ['convergence_score', 'vocabulary_overlap', 'length_ratio', 
                          'structural_similarity', 'cross_repetition_score', 'mimicry_score']
        
        for key in convergence_keys:
            if key in metrics:
                turn_metrics[key] = metrics[key]
        
        # Extract agent-specific metrics
        for k, v in metrics.items():
            if k.endswith('_a'):
                # Remove _a suffix for storage
                agent_a_metrics[k[:-2]] = v
            elif k.endswith('_b'):
                # Remove _b suffix for storage
                agent_b_metrics[k[:-2]] = v
        
        # Calculate turn-level aggregates
        total_words = agent_a_metrics.get('word_count', 0) + agent_b_metrics.get('word_count', 0)
        total_sentences = agent_a_metrics.get('sentence_count', 0) + agent_b_metrics.get('sentence_count', 0)
        vocab_a = set(calculator._tokenize(msg_a.lower()))
        vocab_b = set(calculator._tokenize(msg_b.lower()))
        combined_vocabulary_size = len(vocab_a | vocab_b)
        
        # Add timing information
        timings = self.message_timings.get(conv_id, {})
        agent_a_response_time = timings.get('agent_a', 0)
        agent_b_response_time = timings.get('agent_b', 0)
        
        # Complete turn metrics
        turn_metrics.update({
            'total_words': total_words,
            'total_sentences': total_sentences,
            'combined_vocabulary_size': combined_vocabulary_size,
            'turn_duration_ms': turn_duration_ms,
            'agent_a_response_time_ms': agent_a_response_time,
            'agent_b_response_time_ms': agent_b_response_time
        })
        
        # Store turn-level metrics
        self.storage.log_turn_metrics(conv_id, turn_number, turn_metrics)
        
        # Store message metrics for agent A
        agent_a_metrics['response_time_ms'] = agent_a_response_time
        self.storage.log_message_metrics(
            conv_id, 0, turn_number, 'agent_a', agent_a_metrics
        )
        
        # Store message metrics for agent B
        agent_b_metrics['response_time_ms'] = agent_b_response_time
        self.storage.log_message_metrics(
            conv_id, 1, turn_number, 'agent_b', agent_b_metrics
        )
        
        # Log word frequencies
        word_freq_a, new_words_a = calculator.get_word_frequencies(msg_a, 'agent_a')
        word_freq_b, new_words_b = calculator.get_word_frequencies(msg_b, 'agent_b')
        
        self.storage.log_word_frequencies(
            conv_id, turn_number, 'agent_a', word_freq_a, new_words_a
        )
        self.storage.log_word_frequencies(
            conv_id, turn_number, 'agent_b', word_freq_b, new_words_b
        )
        
        # Emit metrics event if we have an EventBus
        if self.event_bus:
            # Combine all metrics for the event
            all_metrics = {
                **turn_metrics,
                'agent_a': agent_a_metrics,
                'agent_b': agent_b_metrics,
                'word_frequencies': {
                    'agent_a': {'frequencies': word_freq_a, 'new_words': new_words_a},
                    'agent_b': {'frequencies': word_freq_b, 'new_words': new_words_b}
                }
            }
            
            await self.event_bus.emit(MetricsCalculatedEvent(
                conversation_id=conv_id,
                turn_number=turn_number,
                metrics=all_metrics,
                experiment_id=self.experiment_id
            ))
        
        # Clear timing data for next turn
        self.message_timings[conv_id] = {}
    
    async def handle_conversation_end(self, event: ConversationEndEvent):
        """Update final conversation status."""
        conv_id = event.conversation_id
        
        # Determine final status based on reason
        if event.reason == 'error':
            status = 'failed'
        elif event.reason == 'pause':
            status = 'interrupted'
        else:
            status = 'completed'
        
        # Get final convergence score if available
        calculator = self.metrics_calculators.get(conv_id)
        final_convergence = None
        
        if calculator and event.total_turns > 0:
            # Get last turn's convergence score from database
            # (We could also track it in memory)
            pass
        
        # Update conversation status
        self.storage.update_conversation_status(
            conv_id,
            status,
            convergence_reason=event.reason,
            final_convergence_score=final_convergence
        )
        
        # Clean up tracking data
        if conv_id in self.metrics_calculators:
            del self.metrics_calculators[conv_id]
        if conv_id in self.conversation_configs:
            del self.conversation_configs[conv_id]
        if conv_id in self.message_timings:
            del self.message_timings[conv_id]
        if conv_id in self.turn_messages:
            del self.turn_messages[conv_id]
        if conv_id in self.turn_start_times:
            del self.turn_start_times[conv_id]