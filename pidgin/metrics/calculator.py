"""Comprehensive metrics calculator for conversation analysis."""

from typing import Dict, List, Set, Any, Optional
from collections import defaultdict

from .text_analysis import TextAnalyzer
from .convergence_metrics import ConvergenceCalculator
from .linguistic_metrics import LinguisticAnalyzer


class MetricsCalculator:
    """Calculates comprehensive metrics for conversation turns."""
    
    def __init__(self):
        """Initialize calculator with cross-turn tracking."""
        self.conversation_vocabulary: Set[str] = set()
        self.turn_vocabularies: List[Dict[str, Set[str]]] = []
        self.previous_messages: Dict[str, List[str]] = {
            'agent_a': [],
            'agent_b': []
        }
        self.all_words_seen: Set[str] = set()
        
        # Initialize helper classes
        self.text_analyzer = TextAnalyzer()
        self.convergence_calc = ConvergenceCalculator()
        self.linguistic_analyzer = LinguisticAnalyzer()
    
    def calculate_turn_metrics(self, turn_number: int, 
                             agent_a_message: str, 
                             agent_b_message: str) -> Dict[str, Any]:
        """Calculate all metrics for a turn.
        
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
        
        # Calculate convergence metrics
        convergence = self._calculate_convergence_metrics(
            agent_a_message, agent_b_message, turn_number
        )
        
        # Store messages for next turn
        self.previous_messages['agent_a'].append(agent_a_message)
        self.previous_messages['agent_b'].append(agent_b_message)
        
        # Update vocabularies
        self.turn_vocabularies.append({
            'agent_a': metrics_a['vocabulary'],
            'agent_b': metrics_b['vocabulary']
        })
        
        return {
            'agent_a': metrics_a,
            'agent_b': metrics_b,
            'convergence': convergence
        }
    
    def _calculate_message_metrics(self, message: str, 
                                 agent: str, 
                                 turn_number: int) -> Dict[str, Any]:
        """Calculate metrics for a single message."""
        # Get word frequencies and vocabulary
        word_counter, vocabulary = self.text_analyzer.get_word_frequencies(message)
        words = self.text_analyzer.tokenize(message)
        
        # Update tracking
        self.conversation_vocabulary.update(vocabulary)
        new_words = vocabulary - self.all_words_seen
        self.all_words_seen.update(vocabulary)
        
        # Basic counts
        word_count = len(words)
        char_count = len(message)
        
        # Text structure metrics
        sentence_count = self.text_analyzer.count_sentences(message)
        paragraph_count = self.text_analyzer.count_paragraphs(message)
        question_count = self.text_analyzer.count_questions(message)
        exclamation_count = self.text_analyzer.count_exclamations(message)
        
        # Special elements
        special_symbol_count = self.text_analyzer.count_special_symbols(message)
        number_count = self.text_analyzer.count_numbers(message)
        proper_noun_count = self.text_analyzer.count_proper_nouns(words)
        
        # Linguistic markers
        linguistic_markers = self.linguistic_analyzer.count_linguistic_markers(words)
        
        # Complexity metrics
        entropy = self.linguistic_analyzer.calculate_entropy(word_counter)
        compression_ratio = self.convergence_calc.calculate_compression_ratio(message)
        
        # Diversity metrics
        lexical_diversity = self.linguistic_analyzer.calculate_lexical_diversity_index(
            word_count, len(vocabulary)
        )
        punctuation_diversity = self.text_analyzer.calculate_punctuation_diversity(message)
        
        # Repetition metrics
        self_repetition = self.linguistic_analyzer.calculate_self_repetition(words)
        turn_repetition = self._calculate_repetition(message, agent, turn_number)
        
        # Style metrics
        avg_word_length = sum(len(w) for w in words) / max(word_count, 1)
        avg_sentence_length = word_count / max(sentence_count, 1)
        formality_score = self.linguistic_analyzer.calculate_formality_score(message, words)
        
        # Acknowledgment detection
        starts_with_ack = self.text_analyzer.starts_with_acknowledgment(message)
        
        return {
            # Basic counts
            'message_length': char_count,
            'word_count': word_count,
            'vocabulary_size': len(vocabulary),
            'new_words': len(new_words),
            'vocabulary': vocabulary,
            
            # Structure
            'sentence_count': sentence_count,
            'paragraph_count': paragraph_count,
            'avg_word_length': avg_word_length,
            'avg_sentence_length': avg_sentence_length,
            
            # Content types
            'question_count': question_count,
            'exclamation_count': exclamation_count,
            'special_symbol_count': special_symbol_count,
            'number_count': number_count,
            'proper_noun_count': proper_noun_count,
            
            # Linguistic markers
            **linguistic_markers,
            
            # Complexity
            'entropy': entropy,
            'compression_ratio': compression_ratio,
            'lexical_diversity': lexical_diversity,
            'punctuation_diversity': punctuation_diversity,
            
            # Repetition
            'self_repetition': self_repetition,
            'turn_repetition': turn_repetition,
            
            # Style
            'formality_score': formality_score,
            'starts_with_acknowledgment': starts_with_ack
        }
    
    def _calculate_convergence_metrics(self, message_a: str, message_b: str,
                                     turn_number: int) -> Dict[str, float]:
        """Calculate convergence metrics between messages."""
        # Get vocabularies
        _, vocab_a = self.text_analyzer.get_word_frequencies(message_a)
        _, vocab_b = self.text_analyzer.get_word_frequencies(message_b)
        
        # Vocabulary overlap
        current_overlap = self.convergence_calc.calculate_vocabulary_overlap(vocab_a, vocab_b)
        
        # Calculate cumulative overlap
        cumulative_vocab_a = set()
        cumulative_vocab_b = set()
        for i in range(turn_number + 1):
            if i < len(self.turn_vocabularies):
                cumulative_vocab_a.update(self.turn_vocabularies[i].get('agent_a', set()))
                cumulative_vocab_b.update(self.turn_vocabularies[i].get('agent_b', set()))
        
        cumulative_overlap = self.convergence_calc.calculate_vocabulary_overlap(
            cumulative_vocab_a, cumulative_vocab_b
        )
        
        # Other convergence metrics
        cross_repetition = self.convergence_calc.calculate_cross_repetition(message_a, message_b)
        structural_similarity = self.convergence_calc.calculate_structural_similarity(message_a, message_b)
        
        # Mimicry (check both directions)
        mimicry_a_to_b = self.convergence_calc.calculate_mimicry_score(message_a, message_b)
        mimicry_b_to_a = self.convergence_calc.calculate_mimicry_score(message_b, message_a)
        
        return {
            'vocabulary_overlap': current_overlap,
            'cumulative_overlap': cumulative_overlap,
            'cross_repetition': cross_repetition,
            'structural_similarity': structural_similarity,
            'mimicry_a_to_b': mimicry_a_to_b,
            'mimicry_b_to_a': mimicry_b_to_a,
            'mutual_mimicry': (mimicry_a_to_b + mimicry_b_to_a) / 2
        }
    
    def _calculate_repetition(self, message: str, agent: str, 
                            turn_number: int) -> float:
        """Calculate repetition relative to previous messages."""
        if turn_number == 0:
            return 0.0
        
        current_words = set(self.text_analyzer.tokenize(message.lower()))
        if not current_words:
            return 0.0
        
        # Check overlap with all previous messages from this agent
        previous_words = set()
        for prev_msg in self.previous_messages[agent]:
            previous_words.update(self.text_analyzer.tokenize(prev_msg.lower()))
        
        if not previous_words:
            return 0.0
        
        overlap = len(current_words & previous_words)
        return overlap / len(current_words)