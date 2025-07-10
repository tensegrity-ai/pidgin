"""Optimized metrics calculator with O(n) performance for conversation analysis."""

from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict
import functools

from .text_analysis import TextAnalyzer
from .convergence_metrics import ConvergenceCalculator
from .linguistic_metrics import LinguisticAnalyzer


class OptimizedMetricsCalculator:
    """Optimized calculator with caching and incremental updates for O(n) performance."""
    
    def __init__(self):
        """Initialize calculator with optimized tracking structures."""
        # Cumulative vocabulary tracking (incrementally updated)
        self.cumulative_vocab = {
            'agent_a': set(),
            'agent_b': set()
        }
        
        # All words seen by each agent (for repetition calculation)
        self.all_agent_words = {
            'agent_a': set(),
            'agent_b': set()
        }
        
        # Token cache to avoid re-tokenizing
        self._token_cache: Dict[str, List[str]] = {}
        self._cache_size_limit = 1000  # Limit cache size
        
        # Previous messages for context
        self.previous_messages: Dict[str, List[str]] = {
            'agent_a': [],
            'agent_b': []
        }
        
        # Track turn vocabularies for other analyses
        self.turn_vocabularies: List[Dict[str, Set[str]]] = []
        
        # Initialize helper classes
        self.text_analyzer = TextAnalyzer()
        self.convergence_calc = ConvergenceCalculator()
        self.linguistic_analyzer = LinguisticAnalyzer()
    
    def _tokenize_cached(self, text: str) -> List[str]:
        """Tokenize with caching to avoid redundant processing."""
        # Check cache
        if text in self._token_cache:
            return self._token_cache[text]
        
        # Tokenize
        tokens = self.text_analyzer.tokenize(text.lower())
        
        # Add to cache if within size limit
        if len(self._token_cache) < self._cache_size_limit:
            self._token_cache[text] = tokens
        
        return tokens
    
    def calculate_turn_metrics(self, turn_number: int, 
                             agent_a_message: str, 
                             agent_b_message: str) -> Dict[str, Any]:
        """Calculate all metrics for a turn with O(n) performance.
        
        Args:
            turn_number: 0-indexed turn number
            agent_a_message: Message from agent A
            agent_b_message: Message from agent B
            
        Returns:
            Dictionary with all calculated metrics
        """
        # Calculate metrics for each agent
        metrics_a = self._calculate_message_metrics(
            agent_a_message, 'agent_a', turn_number
        )
        metrics_b = self._calculate_message_metrics(
            agent_b_message, 'agent_b', turn_number
        )
        
        # Calculate convergence metrics with optimization
        convergence = self._calculate_convergence_optimized(
            agent_a_message, agent_b_message, turn_number
        )
        
        # Update tracking structures for next turn
        self.previous_messages['agent_a'].append(agent_a_message)
        self.previous_messages['agent_b'].append(agent_b_message)
        
        # Combine all metrics
        return {
            'turn_number': turn_number,
            'agent_a': metrics_a,
            'agent_b': metrics_b,
            'convergence': convergence
        }
    
    def _calculate_message_metrics(self, message: str, agent: str, 
                                 turn_number: int) -> Dict[str, Any]:
        """Calculate metrics for a single message."""
        # Use cached tokenization
        words = self._tokenize_cached(message)
        sentences = self.text_analyzer.split_sentences(message)
        
        # Basic metrics
        word_count = len(words)
        sentence_count = len(sentences)
        char_count = len(message)
        
        # Safe division with guards
        avg_word_length = sum(len(w) for w in words) / max(word_count, 1)
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        # Linguistic analysis
        linguistic = self.linguistic_analyzer.analyze_message(message)
        
        # Vocabulary analysis
        unique_words = set(words)
        vocab_size = len(unique_words)
        
        # Repetition (optimized O(1) calculation)
        repetition = self._calculate_repetition_optimized(words, agent, turn_number)
        
        # Update agent's cumulative vocabulary
        self.cumulative_vocab[agent].update(unique_words)
        self.all_agent_words[agent].update(unique_words)
        
        return {
            'message_length': char_count,
            'word_count': word_count,
            'sentence_count': sentence_count,
            'avg_word_length': avg_word_length,
            'avg_sentence_length': avg_sentence_length,
            'vocabulary_size': vocab_size,
            'unique_word_ratio': vocab_size / max(word_count, 1),
            'repetition': repetition,
            **linguistic
        }
    
    def _calculate_convergence_optimized(self, message_a: str, message_b: str,
                                       turn_number: int) -> Dict[str, float]:
        """Calculate convergence metrics with O(1) cumulative overlap."""
        # Get vocabularies for this turn
        words_a = set(self._tokenize_cached(message_a))
        words_b = set(self._tokenize_cached(message_b))
        
        # Store turn vocabulary
        turn_vocab = {'agent_a': words_a, 'agent_b': words_b}
        self.turn_vocabularies.append(turn_vocab)
        
        # Current turn overlap
        current_overlap = self.convergence_calc.calculate_vocabulary_overlap(words_a, words_b)
        
        # Cumulative overlap (O(1) - using already updated cumulative sets)
        cumulative_overlap = self.convergence_calc.calculate_vocabulary_overlap(
            self.cumulative_vocab['agent_a'], 
            self.cumulative_vocab['agent_b']
        )
        
        # Other convergence metrics
        cross_repetition = self.convergence_calc.calculate_cross_repetition(message_a, message_b)
        structural_similarity = self.convergence_calc.calculate_structural_similarity(message_a, message_b)
        
        # Mimicry (check both directions)
        mimicry_a_to_b = self.convergence_calc.calculate_mimicry_score(message_a, message_b)
        mimicry_b_to_a = self.convergence_calc.calculate_mimicry_score(message_b, message_a)
        
        # Safe division for mutual mimicry
        mutual_mimicry = (mimicry_a_to_b + mimicry_b_to_a) / 2 if mimicry_a_to_b is not None and mimicry_b_to_a is not None else 0.0
        
        return {
            'vocabulary_overlap': current_overlap,
            'cumulative_overlap': cumulative_overlap,
            'cross_repetition': cross_repetition,
            'structural_similarity': structural_similarity,
            'mimicry_a_to_b': mimicry_a_to_b,
            'mimicry_b_to_a': mimicry_b_to_a,
            'mutual_mimicry': mutual_mimicry
        }
    
    def _calculate_repetition_optimized(self, current_words: List[str], 
                                      agent: str, turn_number: int) -> float:
        """Calculate repetition with O(1) performance using maintained sets."""
        if turn_number == 0:
            return 0.0
        
        current_word_set = set(current_words)
        if not current_word_set:
            return 0.0
        
        # O(1) lookup using maintained cumulative set
        # Note: We exclude current words since they haven't been added yet
        previous_words = self.all_agent_words[agent] - current_word_set
        
        if not previous_words:
            return 0.0
        
        overlap = len(current_word_set & previous_words)
        return overlap / len(current_word_set)
    
    def reset(self):
        """Reset calculator state for new conversation."""
        self.cumulative_vocab = {'agent_a': set(), 'agent_b': set()}
        self.all_agent_words = {'agent_a': set(), 'agent_b': set()}
        self.previous_messages = {'agent_a': [], 'agent_b': []}
        self.turn_vocabularies = []
        self._token_cache.clear()