"""Async event handler for experiments using DuckDB storage."""

import asyncio
from typing import Dict, Any, Optional, Set, List, Tuple
from datetime import datetime

from ..core.events import (
    ConversationStartEvent,
    TurnCompleteEvent,
    ConversationEndEvent,
    MessageCompleteEvent,
    SystemPromptEvent,
    MetricsCalculatedEvent,
    TokenUsageEvent,
    Turn
)
from ..core.types import Message
from .storage import AsyncExperimentStore
from ..metrics import MetricsCalculator
from ..io.logger import get_logger
from .token_handler import TokenUsageHandler

logger = get_logger("async_event_handler")


class AsyncExperimentEventHandler:
    """Async event handler that stores metrics in DuckDB."""
    
    def __init__(self, storage: AsyncExperimentStore, experiment_id: str, 
                 event_bus=None):
        """Initialize async event handler.
        
        Args:
            storage: Async database storage instance
            experiment_id: Parent experiment identifier
            event_bus: Optional EventBus for emitting metrics events
        """
        self.storage = storage
        self.experiment_id = experiment_id
        self.event_bus = event_bus
        
        # Initialize token handler
        self.token_handler = TokenUsageHandler(storage)
        
        # Per-conversation state
        self.metrics_calculators: Dict[str, MetricsCalculator] = {}
        self.conversation_configs: Dict[str, Dict[str, Any]] = {}
        self.message_timings: Dict[str, Dict[str, int]] = {}
        self.turn_start_times: Dict[str, Dict[int, datetime]] = {}
        self.conversation_metrics: Dict[str, Dict[str, Any]] = {}
    
    async def handle_conversation_start(self, event: ConversationStartEvent):
        """Initialize tracking for new conversation."""
        conv_id = event.conversation_id
        
        # Initialize metrics calculator
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
        
        # Initialize tracking
        self.message_timings[conv_id] = {}
        self.turn_start_times[conv_id] = {}
        self.conversation_metrics[conv_id] = {
            'convergence_history': [],
            'vocabulary_overlap_history': [],
            'message_lengths': {'agent_a': [], 'agent_b': []},
            'word_counts': {'agent_a': [], 'agent_b': []},
            'emoji_counts': {'agent_a': [], 'agent_b': []}
        }
        
        # Update database asynchronously
        await self.storage.update_conversation_status(conv_id, 'running')
    
    async def handle_system_prompt(self, event: SystemPromptEvent):
        """Handle system prompt events to capture agent names."""
        conv_id = event.conversation_id
        
        # Check if this is a name choice
        if event.agent_display_name and event.agent_display_name != event.agent_id:
            await self.storage.log_agent_name(
                conv_id,
                event.agent_id,
                event.agent_display_name
            )
    
    async def handle_message_complete(self, event: MessageCompleteEvent):
        """Track message completion for timing metrics."""
        conv_id = event.conversation_id
        
        # Store timing information
        if conv_id not in self.message_timings:
            self.message_timings[conv_id] = {}
        
        self.message_timings[conv_id][event.agent_id] = event.duration_ms
        
        # Log message to database for search
        await self.storage.log_message(
            conv_id,
            -1,  # Turn number will be updated when turn completes
            event.agent_id,
            event.message.content,
            {'count': event.tokens_used, 'model_reported': event.tokens_used}
        )
        
        # Also handle token tracking
        await self.token_handler.handle_message_complete(event)
    
    async def handle_turn_complete(self, event: TurnCompleteEvent):
        """Calculate and store metrics when turn completes."""
        conv_id = event.conversation_id
        turn_number = event.turn_number
        turn = event.turn
        
        # Get the calculator
        calculator = self.metrics_calculators.get(conv_id)
        if not calculator:
            logger.warning(f"No calculator for conversation {conv_id}")
            return
        
        # Extract messages
        msg_a = turn.agent_a_message.content
        msg_b = turn.agent_b_message.content
        
        # Calculate all metrics
        metrics = calculator.calculate_turn_metrics(turn_number, msg_a, msg_b)
        
        # Separate metrics by category
        agent_a_metrics = {}
        agent_b_metrics = {}
        turn_metrics = {}
        
        for key, value in metrics.items():
            if key.endswith('_a'):
                agent_a_metrics[key[:-2]] = value
            elif key.endswith('_b'):
                agent_b_metrics[key[:-2]] = value
            else:
                turn_metrics[key] = value
        
        # Get word frequencies
        word_freq_a, _ = calculator.get_word_frequencies(msg_a, 'agent_a')
        word_freq_b, _ = calculator.get_word_frequencies(msg_b, 'agent_b')
        
        # Calculate shared vocabulary
        words_a = set(word_freq_a.keys())
        words_b = set(word_freq_b.keys())
        shared_words = words_a & words_b
        shared_vocab = {word: word_freq_a[word] + word_freq_b[word] for word in shared_words}
        
        # Prepare word frequencies dict
        word_frequencies = {
            'agent_a': word_freq_a,
            'agent_b': word_freq_b,
            'shared': shared_vocab
        }
        
        # Calculate timing
        timing_info = self._calculate_timing(conv_id, turn_number)
        
        # Add response times to message metrics
        agent_a_metrics['response_time_ms'] = self.message_timings.get(conv_id, {}).get('agent_a', 0)
        agent_b_metrics['response_time_ms'] = self.message_timings.get(conv_id, {}).get('agent_b', 0)
        
        # Prepare message metrics
        message_metrics = {
            'agent_a': agent_a_metrics,
            'agent_b': agent_b_metrics
        }
        
        # Track metrics history
        self._track_conversation_metrics(conv_id, turn_metrics, agent_a_metrics, agent_b_metrics)
        
        # Store to database using new schema
        await self.storage.log_turn_metrics(
            conv_id, turn_number,
            turn_metrics, word_frequencies, message_metrics, timing_info
        )
        
        # Update messages with correct turn number
        await self.storage.log_message(
            conv_id, turn_number, 'agent_a', msg_a,
            {'count': len(msg_a.split()), 'model_reported': None}
        )
        await self.storage.log_message(
            conv_id, turn_number, 'agent_b', msg_b,
            {'count': len(msg_b.split()), 'model_reported': None}
        )
        
        # Emit metrics event if configured
        if self.event_bus:
            await self._emit_metrics_event(
                conv_id, turn_number, turn_metrics, message_metrics, timing_info
            )
    
    async def handle_conversation_end(self, event: ConversationEndEvent):
        """Clean up after conversation ends."""
        conv_id = event.conversation_id
        
        # Determine status
        status_map = {
            'max_turns_reached': 'completed',
            'high_convergence': 'completed',
            'error': 'failed',
            'pause': 'interrupted',
            'user_interrupt': 'interrupted'
        }
        status = status_map.get(event.reason, event.reason)
        
        # Get final convergence score if available
        final_convergence = None
        if conv_id in self.conversation_metrics:
            history = self.conversation_metrics[conv_id]['convergence_history']
            if history:
                final_convergence = history[-1]
        
        # Update conversation status
        await self.storage.update_conversation_status(
            conv_id, 
            status,
            convergence_reason=event.reason if 'convergence' in event.reason else None,
            final_convergence_score=final_convergence,
            error_message=None  # Could be populated from error events
        )
        
        # Clean up tracking data
        self.metrics_calculators.pop(conv_id, None)
        self.conversation_configs.pop(conv_id, None)
        self.message_timings.pop(conv_id, None)
        self.turn_start_times.pop(conv_id, None)
        self.conversation_metrics.pop(conv_id, None)
    
    def _calculate_timing(self, conv_id: str, turn_number: int) -> Dict[str, Any]:
        """Calculate timing information for a turn."""
        if conv_id not in self.turn_start_times:
            self.turn_start_times[conv_id] = {}
        
        if turn_number not in self.turn_start_times[conv_id]:
            self.turn_start_times[conv_id][turn_number] = datetime.now()
        
        turn_start = self.turn_start_times[conv_id][turn_number]
        turn_end = datetime.now()
        duration_ms = int((turn_end - turn_start).total_seconds() * 1000)
        
        return {
            'turn_start': turn_start,
            'turn_end': turn_end,
            'duration_ms': duration_ms
        }
    
    def _track_conversation_metrics(self, conv_id: str, turn_metrics: Dict[str, Any],
                                   agent_a_metrics: Dict[str, Any],
                                   agent_b_metrics: Dict[str, Any]):
        """Track metrics history for conversation."""
        if conv_id not in self.conversation_metrics:
            return
        
        history = self.conversation_metrics[conv_id]
        
        # Track convergence
        history['convergence_history'].append(turn_metrics.get('convergence_score', 0))
        history['vocabulary_overlap_history'].append(turn_metrics.get('vocabulary_overlap', 0))
        
        # Track per-agent metrics
        history['message_lengths']['agent_a'].append(agent_a_metrics.get('message_length', 0))
        history['message_lengths']['agent_b'].append(agent_b_metrics.get('message_length', 0))
        history['word_counts']['agent_a'].append(agent_a_metrics.get('word_count', 0))
        history['word_counts']['agent_b'].append(agent_b_metrics.get('word_count', 0))
        history['emoji_counts']['agent_a'].append(agent_a_metrics.get('emoji_count', 0))
        history['emoji_counts']['agent_b'].append(agent_b_metrics.get('emoji_count', 0))
    
    async def _emit_metrics_event(self, conv_id: str, turn_number: int,
                                 turn_metrics: Dict[str, Any],
                                 message_metrics: Dict[str, Any],
                                 timing: Dict[str, Any]):
        """Emit metrics event for other components."""
        all_metrics = {
            **turn_metrics,
            'timing': timing,
            'messages': message_metrics
        }
        
        event = MetricsCalculatedEvent(
            conversation_id=conv_id,
            turn_number=turn_number,
            metrics=all_metrics,
            experiment_id=self.experiment_id
        )
        
        await self.event_bus.emit(event)
    
    async def handle_token_usage(self, event: TokenUsageEvent):
        """Handle token usage events."""
        await self.token_handler.handle_token_usage(event)