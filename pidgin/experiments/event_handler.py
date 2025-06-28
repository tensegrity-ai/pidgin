"""Event handler for capturing metrics during experiments."""

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
    Turn
)
from ..core.types import Message
from .storage import ExperimentStore
from ..metrics import MetricsCalculator


class ExperimentEventHandler:
    """Handles events during experiment runs and stores metrics."""
    
    def __init__(self, storage: ExperimentStore, experiment_id: str, 
                 event_bus=None):
        """Initialize event handler.
        
        Args:
            storage: Database storage instance
            experiment_id: Parent experiment identifier
            event_bus: Optional EventBus for emitting metrics events
        """
        self.storage = storage
        self.experiment_id = experiment_id
        self.event_bus = event_bus
        
        # Per-conversation state
        self.metrics_calculators: Dict[str, MetricsCalculator] = {}
        self.conversation_configs: Dict[str, Dict[str, Any]] = {}
        self.message_timings: Dict[str, Dict[str, int]] = {}
        self.turn_start_times: Dict[str, Dict[int, datetime]] = {}
        self.conversation_metrics: Dict[str, Dict[str, Any]] = {}  # Track metrics history
    
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
        
        # Initialize tracking structures
        self.message_timings[conv_id] = {}
        self.turn_start_times[conv_id] = {}
        self.conversation_metrics[conv_id] = {
            'convergence_history': [],
            'vocabulary_overlap_history': [],
            'message_lengths': {'agent_a': [], 'agent_b': []},
            'word_counts': {'agent_a': [], 'agent_b': []},
            'emoji_counts': {'agent_a': [], 'agent_b': []}
        }
        
        # Update database
        self.storage.update_conversation_status(conv_id, 'running')
    
    async def handle_system_prompt(self, event: SystemPromptEvent):
        """Handle system prompt events to capture agent names if chosen."""
        conv_id = event.conversation_id
        
        # Check if this is a name choice
        if event.agent_display_name and event.agent_display_name != event.agent_id:
            self.storage.log_agent_name(
                conv_id,
                event.agent_id,
                event.agent_display_name,
                turn_number=0
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
        
        # Skip if already processed (idempotency)
        if await self._already_processed(conv_id, turn_number):
            return
        
        # Get the calculator for this conversation
        calculator = self.metrics_calculators.get(conv_id)
        if not calculator:
            return
        
        # Extract messages
        msg_a = turn.agent_a_message.content
        msg_b = turn.agent_b_message.content
        
        # Calculate all metrics
        metrics = calculator.calculate_turn_metrics(turn_number, msg_a, msg_b)
        separated_metrics = self._separate_metrics(metrics)
        
        # Calculate timing
        timing_metrics = self._calculate_timing_metrics(conv_id, turn_number)
        
        # Track metrics for this conversation
        self._track_conversation_metrics(conv_id, separated_metrics)
        
        # Store to database
        await self._store_metrics_to_database(
            conv_id, turn_number, 
            separated_metrics, timing_metrics,
            calculator, msg_a, msg_b
        )
        
        # Emit event if configured
        if self.event_bus:
            await self._emit_metrics_event(
                conv_id, turn_number,
                separated_metrics, timing_metrics
            )
        
    
    async def handle_conversation_end(self, event: ConversationEndEvent):
        """Clean up after conversation ends and update aggregates."""
        conv_id = event.conversation_id
        
        # Determine status based on reason
        status_map = {
            'max_turns_reached': 'completed',
            'high_convergence': 'completed',
            'error': 'failed',
            'pause': 'interrupted',
            'user_interrupt': 'interrupted'
        }
        status = status_map.get(event.reason, event.reason)
        
        # Update conversation status in database
        self.storage.update_conversation_status(
            conv_id, 
            status,
            convergence_reason=event.reason if 'convergence' in event.reason else None
        )
        
        
        # Clean up tracking data
        self.metrics_calculators.pop(conv_id, None)
        self.conversation_configs.pop(conv_id, None)
        self.message_timings.pop(conv_id, None)
        self.turn_start_times.pop(conv_id, None)
        self.conversation_metrics.pop(conv_id, None)
    
    # ========== Helper Methods ==========
    
    async def _already_processed(self, conv_id: str, turn_number: int) -> bool:
        """Check if turn was already processed."""
        try:
            existing = self.storage.get_turn_metrics(conv_id, turn_number)
            return existing is not None
        except:
            return False
    
    def _separate_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Separate metrics by category (agent_a, agent_b, turn)."""
        agent_a_metrics = {}
        agent_b_metrics = {}
        turn_metrics = {}
        
        for key, value in metrics.items():
            if key.endswith('_a'):
                # Remove suffix for cleaner storage
                agent_a_metrics[key[:-2]] = value
            elif key.endswith('_b'):
                # Remove suffix for cleaner storage
                agent_b_metrics[key[:-2]] = value
            else:
                # Turn-level metrics (convergence, overlap, etc.)
                turn_metrics[key] = value
        
        return {
            'agent_a': agent_a_metrics,
            'agent_b': agent_b_metrics,
            'turn': turn_metrics
        }
    
    def _calculate_timing_metrics(self, conv_id: str, turn_number: int) -> Dict[str, int]:
        """Calculate timing-related metrics."""
        # Initialize if needed
        if conv_id not in self.turn_start_times:
            self.turn_start_times[conv_id] = {}
        
        if turn_number not in self.turn_start_times[conv_id]:
            self.turn_start_times[conv_id][turn_number] = datetime.now()
        
        # Calculate turn duration
        turn_start = self.turn_start_times[conv_id][turn_number]
        turn_duration_ms = int((datetime.now() - turn_start).total_seconds() * 1000)
        
        # Get response times from message timings
        timings = self.message_timings.get(conv_id, {})
        
        return {
            'turn_duration_ms': turn_duration_ms,
            'agent_a_response_time_ms': timings.get('agent_a', 0),
            'agent_b_response_time_ms': timings.get('agent_b', 0)
        }
    
    def _track_conversation_metrics(self, conv_id: str, separated_metrics: Dict[str, Dict]):
        """Track metrics history for this conversation."""
        if conv_id not in self.conversation_metrics:
            return
        
        history = self.conversation_metrics[conv_id]
        turn_metrics = separated_metrics['turn']
        agent_a_metrics = separated_metrics['agent_a']
        agent_b_metrics = separated_metrics['agent_b']
        
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
    
    async def _store_metrics_to_database(self, conv_id: str, turn_number: int,
                                        separated_metrics: Dict[str, Dict],
                                        timing_metrics: Dict[str, int],
                                        calculator: MetricsCalculator,
                                        msg_a: str, msg_b: str):
        """Store all metrics to database."""
        # Prepare turn metrics with timing
        turn_metrics = separated_metrics['turn'].copy()
        turn_metrics.update(timing_metrics)
        
        # Add combined vocabulary size
        words_a = set(calculator._tokenize(msg_a.lower()))
        words_b = set(calculator._tokenize(msg_b.lower()))
        turn_metrics['combined_vocabulary_size'] = len(words_a | words_b)
        
        # Store turn-level metrics
        self.storage.log_turn_metrics(conv_id, turn_number, turn_metrics)
        
        # Store agent A metrics
        agent_a_metrics = separated_metrics['agent_a'].copy()
        agent_a_metrics['response_time_ms'] = timing_metrics['agent_a_response_time_ms']
        self.storage.log_message_metrics(conv_id, turn_number, 'agent_a', agent_a_metrics)
        
        # Store agent B metrics
        agent_b_metrics = separated_metrics['agent_b'].copy()
        agent_b_metrics['response_time_ms'] = timing_metrics['agent_b_response_time_ms']
        self.storage.log_message_metrics(conv_id, turn_number, 'agent_b', agent_b_metrics)
        
        # Store word frequencies
        word_freq_a, _ = calculator.get_word_frequencies(msg_a, 'agent_a')
        word_freq_b, _ = calculator.get_word_frequencies(msg_b, 'agent_b')
        
        self.storage.log_word_frequencies(conv_id, turn_number, 'agent_a', word_freq_a)
        self.storage.log_word_frequencies(conv_id, turn_number, 'agent_b', word_freq_b)
    
    async def _emit_metrics_event(self, conv_id: str, turn_number: int,
                                 separated_metrics: Dict[str, Dict],
                                 timing_metrics: Dict[str, int]):
        """Emit metrics event for other components."""
        # Combine all metrics for the event
        all_metrics = {
            **separated_metrics['turn'],
            **timing_metrics,
            'agent_a': separated_metrics['agent_a'],
            'agent_b': separated_metrics['agent_b']
        }
        
        event = MetricsCalculatedEvent(
            conversation_id=conv_id,
            turn_number=turn_number,
            metrics=all_metrics,
            experiment_id=self.experiment_id
        )
        
        await self.event_bus.emit(event)
    
    
    def _build_conversation_summary(self, conv_id: str, event: ConversationEndEvent) -> Dict[str, Any]:
        """Build a comprehensive summary of the completed conversation."""
        config = self.conversation_configs.get(conv_id, {})
        history = self.conversation_metrics.get(conv_id, {})
        
        # Basic info
        summary = {
            'conversation_id': conv_id,
            'total_turns': event.total_turns,
            'model_pair': (config.get('agent_a_model'), config.get('agent_b_model')),
            'temperatures': (config.get('temperature_a'), config.get('temperature_b')),
        }
        
        # Convergence metrics
        convergence_history = history.get('convergence_history', [])
        if convergence_history:
            summary['final_convergence'] = convergence_history[-1]
            summary['max_convergence'] = max(convergence_history)
            summary['convergence_history'] = convergence_history
        else:
            summary['final_convergence'] = 0.0
            summary['max_convergence'] = 0.0
            summary['convergence_history'] = []
        
        # Vocabulary metrics
        vocab_history = history.get('vocabulary_overlap_history', [])
        if vocab_history and len(vocab_history) > 5:
            # Check for vocabulary compression
            early_overlap = sum(vocab_history[:5]) / 5
            late_overlap = sum(vocab_history[-5:]) / 5
            compression_ratio = late_overlap / early_overlap if early_overlap > 0 else 1.0
            summary['vocabulary_metrics'] = {
                'compression_ratio': compression_ratio,
                'final_overlap': vocab_history[-1] if vocab_history else 0
            }
        
        # Pattern detection
        patterns = self._detect_patterns(conv_id, history, summary)
        summary['pattern_flags'] = patterns
        
        # Word frequencies (simplified for now)
        calculator = self.metrics_calculators.get(conv_id)
        if calculator:
            # Get final word frequencies
            all_words = calculator.all_words_seen
            summary['word_frequencies'] = {word: 1 for word in list(all_words)[:50]}  # Top 50
            
            # Emergent words (appeared after turn 10)
            emergent = set()
            for turn_vocab in calculator.turn_vocabularies[10:]:
                emergent.update(turn_vocab.get('agent_a', set()))
                emergent.update(turn_vocab.get('agent_b', set()))
            summary['emergent_words'] = emergent
        
        return summary
    
    def _detect_patterns(self, conv_id: str, history: Dict[str, Any], 
                        summary: Dict[str, Any]) -> Dict[str, bool]:
        """Detect various conversation patterns."""
        patterns = {}
        
        # High convergence
        patterns['high_convergence'] = summary.get('final_convergence', 0) > 0.8
        
        # Vocabulary compression
        vocab_metrics = summary.get('vocabulary_metrics', {})
        patterns['vocabulary_compression'] = vocab_metrics.get('compression_ratio', 1.0) < 0.5
        
        # Symbol emergence (high emoji count in later turns)
        emoji_a = history.get('emoji_counts', {}).get('agent_a', [])
        emoji_b = history.get('emoji_counts', {}).get('agent_b', [])
        if emoji_a and emoji_b:
            late_emoji_density = (sum(emoji_a[-5:]) + sum(emoji_b[-5:])) / 10
            patterns['symbol_emergence'] = late_emoji_density > 2
        else:
            patterns['symbol_emergence'] = False
        
        # Gratitude spiral (simplified - would need word frequency tracking)
        patterns['gratitude_spiral'] = False  # TODO: Implement proper detection
        
        # Echo chamber (high mimicry in later turns)
        patterns['echo_chamber'] = summary.get('max_convergence', 0) > 0.9
        
        return patterns